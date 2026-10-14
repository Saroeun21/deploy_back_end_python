def test_save_and_remove_destination_and_wikipedia_items(client, auth_headers):
    for item_type, item_key, title in (
        ("destination", "7", "Kyoto, Japan"),
        ("wikipedia", "wiki-123", "Fushimi Inari Taisha"),
    ):
        saved = client.post(
            "/api/v1/saved-items",
            headers=auth_headers,
            json={
                "item_type": item_type,
                "item_key": item_key,
                "title": title,
                "description": "A saved travel item.",
                "image": "https://example.com/photo.jpg",
                "location": "Kyoto, Japan",
                "source_url": "https://en.wikipedia.org/?curid=123",
            },
        )
        assert saved.status_code == 201
        assert saved.json()["item_type"] == item_type
        assert saved.json()["item_key"] == item_key

        duplicate = client.post(
            "/api/v1/saved-items",
            headers=auth_headers,
            json={
                "item_type": item_type,
                "item_key": item_key,
                "title": title,
            },
        )
        assert duplicate.status_code == 409

    listed = client.get("/api/v1/saved-items", headers=auth_headers)
    assert [item["title"] for item in listed.json()] == [
        "Fushimi Inari Taisha",
        "Kyoto, Japan",
    ]

    saved_id = listed.json()[0]["id"]
    removed = client.delete(
        f"/api/v1/saved-items/{saved_id}",
        headers=auth_headers,
    )
    assert removed.status_code == 204


def test_saved_items_are_private(client, auth_headers):
    response = client.post(
        "/api/v1/saved-items",
        headers=auth_headers,
        json={
            "item_type": "destination",
            "item_key": "7",
            "title": "Kyoto, Japan",
        },
    )
    assert response.status_code == 201

    listed = client.get("/api/v1/saved-items")
    assert listed.status_code == 401
