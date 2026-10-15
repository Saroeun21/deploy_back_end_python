from app.core.database import SessionLocal
from app.models.user.user import User


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
