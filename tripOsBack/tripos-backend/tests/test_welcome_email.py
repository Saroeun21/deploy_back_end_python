from base64 import urlsafe_b64decode
from email import message_from_bytes, policy

import httpx

from app.core.config import settings
from app.services import welcome_email_service


def test_welcome_email_reports_missing_gmail_configuration(monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", None)
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", None)
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", None)
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", None)

    assert welcome_email_service.send_welcome_email(
        "traveler@example.com",
        "Traveler",
    ) == "not_configured"


def test_welcome_email_sends_using_gmail_oauth(monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    requested = []

    def fake_post(url, **kwargs):
        requested.append((url, kwargs))
        if url == welcome_email_service.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "access-token"})
        return httpx.Response(200, json={"id": "gmail-message-id"})

    monkeypatch.setattr(welcome_email_service.httpx, "post", fake_post)

    assert welcome_email_service.send_welcome_email(
        "traveler@example.com",
        "Traveler",
    ) == "sent"
    assert requested[0][0] == welcome_email_service.GOOGLE_TOKEN_URL
    assert requested[0][1]["data"]["refresh_token"] == "refresh-token"
    assert requested[1][0] == welcome_email_service.GMAIL_SEND_URL
    assert requested[1][1]["headers"]["Authorization"] == "Bearer access-token"
    raw_message = requested[1][1]["json"]["raw"]
    decoded_message = urlsafe_b64decode(raw_message + "===")
    parsed_message = message_from_bytes(decoded_message, policy=policy.default)
    assert parsed_message["To"] == "traveler@example.com"
    assert parsed_message["From"] == "Komsan <sender@gmail.com>"
    assert parsed_message["Subject"] == "Welcome to Komsan"
    assert "Welcome to Komsan! Your account is ready." in (
        parsed_message.get_body(preferencelist=("plain",)).get_content()
    )
    html_body = parsed_message.get_body(preferencelist=("html",)).get_content()
    assert '<a href="http://localhost:5173">Komsan | Travel planner</a>' in html_body


def test_welcome_back_email_has_distinct_subject(monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", "sender@gmail.com")
    requested = []

    def fake_post(url, **kwargs):
        requested.append((url, kwargs))
        if url == welcome_email_service.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "access-token"})
        return httpx.Response(200, json={"id": "gmail-message-id"})

    monkeypatch.setattr(welcome_email_service.httpx, "post", fake_post)

    assert welcome_email_service.send_welcome_email(
        "traveler@example.com",
        "Traveler",
        is_returning_user=True,
    ) == "sent"
    raw_message = requested[1][1]["json"]["raw"]
    parsed_message = message_from_bytes(
        urlsafe_b64decode(raw_message + "==="),
        policy=policy.default,
    )
    assert parsed_message["Subject"] == "Welcome back to Komsan"
    assert "Welcome back to Komsan!" in (
        parsed_message.get_body(preferencelist=("plain",)).get_content()
    )


def test_welcome_email_reports_gmail_rejection(monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", "sender@gmail.com")

    def fake_post(url, **kwargs):
        if url == welcome_email_service.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "access-token"})
        return httpx.Response(403)

    monkeypatch.setattr(welcome_email_service.httpx, "post", fake_post)

    assert welcome_email_service.send_welcome_email(
        "traveler@example.com",
        "Traveler",
    ) == "failed"


def test_welcome_email_logs_gmail_permission_rejection(monkeypatch, caplog):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")

    def fake_post(url, **kwargs):
        if url == welcome_email_service.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "access-token"})
        return httpx.Response(
            403,
            json={
                "error": {
                    "status": "PERMISSION_DENIED",
                    "message": "Insufficient Permission",
                }
            },
        )

    monkeypatch.setattr(welcome_email_service.httpx, "post", fake_post)

    with caplog.at_level("ERROR", logger=welcome_email_service.__name__):
        result = welcome_email_service.send_welcome_email(
            "traveler@example.com",
            "Traveler",
        )

    assert result == "failed"
    assert "HTTP 403" in caplog.text
    assert "PERMISSION_DENIED" in caplog.text
    assert "Insufficient Permission" in caplog.text


def test_welcome_email_logs_oauth_refresh_error(monkeypatch, caplog):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    monkeypatch.setattr(
        welcome_email_service.httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": "Bad Request",
            },
        ),
    )

    with caplog.at_level("ERROR", logger=welcome_email_service.__name__):
        result = welcome_email_service.send_welcome_email(
            "traveler@example.com",
            "Traveler",
        )

    assert result == "failed"
    assert "HTTP 400" in caplog.text
    assert "invalid_grant" in caplog.text
    assert "Bad Request" in caplog.text
