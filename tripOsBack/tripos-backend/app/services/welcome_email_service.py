import base64
from collections.abc import Mapping
from html import escape
from email.message import EmailMessage
import logging
from typing import Literal

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WelcomeEmailStatus = Literal["sent", "failed", "not_configured"]
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _response_error_details(
    response: httpx.Response,
) -> tuple[str | None, str | None]:
    try:
        payload = response.json()
    except ValueError:
        return None, None
    if not isinstance(payload, Mapping):
        return None, None

    error = payload.get("error")
    if isinstance(error, Mapping):
        code = error.get("status") or error.get("code")
        description = error.get("message")
        return (
            str(code)[:100] if code is not None else None,
            description[:500] if isinstance(description, str) else None,
        )
    if isinstance(error, str):
        description = payload.get("error_description")
        return (
            error[:100],
            description[:500] if isinstance(description, str) else None,
        )
    return None, None


def send_welcome_email(
    email: str,
    name: str,
    *,
    is_returning_user: bool = False,
) -> WelcomeEmailStatus:
    client_id = settings.GMAIL_CLIENT_ID
    client_secret = settings.GMAIL_CLIENT_SECRET
    refresh_token = settings.GMAIL_REFRESH_TOKEN
    from_email = settings.GMAIL_FROM_EMAIL or settings.GMAIL_USER
    if not all((client_id, client_secret, refresh_token, from_email)):
        logger.warning(
            "Welcome email was not sent because Gmail API OAuth is not configured."
        )
        return "not_configured"

    greeting = f"Hi {name}," if name else "Hello,"
    message = EmailMessage()
    message["To"] = email
    message["From"] = f"{settings.GMAIL_FROM_NAME} <{from_email}>"
    message["Subject"] = (
        "Welcome back to Komsan" if is_returning_user else "Welcome to Komsan"
    )
    website_url = settings.WEBSITE_URL.rstrip("/")
    welcome_message = (
        "Welcome back to Komsan!"
        if is_returning_user
        else "Welcome to Komsan!"
    )
    message.set_content(
        f"{greeting}\n\n"
        f"{welcome_message} Your account is ready. "
        "You can now save places and plan your trips.\n\n"
        "Happy travels,\nThe Komsan team\n\n"
        f"Komsan | Travel planner: {website_url}"
    )
    message.add_alternative(
        f"""<html><body>
<p>{escape(greeting)}</p>
<p>{escape(welcome_message)} Your account is ready. You can now save places and plan your trips.</p>
<p>Happy travels,<br>The Komsan team</p>
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
            "Gmail OAuth token request for welcome email failed (%s).",
            type(error).__name__,
        )
        return "failed"

    if token_response.status_code != 200:
        error_code, error_description = _response_error_details(token_response)
        logger.error(
            "Google OAuth rejected the Gmail token refresh for welcome email "
            "(HTTP %s, error=%s, description=%s).",
            token_response.status_code,
            error_code or "unknown",
            error_description or "no error description returned",
        )
        return "failed"

    try:
        token_payload = token_response.json()
    except ValueError:
        logger.error(
            "Google OAuth token refresh returned invalid JSON for welcome email."
        )
        return "failed"
    access_token = (
        token_payload.get("access_token")
        if isinstance(token_payload, Mapping)
        else None
    )
    if not isinstance(access_token, str) or not access_token:
        logger.error(
            "Google OAuth token refresh returned no access token for welcome email."
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
            "Gmail API welcome email request failed (%s).",
            type(error).__name__,
        )
        return "failed"

    if response.status_code != 200:
        error_code, error_description = _response_error_details(response)
        logger.error(
            "Gmail API rejected welcome email (HTTP %s, error=%s, "
            "description=%s).",
            response.status_code,
            error_code or "unknown",
            error_description or "no error description returned",
        )
        return "failed"
    return "sent"
