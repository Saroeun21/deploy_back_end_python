import base64
from collections.abc import Mapping
from email.message import EmailMessage
from html import escape
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import and_, or_

from app.core.config import settings
from app.models.reminder.reminder import Reminder, ReminderStatus

logger = logging.getLogger(__name__)

ReminderEmailStatus = Literal["sent", "failed"]
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
CAMBODIA_TIMEZONE = ZoneInfo("Asia/Phnom_Penh")


def _google_api_error_details(
    response: httpx.Response,
) -> tuple[str | None, str | None, str | None]:
    try:
        payload = response.json()
    except ValueError:
        return None, None, None

    if not isinstance(payload, Mapping):
        return None, None, None
    error = payload.get("error")
    if not isinstance(error, Mapping):
        return None, None, None

    reason = None
    for errors_key in ("errors", "details"):
        errors = error.get(errors_key)
        if not isinstance(errors, list):
            continue
        for item in errors:
            if isinstance(item, Mapping) and isinstance(item.get("reason"), str):
                reason = item["reason"]
                break
        if reason is not None:
            break

    status = error.get("status")
    message = error.get("message")
    return (
        reason[:100] if reason else None,
        status[:100] if isinstance(status, str) else None,
        message[:500] if isinstance(message, str) else None,
    )


def send_reminder_email(email: str, reminder: Reminder) -> ReminderEmailStatus:
    client_id = settings.GMAIL_CLIENT_ID
    client_secret = settings.GMAIL_CLIENT_SECRET
    refresh_token = settings.GMAIL_REFRESH_TOKEN
    from_email = settings.GMAIL_FROM_EMAIL or settings.GMAIL_USER
    if not all((client_id, client_secret, refresh_token, from_email)):
        logger.warning(
            "Reminder email delivery is skipped because Gmail API OAuth is not configured."
        )
        return "failed"

    due_date = reminder.due_date
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    local_due_date = due_date.astimezone(CAMBODIA_TIMEZONE)
    due_date_text = (
        f"{local_due_date.strftime('%b %d, %Y, %I:%M %p')} "
        "Cambodia time (UTC+07:00)"
    )
    message = EmailMessage()
    message["To"] = email
    message["From"] = f"{settings.GMAIL_FROM_NAME} <{from_email}>"
    message["Subject"] = f"Reminder due: {reminder.title}"
    website_url = settings.WEBSITE_URL.rstrip("/")
    message.set_content(
        f'Your reminder "{reminder.title}" is due now.\n'
        f"Due: {due_date_text}\n\n"
        "Open Komsan to view the reminder details.\n\n"
        f"Komsan | Travel planner: {website_url}"
    )
    message.add_alternative(
        f"""<html><body>
<p>Your reminder &quot;{escape(reminder.title)}&quot; is due now.<br>
Due: {escape(due_date_text)}</p>
<p>Open Komsan to view the reminder details.</p>
<p><a href="{escape(website_url, quote=True)}">Komsan | Travel planner</a></p>
</body></html>""",
        subtype="html",
    )

    try:
        token_response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
    except httpx.RequestError as error:
        logger.error(
            "Gmail OAuth token request failed (%s).",
            type(error).__name__,
        )
        return "failed"

    if token_response.status_code != 200:
        logger.error(
            "Google OAuth rejected the Gmail token refresh (HTTP %s).",
            token_response.status_code,
        )
        return "failed"
    access_token = token_response.json().get("access_token")
    if not access_token:
        logger.error("Google OAuth token refresh returned no access token.")
        return "failed"

    try:
        response = httpx.post(
            GMAIL_SEND_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "raw": base64.urlsafe_b64encode(message.as_bytes())
                .decode("ascii")
                .rstrip("=")
            },
            timeout=10,
        )
    except httpx.RequestError as error:
        logger.error(
            "Gmail API reminder send request failed (%s).",
            type(error).__name__,
        )
        return "failed"

    if response.status_code != 200:
        reason, google_status, message = _google_api_error_details(response)
        logger.error(
            "Gmail API rejected reminder email %s (HTTP %s, reason=%s, "
            "status=%s, message=%s).",
            reminder.id,
            response.status_code,
            reason or "unknown",
            google_status or "unknown",
            message or "no error message returned",
        )
        return "failed"
    return "sent"


def reminder_email_is_configured() -> bool:
    return not missing_reminder_email_settings()


def missing_reminder_email_settings() -> tuple[str, ...]:
    required_settings = (
        ("GMAIL_CLIENT_ID", settings.GMAIL_CLIENT_ID),
        ("GMAIL_CLIENT_SECRET", settings.GMAIL_CLIENT_SECRET),
        ("GMAIL_REFRESH_TOKEN", settings.GMAIL_REFRESH_TOKEN),
        ("GMAIL_FROM_EMAIL or GMAIL_USER", settings.GMAIL_FROM_EMAIL or settings.GMAIL_USER),
    )
    return tuple(name for name, value in required_settings if not value)


def _email_eligible_reminder_filter():
    return or_(
        Reminder.status == ReminderStatus.PENDING,
        and_(
            Reminder.status == ReminderStatus.COMPLETED,
            Reminder.completed_at >= Reminder.due_date,
        ),
    )


def _claim_due_reminder_ids(
    now: datetime,
    limit: int,
) -> list[int]:
    from app.core.database import SessionLocal
    stale_claim_cutoff = now - timedelta(minutes=10)
    with SessionLocal() as db:
        candidates = (
            db.query(Reminder.id)
            .filter(
                _email_eligible_reminder_filter(),
                Reminder.due_date <= now,
                Reminder.email_sent_at.is_(None),
                or_(
                    Reminder.email_claimed_at.is_(None),
                    Reminder.email_claimed_at < stale_claim_cutoff,
                ),
            )
            .order_by(Reminder.due_date, Reminder.id)
            .limit(limit)
            .all()
        )
        claimed_ids = []
        for (reminder_id,) in candidates:
            claimed = (
                db.query(Reminder)
                .filter(
                    Reminder.id == reminder_id,
                    _email_eligible_reminder_filter(),
                    Reminder.due_date <= now,
                    Reminder.email_sent_at.is_(None),
                    or_(
                        Reminder.email_claimed_at.is_(None),
                        Reminder.email_claimed_at < stale_claim_cutoff,
                    ),
                )
                .update(
                    {Reminder.email_claimed_at: now},
                    synchronize_session=False,
                )
            )
            if claimed:
                claimed_ids.append(reminder_id)
        db.commit()
        return claimed_ids


def process_due_reminder_emails(limit: int = 50) -> int:
    if not reminder_email_is_configured():
        return 0

    from app.core.database import SessionLocal
    from app.models.user.user import User

    now = datetime.now(timezone.utc)
    reminder_ids = _claim_due_reminder_ids(now, limit)
    sent_count = 0
    for reminder_id in reminder_ids:
        with SessionLocal() as db:
            reminder = (
                db.query(Reminder)
                .filter(
                    Reminder.id == reminder_id,
                    _email_eligible_reminder_filter(),
                    Reminder.email_sent_at.is_(None),
                )
                .first()
            )
            if reminder is None:
                db.query(Reminder).filter(
                    Reminder.id == reminder_id,
                ).update(
                    {Reminder.email_claimed_at: None},
                    synchronize_session=False,
                )
                db.commit()
                continue
            recipient = (
                db.query(User.email)
                .filter(User.id == reminder.user_id)
                .scalar()
            )
            status = (
                send_reminder_email(recipient, reminder)
                if recipient
                else "failed"
            )
            if status == "sent":
                reminder.email_sent_at = now
                sent_count += 1
            reminder.email_claimed_at = None
            if not recipient:
                logger.error(
                    "Reminder %s has no recipient account email.",
                    reminder.id,
                )
            db.commit()
    return sent_count
