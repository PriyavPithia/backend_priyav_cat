from datetime import datetime, timedelta
import uuid

import pytest

from src.models import Case, CaseStatus, Office, User, UserRole, UserStatus
from src.services.reminder_service import ReminderService, REMINDER_TEMPLATE_NAME
from src.services.email_service import EmailServiceError


class FakeEmailService:
    def __init__(self):
        self.calls = []

    def send_template_email(self, to_emails, template_name, context):
        self.calls.append({
            "to": to_emails,
            "template": template_name,
            "context": context,
        })
        return True


class FailingEmailService(FakeEmailService):
    def send_template_email(self, to_emails, template_name, context):
        super().send_template_email(to_emails, template_name, context)
        raise EmailServiceError("SMTP failure")


def _create_case(db_session, **overrides):
    office = Office(
        name="Test Office",
        code=f"OFF-{uuid.uuid4().hex[:6]}"
    )

    client = User(
        email=f"client-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hashed",
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        first_name="Case",
        last_name="Tester",
        ca_client_number=overrides.pop("client_number", "CAT-001"),
    )
    client.office = office

    case = Case(
        client=client,
        office=office,
        status=overrides.pop("status", CaseStatus.PENDING),
        reminder_count=overrides.pop("reminder_count", 0),
        last_reminder_sent=overrides.pop("last_reminder_sent", None),
        has_debt_emergency=False,
        debts_completed=overrides.pop("debts_completed", False),
        income_completed=overrides.pop("income_completed", False),
        expenditure_completed=overrides.pop("expenditure_completed", False),
    )

    for key, value in overrides.items():
        setattr(case, key, value)

    db_session.add(case)
    db_session.commit()
    return case


def test_reminder_sent_for_pending_case(db_session):
    case = _create_case(db_session)
    email_service = FakeEmailService()

    service = ReminderService(db_session, email_service=email_service)
    result = service.send_pending_case_reminders()

    assert result.sent == 1
    assert result.total_candidates == 1
    assert email_service.calls[0]["template"] == REMINDER_TEMPLATE_NAME
    assert email_service.calls[0]["to"] == [case.client.email]
    assert email_service.calls[0]["context"]["assessment_link"].endswith("/debt-advice")

    updated_case = db_session.get(Case, case.id)
    assert updated_case.reminder_count == 1
    assert updated_case.last_reminder_sent is not None


def test_reminder_skipped_when_recently_sent(db_session):
    last_week = datetime.utcnow() - timedelta(days=3)
    case = _create_case(db_session, last_reminder_sent=last_week)

    email_service = FakeEmailService()
    service = ReminderService(db_session, email_service=email_service)
    result = service.send_pending_case_reminders()

    assert result.sent == 0
    assert result.skipped == 1
    assert email_service.calls == []

    updated_case = db_session.get(Case, case.id)
    assert updated_case.reminder_count == 0
    assert updated_case.last_reminder_sent == last_week


def test_reminder_stops_after_maximum(db_session):
    last_month = datetime.utcnow() - timedelta(days=40)
    case = _create_case(db_session, reminder_count=6, last_reminder_sent=last_month)

    email_service = FakeEmailService()
    service = ReminderService(db_session, email_service=email_service)
    result = service.send_pending_case_reminders()

    assert result.sent == 0
    assert result.skipped == 1
    assert email_service.calls == []

    updated_case = db_session.get(Case, case.id)
    assert updated_case.reminder_count == 6


def test_reminder_records_failures(db_session):
    case = _create_case(db_session)
    case_id = case.id
    email_service = FailingEmailService()

    service = ReminderService(db_session, email_service=email_service)
    result = service.send_pending_case_reminders()

    assert result.sent == 0
    assert result.failed == 1
    assert result.failed_case_ids == [case_id]

    updated_case = db_session.get(Case, case_id)
    assert updated_case.reminder_count == 0
    assert updated_case.last_reminder_sent is None
