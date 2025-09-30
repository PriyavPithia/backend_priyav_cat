"""Weekly reminder service for incomplete client assessments."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

try:  # pragma: no cover - import fallback for script execution
    from ..config.settings import settings
    from ..models import Case, CaseStatus
    from ..services.email_service import EmailServiceError, get_email_service
    from ..utils.auth import should_send_reminder
except ImportError:
    from config.settings import settings
    from models import Case, CaseStatus
    from services.email_service import EmailServiceError, get_email_service
    from utils.auth import should_send_reminder

logger = logging.getLogger(__name__)

REMINDER_TEMPLATE_NAME = "4. WEEKLY REMINDER EMAIL TO INCOMPLETE CLIENTS.html"
MAX_REMINDERS = 6


@dataclass
class ReminderResult:
    """Summary information returned after processing reminder emails."""

    total_candidates: int = 0
    sent: int = 0
    skipped: int = 0
    failed: int = 0
    skipped_case_ids: List[str] = field(default_factory=list)
    failed_case_ids: List[str] = field(default_factory=list)

    @property
    def has_activity(self) -> bool:
        """Check whether any reminder emails were sent."""
        return self.sent > 0


class ReminderService:
    """Service that sends weekly reminders for incomplete client assessments."""

    def __init__(self, db: Session, email_service=None):
        self.db = db
        self.email_service = email_service or get_email_service()

    def send_pending_case_reminders(self) -> ReminderResult:
        """Send reminder emails to clients with pending cases."""
        result = ReminderResult()

        eligible_cases = (
            self.db.query(Case)
            .options(joinedload(Case.client), joinedload(Case.office))
            .filter(
                Case.status == CaseStatus.PENDING,
                or_(Case.reminder_count.is_(None), Case.reminder_count <= MAX_REMINDERS),
            )
            .all()
        )

        result.total_candidates = len(eligible_cases)
        logger.info("Found %s cases eligible for reminder processing", result.total_candidates)

        for case in eligible_cases:
            reminder_count = case.reminder_count or 0

            if not case.client or not case.client.email:
                logger.warning("Skipping case %s due to missing client email", case.id)
                result.skipped += 1
                result.skipped_case_ids.append(case.id)
                continue

            if not should_send_reminder(case.last_reminder_sent, reminder_count):
                logger.debug(
                    "Skipping case %s due to reminder cadence (last=%s, count=%s)",
                    case.id,
                    case.last_reminder_sent,
                    reminder_count,
                )
                result.skipped += 1
                result.skipped_case_ids.append(case.id)
                continue

            context = self._build_email_context(case)

            try:
                self.email_service.send_template_email(
                    [case.client.email],
                    REMINDER_TEMPLATE_NAME,
                    context,
                )
            except EmailServiceError:
                logger.exception("Failed to send reminder email for case %s", case.id)
                result.failed += 1
                result.failed_case_ids.append(case.id)
                continue
            except Exception:  # pragma: no cover - defensive fallback
                logger.exception("Unexpected error while sending reminder for case %s", case.id)
                result.failed += 1
                result.failed_case_ids.append(case.id)
                continue

            case.last_reminder_sent = datetime.utcnow()
            case.reminder_count = reminder_count + 1
            self.db.add(case)
            self.db.commit()

            result.sent += 1
            logger.info(
                "Sent reminder %s/%s to client %s for case %s",
                case.reminder_count,
                MAX_REMINDERS,
                case.client.email,
                case.id,
            )

        return result

    def _build_email_context(self, case: Case) -> dict:
        """Build template context for reminder email."""
        client = case.client
        office = case.office

        assessment_link = f"{settings.frontend_url.rstrip('/')}/debt-advice"

        return {
            "subject": "Complete Your Assessment - Citizens Advice Tadley",
            "user_name": client.full_name,
            "assessment_link": assessment_link,
            "case_status": case.status.value.replace("_", " ").title(),
            "completion_percentage": int(round(case.completion_percentage or 0)),
            "ca_client_number": client.ca_client_number or "Not provided",
            "ca_office": office.name if office else "Citizens Advice Tadley",
        }


def run_reminder_job(db: Session, email_service=None) -> ReminderResult:
    """Convenience function to run reminders with an existing DB session."""
    service = ReminderService(db, email_service=email_service)
    return service.send_pending_case_reminders()
