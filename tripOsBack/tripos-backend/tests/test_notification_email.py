from base64 import urlsafe_b64decode
from datetime import datetime, timedelta, timezone
from email import message_from_bytes, policy

import httpx
import pytest

from app.core.config import settings
from app.services import gmail_email_service, notification_email_service


def test_notification_email_uses_gmail_oauth(monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    requested = []

    def fake_post(url, **kwargs):
        requested.append((url, kwargs))
        if url == gmail_email_service.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "access-token"})
        return httpx.Response(200, json={"id": "gmail-message-id"})

    monkeypatch.setattr(gmail_email_service.httpx, "post", fake_post)
    notification = type(
        "Notification",
        (),
        {
            "id": 12,
            "title": "Trip update",
            "message": "Your itinerary is ready.",
            "due_date": datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc),
        },
    )()

    assert (
        notification_email_service.send_notification_email(
            "traveler@example.com",
            notification,
        )
        == "sent"
    )
    assert requested[0][0] == gmail_email_service.GOOGLE_TOKEN_URL
    assert requested[0][1]["data"]["refresh_token"] == "refresh-token"
    assert requested[1][0] == gmail_email_service.GMAIL_SEND_URL
    assert requested[1][1]["headers"]["Authorization"] == "Bearer access-token"
    raw_message = requested[1][1]["json"]["raw"]
    parsed = message_from_bytes(
        urlsafe_b64decode(raw_message + "==="),
        policy=policy.default,
    )
    assert parsed["To"] == "traveler@example.com"
    assert parsed["From"] == "Komsan <sender@gmail.com>"
    assert parsed["Subject"] == "Notification: Trip update"
    plain_text = parsed.get_body(preferencelist=("plain",)).get_content()
    assert "Your itinerary is ready." in plain_text
    assert "Due: Oct 16, 2026, 09:30 PM Cambodia time (UTC+07:00)" in plain_text


def test_due_notification_email_retries_and_sends_once(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    attempts = []

    def fail_once(email, notification):
        attempts.append((email, notification.title))
        return "failed" if len(attempts) == 1 else "sent"

    monkeypatch.setattr(
        notification_email_service,
        "send_notification_email",
        fail_once,
    )
    created = client.post(
        "/api/v1/notifications",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Trip update",
            "message": "Your itinerary is ready.",
            "type": "trip",
            "due_date": (
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ).isoformat(),
        },
    )
    assert created.status_code == 201
    notification_id = created.json()["id"]

    assert notification_email_service.process_due_notification_emails() == 0
    assert notification_email_service.process_due_notification_emails() == 1
    assert notification_email_service.process_due_notification_emails() == 0
    assert attempts == [("traveler@example.com", "Trip update")] * 2

    from app.core.database import SessionLocal
    from app.models.notification.notification import Notification

    with SessionLocal() as db:
        notification = db.query(Notification).filter_by(id=notification_id).one()
        assert notification.email_sent_at is not None
        assert notification.email_claimed_at is None


def test_notification_without_due_date_is_not_emailed(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    monkeypatch.setattr(
        notification_email_service,
        "send_notification_email",
        lambda email, notification: pytest.fail(
            "notification without due date was emailed"
        ),
    )
    created = client.post(
        "/api/v1/notifications",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Trip update",
            "message": "Your itinerary is ready.",
            "type": "trip",
        },
    )
    assert created.status_code == 201

    assert notification_email_service.process_due_notification_emails() == 0


def test_changing_notification_due_date_resets_email_delivery(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    attempts = []
    monkeypatch.setattr(
        notification_email_service,
        "send_notification_email",
        lambda email, notification: attempts.append(notification.title) or "sent",
    )
    created = client.post(
        "/api/v1/notifications",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Trip update",
            "message": "Your itinerary is ready.",
            "type": "trip",
            "due_date": (
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ).isoformat(),
        },
    )
    assert created.status_code == 201
    notification_id = created.json()["id"]
    assert notification_email_service.process_due_notification_emails() == 1

    updated = client.patch(
        f"/api/v1/notifications/{notification_id}",
        headers=auth_headers,
        json={
            "due_date": (
                datetime.now(timezone.utc) - timedelta(minutes=2)
            ).isoformat(),
        },
    )
    assert updated.status_code == 200
    assert notification_email_service.process_due_notification_emails() == 1
    assert attempts == ["Trip update", "Trip update"]
