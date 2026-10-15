def test_report_submission_and_admin_review(client, auth_headers, admin_headers):
    submitted = client.post(
        "/api/v1/reports",
        headers=auth_headers,
        json={
            "content_type": "place",
            "content_id": 12,
            "reason": "This place listing is inaccurate.",
        },
    )

    assert submitted.status_code == 201
    assert submitted.json()["status"] == "pending"
    assert submitted.json()["reporter_email"] == "traveler@example.com"

    listing = client.get(
        "/api/v1/admin/reports?page=1&page_size=4",
        headers=admin_headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == submitted.json()["id"]

    reviewed = client.patch(
        f"/api/v1/admin/reports/{submitted.json()['id']}",
        headers=admin_headers,
        json={"status": "resolved", "resolution": "Listing corrected."},
    )

    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "resolved"
    assert reviewed.json()["resolution"] == "Listing corrected."


def test_report_endpoints_enforce_auth_and_admin_access(client, auth_headers):
    unauthenticated = client.post(
        "/api/v1/reports",
        json={"reason": "Incorrect content"},
    )
    regular_user_listing = client.get(
        "/api/v1/admin/reports",
        headers=auth_headers,
    )

    assert unauthenticated.status_code == 401
    assert regular_user_listing.status_code == 403
