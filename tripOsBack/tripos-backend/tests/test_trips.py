def test_create_trip_with_uploaded_cover_image(
    client, auth_headers, destination_id, monkeypatch, tmp_path
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    image_bytes = b"\x89PNG\r\n\x1a\ntrip-cover-content"

    created = client.post(
        "/api/v1/trips",
        headers=auth_headers,
        data={
            "destination_id": str(destination_id),
            "name": "Tokyo with cover",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "currency": "JPY",
            "data": '{"travelers": 2}',
        },
        files={"cover_image": ("cover.png", image_bytes, "image/png")},
    )

    assert created.status_code == 201
    trip = created.json()
    assert trip["cover_image"] == f"/api/v1/trips/{trip['id']}/cover-image"

    image_response = client.get(trip["cover_image"], headers=auth_headers)
    assert image_response.status_code == 200
    assert image_response.content == image_bytes


def test_create_trip_rejects_cover_image_url(client, auth_headers, destination_id):
    response = client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Tokyo with remote cover",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "currency": "JPY",
            "cover_image": "https://example.com/cover.jpg",
        },
    )

    assert response.status_code == 422
    assert "cover_image as a file" in response.json()["detail"]


def test_create_and_list_trips(client, auth_headers, destination_id):
    created = client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Tokyo",
            "description": "Spring trip",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "currency": "JPY",
        },
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Tokyo"

    listed = client.get("/api/v1/trips", headers=auth_headers)
    assert [trip["id"] for trip in listed.json()] == [created.json()["id"]]


def test_user_can_plan_trip_to_another_users_public_destination(
    client, auth_headers, destination_id
):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "another-traveler@example.com",
            "password": "secure-pass-456",
            "name": "Another Traveler",
        },
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "another-traveler@example.com",
            "password": "secure-pass-456",
        },
    )
    assert login.status_code == 200
    other_user_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    created = client.post(
        "/api/v1/trips",
        headers=other_user_headers,
        json={
            "destination_id": destination_id,
            "name": "A public destination trip",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "currency": "JPY",
        },
    )

    assert created.status_code == 201
    assert created.json()["destination_id"] == destination_id
    assert client.get("/api/v1/trips", headers=auth_headers).json() == []
    assert client.get("/api/v1/trips", headers=other_user_headers).json() == [
        created.json()
    ]


def test_create_trip_with_legacy_amount_status_and_extra_data(
    client, auth_headers, destination_id
):
    created = client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Phnom Penh Weekend Trip",
            "description": "A three-day cultural trip.",
            "data": {"destination": "Phnom Penh", "country": "Cambodia"},
            "start_date": "2026-10-10",
            "end_date": "2026-10-12",
            "status": "planned",
            "amount": 250,
            "balance": 85.5,
            "currency": "USD",
            "category": "Travel",
            "spent_on": "2026-10-10",
            "travelers": 2,
            "transport": "Tuk Tuk",
            "accommodation": "Hotel",
            "places": ["Royal Palace", "Wat Phnom", "Central Market"],
        },
    )

    assert created.status_code == 201
    trip = created.json()
    assert trip["budget_amount"] == "250.00"
    assert trip["status"] == "planning"
    assert trip["data"] == {
        "destination": "Phnom Penh",
        "country": "Cambodia",
        "balance": 85.5,
        "category": "Travel",
        "spent_on": "2026-10-10",
        "travelers": 2,
        "transport": "Tuk Tuk",
        "accommodation": "Hotel",
        "places": ["Royal Palace", "Wat Phnom", "Central Market"],
    }
