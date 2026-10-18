from datetime import datetime, timedelta, timezone
from email import policy
from email import message_from_bytes
import base64

import httpx
import pytest

from app.core.config import settings
from app.models.reminder.reminder import Reminder
from app.services import reminder_email_service


def test_missing_gmail_configuration_lists_required_settings(monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", None)
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", None)
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", None)
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", None)

    assert reminder_email_service.missing_reminder_email_settings() == (
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
        "GMAIL_REFRESH_TOKEN",
        "GMAIL_FROM_EMAIL or GMAIL_USER",
    )
    assert not reminder_email_service.reminder_email_is_configured()


def test_reminder_email_uses_gmail_oauth_and_saved_recipient(monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    captured = []

    def fake_post(url, **kwargs):
        captured.append((url, kwargs))
        if url == reminder_email_service.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "access-token"})
        return httpx.Response(200, json={"id": "gmail-message-id"})

    monkeypatch.setattr(reminder_email_service.httpx, "post", fake_post)
    reminder = Reminder(
        id=21,
        title="Check in",
        description="Use the hotel confirmation.",
        due_date=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc),
    )
    reminder.trip = None

    assert (
        reminder_email_service.send_reminder_email(
            "traveler@example.com",
            reminder,
        )
        == "sent"
    )
    assert captured[0][0] == reminder_email_service.GOOGLE_TOKEN_URL
    assert captured[0][1]["data"]["refresh_token"] == "refresh-token"
    assert captured[1][0] == reminder_email_service.GMAIL_SEND_URL
    assert captured[1][1]["headers"]["Authorization"] == "Bearer access-token"
    raw_message = captured[1][1]["json"]["raw"]
    decoded = base64.urlsafe_b64decode(raw_message + "===")
    parsed_message = message_from_bytes(decoded, policy=policy.default)
    assert parsed_message["To"] == "traveler@example.com"
    assert parsed_message["From"] == "Komsan <sender@gmail.com>"
    plain_text = parsed_message.get_body(preferencelist=("plain",)).get_content()
    assert parsed_message["Subject"] == "Reminder due: Check in"
    assert 'Your reminder "Check in" is due now.' in plain_text
    assert "Due: Oct 16, 2026, 09:30 PM Cambodia time (UTC+07:00)" in plain_text
    assert "Open Komsan to view the reminder details." in plain_text
    assert "Komsan | Travel planner: http://localhost:5173" in plain_text
    assert "Use the hotel confirmation." not in plain_text
    html_body = parsed_message.get_body(preferencelist=("html",)).get_content()
    assert '<a href="http://localhost:5173">Komsan | Travel planner</a>' in html_body
    assert parsed_message.get_content_type() == "multipart/alternative"


def test_gmail_403_logs_google_error_details(monkeypatch, caplog):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")

    def fake_post(url, **kwargs):
        if url == reminder_email_service.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "access-token"})
        return httpx.Response(
            403,
            json={
                "error": {
                    "code": 403,
                    "message": "Insufficient Permission",
                    "status": "PERMISSION_DENIED",
                    "errors": [
                        {
                            "reason": "insufficientPermissions",
                        }
                    ],
                }
            },
        )

    monkeypatch.setattr(reminder_email_service.httpx, "post", fake_post)
    reminder = Reminder(
        id=3,
        title="Check in",
        due_date=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc),
    )
    reminder.trip = None

    with caplog.at_level("ERROR", logger=reminder_email_service.__name__):
        result = reminder_email_service.send_reminder_email(
            "traveler@example.com",
            reminder,
        )

    assert result == "failed"
    assert "HTTP 403" in caplog.text
    assert "insufficientPermissions" in caplog.text
    assert "PERMISSION_DENIED" in caplog.text
    assert "Insufficient Permission" in caplog.text


def test_due_reminder_email_retries_and_sends_once(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
):
    due_date = datetime.now(timezone.utc) - timedelta(minutes=1)
    created = client.post(
        "/api/v1/reminders",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Check in",
            "description": "Use the hotel booking confirmation.",
            "due_date": due_date.isoformat(),
            "type": "booking",
        },
    )
    assert created.status_code == 201
    reminder_id = created.json()["id"]

    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    attempts = []

    def fail_once(email, reminder):
        attempts.append((email, reminder.title))
        return "failed" if len(attempts) == 1 else "sent"

    monkeypatch.setattr(
        reminder_email_service,
        "send_reminder_email",
        fail_once,
    )

    assert reminder_email_service.process_due_reminder_emails() == 0
    assert reminder_email_service.process_due_reminder_emails() == 1
    assert reminder_email_service.process_due_reminder_emails() == 0
    assert attempts == [
        ("traveler@example.com", "Check in"),
        ("traveler@example.com", "Check in"),
    ]

    listed = client.get("/api/v1/reminders", headers=auth_headers)
    delivered = next(item for item in listed.json() if item["id"] == reminder_id)
    assert delivered["status"] == "pending"
    assert delivered["email_sent_at"] is not None

    from app.core.database import SessionLocal
    from app.models.reminder.reminder import Reminder

    with SessionLocal() as db:
        reminder = db.query(Reminder).filter_by(id=reminder_id).one()
        assert reminder.email_sent_at is not None
        assert reminder.email_claimed_at is None


def test_due_reminder_email_goes_to_the_account_that_created_it(
    client,
    monkeypatch,
):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "second-traveler@example.com",
            "password": "secure-pass-123",
            "full_name": "Second Traveler",
        },
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "second-traveler@example.com",
            "password": "secure-pass-123",
        },
    )
    second_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
    }
    destination = client.post(
        "/api/v1/destinations",
        headers=second_headers,
        json={
            "name": "Seoul",
            "country": "South Korea",
            "country_code": "KR",
            "average_daily_cost_usd": 100,
        },
    )
    assert destination.status_code == 201
    trip = client.post(
        "/api/v1/trips",
        headers=second_headers,
        json={
            "destination_id": destination.json()["id"],
            "name": "Seoul trip",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "currency": "KRW",
        },
    )
    assert trip.status_code == 201
    reminder = client.post(
        "/api/v1/reminders",
        headers=second_headers,
        json={
            "trip_id": trip.json()["id"],
            "title": "Second account reminder",
            "due_date": (
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ).isoformat(),
            "type": "activity",
        },
    )
    assert reminder.status_code == 201

    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    recipients = []
    monkeypatch.setattr(
        reminder_email_service,
        "send_reminder_email",
        lambda email, _reminder: recipients.append(email) or "sent",
    )

    assert reminder_email_service.process_due_reminder_emails() == 1
    assert recipients == ["second-traveler@example.com"]


def test_due_reminder_email_is_sent_if_completed_after_due(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
):
    due_date = datetime.now(timezone.utc) - timedelta(minutes=1)
    created = client.post(
        "/api/v1/reminders",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Check in",
            "due_date": due_date.isoformat(),
            "type": "booking",
        },
    )
    assert created.status_code == 201
    reminder_id = created.json()["id"]

    completed = client.patch(
        f"/api/v1/reminders/{reminder_id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200

    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    attempts = []

    def send(email, reminder):
        attempts.append((email, reminder.title))
        return "sent"

    monkeypatch.setattr(reminder_email_service, "send_reminder_email", send)

    assert reminder_email_service.process_due_reminder_emails() == 1
    assert reminder_email_service.process_due_reminder_emails() == 0
    assert attempts == [("traveler@example.com", "Check in")]

    from app.core.database import SessionLocal
    from app.models.reminder.reminder import Reminder

    with SessionLocal() as db:
        reminder = db.query(Reminder).filter_by(id=reminder_id).one()
        assert reminder.status.value == "completed"
        assert reminder.email_sent_at is not None
        assert reminder.email_claimed_at is None


def test_cancelled_due_reminder_is_not_emailed(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
):
    due_date = datetime.now(timezone.utc) - timedelta(minutes=1)
    created = client.post(
        "/api/v1/reminders",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Cancelled booking",
            "due_date": due_date.isoformat(),
            "type": "booking",
            "status": "cancelled",
        },
    )
    assert created.status_code == 201

    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    monkeypatch.setattr(
        reminder_email_service,
        "send_reminder_email",
        lambda email, reminder: pytest.fail("cancelled reminder was emailed"),
    )

    assert reminder_email_service.process_due_reminder_emails() == 0


def test_completed_before_due_reminder_is_not_emailed(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
):
    due_date = datetime.now(timezone.utc) + timedelta(minutes=1)
    created = client.post(
        "/api/v1/reminders",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Completed booking",
            "due_date": due_date.isoformat(),
            "type": "booking",
        },
    )
    assert created.status_code == 201
    reminder_id = created.json()["id"]

    completed = client.patch(
        f"/api/v1/reminders/{reminder_id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200

    from app.core.database import SessionLocal
    from app.models.reminder.reminder import Reminder

    with SessionLocal() as db:
        reminder = db.query(Reminder).filter_by(id=reminder_id).one()
        now = datetime.now(timezone.utc)
        reminder.completed_at = now - timedelta(minutes=2)
        reminder.due_date = now - timedelta(minutes=1)
        db.commit()

    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "oauth-client-id")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "GMAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "GMAIL_USER", "sender@gmail.com")
    monkeypatch.setattr(
        reminder_email_service,
        "send_reminder_email",
        lambda email, reminder: pytest.fail("early-completed reminder was emailed"),
    )

    assert reminder_email_service.process_due_reminder_emails() == 0
