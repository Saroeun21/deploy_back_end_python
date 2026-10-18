def test_create_itinerary_with_dates_and_details(client, auth_headers):
    created = client.post(
        "/api/v1/itineraries",
        headers=auth_headers,
        json={
            "name": "Phnom Penh Weekend Trip",
            "description": "A three-day cultural trip.",
            "data": {"destination": "Phnom Penh"},
            "start_date": "2026-10-10",
            "end_date": "2026-10-12",
            "status": "planned",
            "amount": 250,
            "balance": 85.5,
            "currency": "USD",
            "category": "Travel",
            "spent_on": "2026-10-10",
        },
    )

    assert created.status_code == 201
    assert created.json()["name"] == "Phnom Penh Weekend Trip"
    assert created.json()["data"] == {
        "destination": "Phnom Penh",
        "start_date": "2026-10-10",
        "end_date": "2026-10-12",
        "status": "planned",
        "amount": 250,
        "balance": 85.5,
        "currency": "USD",
        "category": "Travel",
        "spent_on": "2026-10-10",
    }


def test_create_itinerary_day_and_item(client, auth_headers, trip_id):
    day = client.post(
        "/api/v1/itinerary-days",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "day_number": 1,
            "date": "2026-10-16",
        },
    )

    assert day.status_code == 201
    assert day.json()["id"] > 0

    item = client.post(
        "/api/v1/itinerary-items",
        headers=auth_headers,
        json={
            "itinerary_day_id": day.json()["id"],
            "title": "Visit the Grand Palace",
            "type": "activity",
            "order_index": 0,
        },
    )

    assert item.status_code == 201
    assert item.json()["id"] > 0
    assert item.json()["itinerary_day_id"] == day.json()["id"]
