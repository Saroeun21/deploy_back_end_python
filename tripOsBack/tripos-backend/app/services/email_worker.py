import asyncio
import logging

from app.core.config import settings
from app.services.notification_email_service import process_due_notification_emails
from app.services.reminder_email_service import (
    missing_reminder_email_settings,
    process_due_reminder_emails,
    reminder_email_is_configured,
)

logger = logging.getLogger(__name__)


async def run_email_worker() -> None:
    if not reminder_email_is_configured():
        raise RuntimeError(
            "The email worker cannot start; missing Gmail settings: "
            + ", ".join(missing_reminder_email_settings())
        )

    logger.info("Komsan reminder and notification email worker started.")
    while True:
        try:
            sent_count = await asyncio.to_thread(process_due_reminder_emails)
            if sent_count:
                logger.info(
                    "Email worker sent %s due reminder email(s).",
                    sent_count,
                )
        except Exception:
            logger.exception("Reminder email worker iteration failed.")
        try:
            sent_count = await asyncio.to_thread(process_due_notification_emails)
            if sent_count:
                logger.info(
                    "Email worker sent %s due notification email(s).",
                    sent_count,
                )
        except Exception:
            logger.exception("Notification email worker iteration failed.")
        await asyncio.sleep(settings.EMAIL_WORKER_INTERVAL_SECONDS)
