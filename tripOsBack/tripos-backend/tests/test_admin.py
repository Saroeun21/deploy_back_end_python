from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.ai.ai_extraction import AIExtraction, AIExtractionStatus
from app.models.ai.ai_conversation import AIConversation
from app.models.ai.ai_message import AIMessage, AIMessageRole
from app.models.destination.destination import Destination
from app.models.itinerary.itinerary_day import ItineraryDay
from app.models.itinerary.itinerary_item import ItineraryItem, ItineraryItemType
from app.models.trip.trip import Trip
from app.models.user.user import User
from app.services.user_avatar_service import user_avatar_path


def test_admin_dashboard_requires_authentication(client):
    response = client.get("/api/v1/admin/dashboard")

    assert response.status_code == 401


def test_admin_dashboard_rejects_non_admin_users(client, auth_headers):
    response = client.get("/api/v1/admin/dashboard", headers=auth_headers)

    assert response.status_code == 403


def test_admin_dashboard_returns_database_counts(client, admin_headers):
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {
        "statistics": {
            "total_registered_travelers": 1,
            "active_trips_managed": 0,
            "ai_screenshot_parse_jobs": 0,
            "destination_catalog": 0,
            "place_catalog": 0,
        }
    }


def test_admin_dashboard_analytics_requires_admin(client, auth_headers):
    assert client.get("/api/v1/admin/dashboard/analytics").status_code == 401
    response = client.get(
        "/api/v1/admin/dashboard/analytics",
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_admin_dashboard_analytics_aggregates_trip_and_ocr_records(
    client,
    admin_headers,
    trip_id,
):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        trip = db.get(Trip, trip_id)
        trip.created_at = now
        day = ItineraryDay(
            trip_id=trip_id,
            day_number=1,
            date=now.date(),
            title="First day",
        )
        db.add(day)
        db.flush()
        db.add(
            ItineraryItem(
                itinerary_day_id=day.id,
                title="Visit the city",
                type=ItineraryItemType.ACTIVITY,
                order_index=0,
            )
        )
        db.add_all(
            [
                AIExtraction(
                    user_id=trip.user_id,
                    trip_id=trip_id,
                    type="flight_boarding_pass",
                    extracted_data={"booking": {"kind": "flight"}},
                    status=AIExtractionStatus.COMPLETED,
                ),
                AIExtraction(
                    user_id=trip.user_id,
                    trip_id=trip_id,
                    type="expense_receipt",
                    extracted_data={"expense": {"amount": 42}},
                    status=AIExtractionStatus.COMPLETED,
                    requires_human_review=True,
                ),
                AIExtraction(
                    user_id=trip.user_id,
                    trip_id=trip_id,
                    type="flight_boarding_pass",
                    extracted_data={},
                    status=AIExtractionStatus.PENDING,
                ),
            ]
        )
        db.commit()

    response = client.get(
        "/api/v1/admin/dashboard/analytics",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    analytics = response.json()
    lifecycle = analytics["trip_lifecycle"]
    month = next(
        item for item in lifecycle["months"]
        if item["month"] == now.strftime("%Y-%m")
    )
    assert len(lifecycle["months"]) == 7
    assert month["regions"]["east_asia"] == {"trips": 1, "itinerary_items": 1}
    assert lifecycle["top_destinations"] == [{"name": "Japan", "trips": 1}]

    ocr = analytics["ocr_model_stats"]
    assert ocr["total_documents"] == 2
    assert {item["key"]: item["count"] for item in ocr["categories"]} == {
        "flight": 1,
        "hotel": 0,
        "transit": 0,
        "expense": 1,
        "other": 0,
    }
    assert ocr["human_review_count"] == 1
    assert ocr["human_review_rate"] == 50.0


def test_admin_can_load_paginated_users_and_catalogs(
    client, admin_headers, auth_headers, destination_id
):
    place = client.post(
        "/api/v1/places",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Wat Phnom",
            "category": "temple",
        },
    )
    assert place.status_code == 201

    users = client.get(
        "/api/v1/admin/users?page=1&page_size=10&search=traveler",
        headers=admin_headers,
    )
    destinations = client.get(
        "/api/v1/admin/destinations?page=1&page_size=100",
        headers=admin_headers,
    )
    places = client.get(
        "/api/v1/admin/places?page=1&page_size=100",
        headers=admin_headers,
    )

    assert users.status_code == 200
    assert users.json()["total"] == 1
    assert users.json()["items"][0]["email"] == "traveler@example.com"
    assert destinations.status_code == 200
    assert destinations.json()["total"] == 1
    assert destinations.json()["items"][0]["id"] == destination_id
    assert places.status_code == 200
    assert places.json()["total"] == 1
    assert places.json()["items"][0]["id"] == place.json()["id"]


def test_admin_catalog_lists_can_return_recent_saved_records(
    client,
    admin_headers,
    auth_headers,
    destination_id,
):
    first_destination = client.post(
        "/api/v1/destinations",
        headers=auth_headers,
        json={
            "name": "First saved",
            "country": "Thailand",
            "country_code": "TH",
        },
    )
    second_destination = client.post(
        "/api/v1/destinations",
        headers=auth_headers,
        json={
            "name": "Second saved",
            "country": "Japan",
            "country_code": "JP",
        },
    )
    assert first_destination.status_code == 201
    assert second_destination.status_code == 201
    first_place = client.post(
        "/api/v1/places",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "First saved place",
            "category": "museum",
        },
    )
    second_place = client.post(
        "/api/v1/places",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Second saved place",
            "category": "park",
        },
    )
    assert first_place.status_code == 201
    assert second_place.status_code == 201

    recent_destinations = client.get(
        "/api/v1/admin/destinations?page=1&page_size=2&recent=true",
        headers=admin_headers,
    )
    recent_places = client.get(
        "/api/v1/admin/places?page=1&page_size=1&recent=true",
        headers=admin_headers,
    )

    assert recent_destinations.status_code == 200
    assert [item["id"] for item in recent_destinations.json()["items"]] == [
        second_destination.json()["id"],
        first_destination.json()["id"],
    ]
    assert recent_places.status_code == 200
    assert recent_places.json()["items"][0]["id"] == second_place.json()["id"]


def test_admin_user_list_rejects_non_admin_users(client, auth_headers):
    response = client.get("/api/v1/admin/users?page=1&page_size=10", headers=auth_headers)

    assert response.status_code == 403


def test_admin_user_list_supports_seeded_non_email_accounts(
    client, admin_headers
):
    with SessionLocal() as db:
        user = User(
            email="public-catalog@tripos.local",
            name="Public catalog",
            hashed_password="not-used-for-login",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    listed = client.get("/api/v1/admin/users?page=1&page_size=10", headers=admin_headers)
    detail = client.get(f"/api/v1/admin/users/{user_id}", headers=admin_headers)

    assert listed.status_code == 200
    assert any(
        item["email"] == "public-catalog@tripos.local"
        for item in listed.json()["items"]
    )
    assert detail.status_code == 200
    assert detail.json()["email"] == "public-catalog@tripos.local"


def test_admin_can_update_user_status_with_dashboard_values(
    client, auth_headers, admin_headers
):
    user = client.get("/api/v1/users/me", headers=auth_headers)
    user_id = user.json()["id"]

    suspended = client.patch(
        f"/api/v1/admin/users/{user_id}",
        headers=admin_headers,
        json={"status": "suspended"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] is False

    activated = client.patch(
        f"/api/v1/admin/users/{user_id}",
        headers=admin_headers,
        json={"status": "active"},
    )
    assert activated.status_code == 200
    assert activated.json()["status"] is True


def test_admin_rejects_unknown_user_status(client, auth_headers, admin_headers):
    user_id = client.get("/api/v1/users/me", headers=auth_headers).json()["id"]

    response = client.patch(
        f"/api/v1/admin/users/{user_id}",
        headers=admin_headers,
        json={"status": "waiting"},
    )

    assert response.status_code == 422


def test_admin_can_delete_user_and_their_trip_data_but_preserves_catalog(
    client, auth_headers, admin_headers, trip_id, destination_id, monkeypatch, tmp_path
):
    user_id = client.get("/api/v1/users/me", headers=auth_headers).json()["id"]
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    avatar_filename = f"{'a' * 32}.png"
    avatar_path = user_avatar_path(avatar_filename)
    avatar_path.parent.mkdir(parents=True)
    avatar_path.write_bytes(b"avatar")

    with SessionLocal() as db:
        user = db.get(User, user_id)
        user.avatar_filename = avatar_filename
        conversation = AIConversation(
            user_id=user_id,
            trip_id=trip_id,
            title="Trip planning",
        )
        db.add(conversation)
        db.flush()
        db.add(
            AIMessage(
                conversation_id=conversation.id,
                role=AIMessageRole.USER,
                message="Plan this trip",
            )
        )
        db.commit()

    response = client.delete(
        f"/api/v1/admin/users/{user_id}",
        headers=admin_headers,
    )

    assert response.status_code == 204
    with SessionLocal() as db:
        assert db.get(User, user_id) is None
        assert db.query(Trip).filter(Trip.user_id == user_id).count() == 0
        assert db.query(AIConversation).filter(AIConversation.user_id == user_id).count() == 0
        assert db.query(AIMessage).count() == 0
        destination = db.get(Destination, destination_id)
        assert destination is not None
        assert destination.user_id is None
    assert not avatar_path.exists()


def test_admin_cannot_delete_own_account(client, admin_headers):
    users = client.get(
        "/api/v1/admin/users?page=1&page_size=10",
        headers=admin_headers,
    ).json()["items"]
    admin_id = next(user["id"] for user in users if user["email"] == "admin@example.com")

    response = client.delete(
        f"/api/v1/admin/users/{admin_id}",
        headers=admin_headers,
    )

    assert response.status_code == 409


def test_user_deletion_requires_admin(client, auth_headers):
    response = client.delete("/api/v1/admin/users/1", headers=auth_headers)

    assert response.status_code == 403
