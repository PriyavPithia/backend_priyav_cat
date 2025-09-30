#!/usr/bin/env python3
"""CLI script to trigger weekly reminder emails for incomplete client assessments."""
import logging
import os
import sys

# Ensure src package is on the path when running as a script
directory = os.path.dirname(__file__)
if directory not in sys.path:
    sys.path.append(os.path.join(directory, "src"))

from src.config.database import SessionLocal
from src.services.reminder_service import ReminderService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reminder_script")


def main() -> None:
    logger.info("Starting weekly reminder job")
    session = SessionLocal()
    try:
        service = ReminderService(session)
        result = service.send_pending_case_reminders()
        logger.info(
            "Reminder job complete: %s sent, %s skipped, %s failed (candidates=%s)",
            result.sent,
            result.skipped,
            result.failed,
            result.total_candidates,
        )
        if result.failed_case_ids:
            logger.warning("Failed case IDs: %s", ", ".join(result.failed_case_ids))
        if result.skipped_case_ids:
            logger.info("Skipped case IDs: %s", ", ".join(result.skipped_case_ids))
    finally:
        session.close()
        logger.info("Weekly reminder job finished")


if __name__ == "__main__":
    main()
