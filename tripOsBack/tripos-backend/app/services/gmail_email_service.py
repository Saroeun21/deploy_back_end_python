import base64
from collections.abc import Mapping
from email.message import EmailMessage
import logging
from typing import Literal

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

EmailSendStatus = Literal["sent", "failed"]
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


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


def send_gmail_message(
    message: EmailMessage,
    email_kind: str,
    record_id: int,
) -> EmailSendStatus:
    client_id = settings.GMAIL_CLIENT_ID
    client_secret = settings.GMAIL_CLIENT_SECRET
    refresh_token = settings.GMAIL_REFRESH_TOKEN
    from_email = settings.GMAIL_FROM_EMAIL or settings.GMAIL_USER
    if not all((client_id, client_secret, refresh_token, from_email)):
        logger.warning(
            "%s email delivery is skipped because Gmail API OAuth is not configured.",
            email_kind,
        )
        return "failed"

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
            "Gmail OAuth token request for %s email failed (%s).",
            email_kind,
            type(error).__name__,
        )
        return "failed"

    if token_response.status_code != 200:
        logger.error(
            "Google OAuth rejected the Gmail token refresh for %s email (HTTP %s).",
            email_kind,
            token_response.status_code,
        )
        return "failed"
    try:
        token_payload = token_response.json()
    except ValueError:
        logger.error(
            "Google OAuth token refresh returned invalid JSON for %s email.",
            email_kind,
        )
        return "failed"
    access_token = (
        token_payload.get("access_token")
        if isinstance(token_payload, Mapping)
        else None
    )
    if not isinstance(access_token, str) or not access_token:
        logger.error(
            "Google OAuth token refresh returned no access token for %s email.",
            email_kind,
        )
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
            "Gmail API %s email request failed (%s).",
            email_kind,
            type(error).__name__,
        )
        return "failed"

    if response.status_code != 200:
        reason, google_status, error_message = _google_api_error_details(response)
        logger.error(
            "Gmail API rejected %s email %s (HTTP %s, reason=%s, "
            "status=%s, message=%s).",
            email_kind,
            record_id,
            response.status_code,
            reason or "unknown",
            google_status or "unknown",
            error_message or "no error message returned",
        )
        return "failed"
    return "sent"
