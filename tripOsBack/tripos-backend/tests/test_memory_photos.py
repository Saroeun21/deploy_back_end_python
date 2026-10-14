from app.core.config import settings


def create_memory(client, auth_headers, trip_id):
    response = client.post(
        "/api/v1/memories",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "title": "A day to remember",
            "memory_date": "2026-10-10",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_upload_memory_photo_and_serve_only_to_owner(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    memory_id = create_memory(client, auth_headers, trip_id)
    image_bytes = b"\x89PNG\r\n\x1a\nphoto data"

    response = client.post(
        "/api/v1/memory-photos/upload",
        headers=auth_headers,
        data={"memory_id": str(memory_id), "caption": "At the market"},
        files={"file": ("market.png", image_bytes, "image/png")},
    )

    assert response.status_code == 201
    photo = response.json()
    assert photo["memory_id"] == memory_id
    assert photo["caption"] == "At the market"
    assert photo["image_path"].startswith("/api/v1/memory-photos/files/")

    image_response = client.get(photo["image_path"], headers=auth_headers)
    assert image_response.status_code == 200
    assert image_response.content == image_bytes
    assert image_response.headers["content-type"] == "image/png"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "another@example.com",
            "password": "secure-pass-456",
            "full_name": "Another Traveler",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "another@example.com", "password": "secure-pass-456"},
    )
    other_headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }
    assert client.get(photo["image_path"], headers=other_headers).status_code == 404
    assert client.get(photo["image_path"]).status_code == 401


def test_upload_memory_photo_rejects_invalid_image(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    memory_id = create_memory(client, auth_headers, trip_id)

    response = client.post(
        "/api/v1/memory-photos/upload",
        headers=auth_headers,
        data={"memory_id": str(memory_id)},
        files={"file": ("not-image.png", b"not an image", "image/png")},
    )

    assert response.status_code == 415
    assert not list(tmp_path.rglob("*"))


def test_upload_memory_photo_accepts_png_with_nonstandard_content_type(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    memory_id = create_memory(client, auth_headers, trip_id)
    image_bytes = b"\x89PNG\r\n\x1a\nphoto data"

    response = client.post(
        "/api/v1/memory-photos/upload",
        headers=auth_headers,
        data={"memory_id": str(memory_id)},
        files={"file": ("photo.PNG", image_bytes, "application/octet-stream")},
    )

    assert response.status_code == 201
    image_response = client.get(
        response.json()["image_path"],
        headers=auth_headers,
    )
    assert image_response.status_code == 200
    assert image_response.content == image_bytes
    assert image_response.headers["content-type"] == "image/png"


def test_upload_memory_photo_rejects_oversized_image(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    memory_id = create_memory(client, auth_headers, trip_id)

    response = client.post(
        "/api/v1/memory-photos/upload",
        headers=auth_headers,
        data={"memory_id": str(memory_id)},
        files={
            "file": (
                "large.png",
                b"\x89PNG\r\n\x1a\n" + b"x" * (10 * 1024 * 1024),
                "image/png",
            )
        },
    )

    assert response.status_code == 413
    assert not list(tmp_path.rglob("*"))


def test_upload_memory_photo_requires_owned_memory(
    client,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/api/v1/memory-photos/upload",
        headers=auth_headers,
        data={"memory_id": "99999"},
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\nphoto", "image/png")},
    )

    assert response.status_code == 404
    assert not list(tmp_path.rglob("*"))


def test_delete_uploaded_memory_photo_removes_file(
    client,
    auth_headers,
    trip_id,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    memory_id = create_memory(client, auth_headers, trip_id)
    response = client.post(
        "/api/v1/memory-photos/upload",
        headers=auth_headers,
        data={"memory_id": str(memory_id)},
        files={"file": ("photo.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
    )

    assert response.status_code == 201
    file_path = settings.UPLOAD_DIR / "memory-photos" / response.json()["image_path"].rsplit("/", 1)[-1]
    assert file_path.is_file()

    delete_response = client.delete(
        f"/api/v1/memory-photos/{response.json()['id']}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204
    assert not file_path.exists()
