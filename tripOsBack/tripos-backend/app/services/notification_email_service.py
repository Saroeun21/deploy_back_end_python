from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from html import escape
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import or_

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.notification.notification import Notification
from app.models.user.user import User
from app.services.gmail_email_service import EmailSendStatus, send_gmail_message
from app.services.reminder_email_service import reminder_email_is_configured

logger = logging.getLogger(__name__)
CAMBODIA_TIMEZONE = ZoneInfo("Asia/Phnom_Penh")


def send_notification_email(
    email: str,
    notification: Notification,
) -> EmailSendStatus:
    due_date = notification.due_date
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    local_due_date = due_date.astimezone(CAMBODIA_TIMEZONE)
    due_date_text = (
        f"{local_due_date.strftime('%b %d, %Y, %I:%M %p')} "
        "Cambodia time (UTC+07:00)"
    )
    website_url = settings.WEBSITE_URL.rstrip("/")
    message = EmailMessage()
    message["To"] = email
    from_email = settings.GMAIL_FROM_EMAIL or settings.GMAIL_USER
    message["From"] = f"{settings.GMAIL_FROM_NAME} <{from_email}>"
    message["Subject"] = f"Notification: {notification.title}"
    message.set_content(
        f"{notification.title}\n\n"
        f"{notification.message}\n\n"
        f"Due: {due_date_text}\n\n"
        "Open Komsan to view the notification.\n\n"
        f"Komsan | Travel planner: {website_url}"
    )
    message.add_alternative(
        f"""<html><body>
<h2>{escape(notification.title)}</h2>
<p>{escape(notification.message).replace(chr(10), "<br>")}</p>
<p>Due: {escape(due_date_text)}</p>
<p>Open Komsan to view the notification.</p>
<p><a href="{escape(website_url, quote=True)}">Komsan | Travel planner</a></p>
</body></html>""",
        subtype="html",
    )
    return send_gmail_message(message, "notification", notification.id)


def _claim_due_notification_ids(now: datetime, limit: int) -> list[int]:
    stale_claim_cutoff = now - timedelta(minutes=10)
    with SessionLocal() as db:
        candidates = (
            db.query(Notification.id)
            .filter(
                Notification.due_date.is_not(None),
                Notification.due_date <= now,
                Notification.email_sent_at.is_(None),
                or_(
                    Notification.email_claimed_at.is_(None),
                    Notification.email_claimed_at < stale_claim_cutoff,
                ),
            )
            .order_by(Notification.due_date, Notification.id)
            .limit(limit)
            .all()
        )
        claimed_ids = []
        for (notification_id,) in candidates:
            claimed = (
                db.query(Notification)
                .filter(
                    Notification.id == notification_id,
                    Notification.due_date.is_not(None),
                    Notification.due_date <= now,
                    Notification.email_sent_at.is_(None),
                    or_(
                        Notification.email_claimed_at.is_(None),
                        Notification.email_claimed_at < stale_claim_cutoff,
                    ),
                )
                .update(
                    {Notification.email_claimed_at: now},
                    synchronize_session=False,
                )
            )
            if claimed:
                claimed_ids.append(notification_id)
        db.commit()
        return claimed_ids


def process_due_notification_emails(limit: int = 50) -> int:
    if not reminder_email_is_configured():
        return 0

    now = datetime.now(timezone.utc)
    notification_ids = _claim_due_notification_ids(now, limit)
    sent_count = 0
    for notification_id in notification_ids:
        with SessionLocal() as db:
            notification = (
                db.query(Notification)
                .filter(
                    Notification.id == notification_id,
                    Notification.due_date.is_not(None),
                    Notification.email_sent_at.is_(None),
                )
                .first()
            )
            if notification is None:
                db.query(Notification).filter(
                    Notification.id == notification_id,
                ).update(
                    {Notification.email_claimed_at: None},
                    synchronize_session=False,
                )
                db.commit()
                continue
            recipient = (
                db.query(User.email)
                .filter(User.id == notification.user_id)
                .scalar()
            )
            status = (
                send_notification_email(recipient, notification)
                if recipient
                else "failed"
            )
            if status == "sent":
                notification.email_sent_at = now
                sent_count += 1
            notification.email_claimed_at = None
            if not recipient:
                logger.error(
                    "Notification %s has no recipient account email.",
                    notification.id,
                )
            db.commit()
    return sent_count
