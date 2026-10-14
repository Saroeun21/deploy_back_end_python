def test_create_and_list_places(client, auth_headers, destination_id):
    created = client.post(
        "/api/v1/places",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Senso-ji",
            "category": "temple",
            "description": "Historic temple in Asakusa",
            "image": "https://example.com/senso-ji.jpg",
            "opening_time": "06:00:00",
            "closing_time": "17:00:00",
        },
    )

    assert created.status_code == 201
    assert created.json()["destination_id"] == destination_id
    assert created.json()["name"] == "Senso-ji"
    assert created.json()["category"] == "temple"
    assert created.json()["image"] == "https://example.com/senso-ji.jpg"

    listed = client.get("/api/v1/places", headers=auth_headers)
    assert [place["id"] for place in listed.json()] == [created.json()["id"]]
