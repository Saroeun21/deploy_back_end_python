from datetime import datetime, timezone


def test_create_document_uses_document_fields(client, auth_headers, trip_id):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "name": "Flight ticket",
            "type": "ticket",
            "file_path": "uploads/flight-ticket.pdf",
            "expires_at": "2026-10-20",
        },
    )

    assert response.status_code == 201
    assert response.json()["trip_id"] == trip_id
    assert response.json()["user_id"]
    assert response.json()["expires_at"] == "2026-10-20"


def test_create_memory_uses_memory_fields(client, auth_headers, trip_id):
    response = client.post(
        "/api/v1/memories",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "First day in Phnom Penh",
            "memory_date": "2026-10-10",
            "location": "Central Market",
        },
    )

    assert response.status_code == 201
    assert response.json()["trip_id"] == trip_id
    assert response.json()["user_id"]
    assert response.json()["memory_date"] == "2026-10-10"


def test_create_reminder_uses_reminder_fields(client, auth_headers, trip_id):
    response = client.post(
        "/api/v1/reminders",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Check in to hotel",
            "due_date": "2026-10-14T10:22:00+05:00",
            "type": "booking",
        },
    )

    assert response.status_code == 201
    assert response.json()["trip_id"] == trip_id
    assert response.json()["user_id"]
    assert response.json()["type"] == "booking"
    assert response.json()["status"] == "pending"
    expected_due_date = datetime(2026, 10, 14, 5, 22, tzinfo=timezone.utc)
    assert datetime.fromisoformat(response.json()["due_date"]) == expected_due_date

    listed_reminders = client.get(
        "/api/v1/reminders",
        headers=auth_headers,
    )
    assert listed_reminders.status_code == 200
    assert datetime.fromisoformat(
        listed_reminders.json()[0]["due_date"]
    ) == expected_due_date


def test_create_screenshot_uses_screenshot_fields(client, auth_headers, trip_id):
    response = client.post(
        "/api/v1/screenshots",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "Hotel booking",
            "type": "hotel",
            "image_path": "uploads/hotel.png",
            "extracted_data": {"confirmation": "ABC123"},
        },
    )

    assert response.status_code == 201
    assert response.json()["trip_id"] == trip_id
    assert response.json()["user_id"]
    assert response.json()["extracted_data"] == {"confirmation": "ABC123"}


def test_create_notification_uses_notification_fields(client, auth_headers):
    response = client.post(
        "/api/v1/notifications",
        headers=auth_headers,
        json={
            "title": "Trip reminder",
            "message": "Your trip is coming up.",
            "type": "trip",
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"]
    assert response.json()["is_read"] is False
