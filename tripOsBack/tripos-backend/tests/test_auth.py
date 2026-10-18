from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core.config import settings
from app.services.firebase_auth_service import verify_firebase_id_token


def create_firebase_test_token(private_key, project_id, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "aud": project_id,
        "iss": f"https://securetoken.google.com/{project_id}",
        "sub": "firebase-user-id",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "email": "traveler@example.com",
        "email_verified": True,
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def mock_firebase_signing_key(monkeypatch, public_key):
    class FakeJWKClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_signing_key_from_jwt(self, token):
            return type("SigningKey", (), {"key": public_key})()

    monkeypatch.setattr(
        "app.services.firebase_auth_service.jwt.PyJWKClient",
        FakeJWKClient,
    )


def test_register_and_login(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": "secure-pass-123", "full_name": "Person"},
    )
    assert registration.status_code == 201
    assert registration.json()["email"] == "person@example.com"
    assert registration.json()["welcome_email_status"] == "not_configured"
    assert "hashed_password" not in registration.json()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "secure-pass-123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["welcome_email_status"] == "not_configured"


def test_email_registration_sends_welcome_email(client, monkeypatch):
    sent = []

    def send_welcome_email(email, name):
        sent.append((email, name))
        return "sent"

    monkeypatch.setattr(
        "app.routes.auth.auth.send_welcome_email",
        send_welcome_email,
    )

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "password": "secure-pass-123",
            "name": "Person",
        },
    )

    assert registration.status_code == 201
    assert registration.json()["welcome_email_status"] == "sent"
    assert sent == [("person@example.com", "Person")]


def test_password_login_sends_welcome_back_email(client, monkeypatch):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "password": "secure-pass-123",
            "name": "Person",
        },
    )
    assert registration.status_code == 201

    sent = []
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.send_welcome_email",
        lambda email, name, **kwargs: sent.append((email, name, kwargs))
        or "sent",
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "secure-pass-123"},
    )

    assert login.status_code == 200
    assert login.json()["welcome_email_status"] == "sent"
    assert sent == [
        ("person@example.com", "Person", {"is_returning_user": True})
    ]


def test_password_signup_login_can_avoid_duplicate_welcome_email(
    client,
    monkeypatch,
):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "password": "secure-pass-123",
            "name": "Person",
        },
    )
    assert registration.status_code == 201
    sent = []
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.send_welcome_email",
        lambda *args, **kwargs: sent.append((args, kwargs)) or "sent",
    )

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "person@example.com",
            "password": "secure-pass-123",
            "send_welcome_email": False,
        },
    )

    assert login.status_code == 200
    assert login.json()["welcome_email_status"] == "not_applicable"
    assert sent == []


def test_firebase_id_token_verification_checks_project_and_verified_email(
    monkeypatch,
):
    project_id = "komsan-test-project"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(settings, "FIREBASE_PROJECT_ID", project_id)
    mock_firebase_signing_key(monkeypatch, private_key.public_key())

    token = create_firebase_test_token(private_key, project_id)
    claims = verify_firebase_id_token(token)
    assert claims["email"] == "traveler@example.com"
    assert claims["email_verified"] is True

    wrong_audience = create_firebase_test_token(
        private_key,
        project_id,
        aud="another-project",
    )
    with pytest.raises(HTTPException) as audience_error:
        verify_firebase_id_token(wrong_audience)
    assert audience_error.value.status_code == 401
    assert "project does not match" in audience_error.value.detail

    expired_token = create_firebase_test_token(
        private_key,
        project_id,
        exp=datetime.now(timezone.utc) - timedelta(minutes=2),
    )
    with pytest.raises(HTTPException) as expired_error:
        verify_firebase_id_token(expired_token)
    assert expired_error.value.status_code == 401
    assert "expired" in expired_error.value.detail.lower()

    slightly_future_token = create_firebase_test_token(
        private_key,
        project_id,
        iat=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    assert verify_firebase_id_token(slightly_future_token)["email"] == (
        "traveler@example.com"
    )

    future_token = create_firebase_test_token(
        private_key,
        project_id,
        iat=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    with pytest.raises(HTTPException) as future_error:
        verify_firebase_id_token(future_token)
    assert future_error.value.status_code == 401
    assert "clock is synchronized" in future_error.value.detail

    with pytest.raises(HTTPException) as malformed_error:
        verify_firebase_id_token("not-a-firebase-id-token")
    assert malformed_error.value.status_code == 401
    assert "valid Firebase ID token" in malformed_error.value.detail

    unverified_email = create_firebase_test_token(
        private_key,
        project_id,
        email_verified=False,
    )
    with pytest.raises(HTTPException) as email_error:
        verify_firebase_id_token(unverified_email)
    assert email_error.value.status_code == 401


def test_google_login_creates_and_reuses_verified_firebase_user(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.verify_firebase_id_token",
        lambda token: {
            "email": "Google.User@example.com",
            "email_verified": True,
            "name": "Google User",
            "picture": "https://lh3.googleusercontent.com/avatar.jpg",
        },
    )
    sent = []
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.send_welcome_email",
        lambda email, name, **kwargs: sent.append((email, name, kwargs))
        or "sent",
    )

    first_login = client.post(
        "/api/v1/auth/google",
        json={"id_token": "verified-firebase-id-token"},
    )
    assert first_login.status_code == 200, first_login.text
    assert first_login.json()["welcome_email_status"] == "sent"
    assert first_login.json()["avatar_url"] == (
        "https://lh3.googleusercontent.com/avatar.jpg"
    )
    first_user = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {first_login.json()['access_token']}"},
    )
    assert first_user.status_code == 200
    assert first_user.json()["email"] == "google.user@example.com"
    assert first_user.json()["name"] == "Google User"
    assert first_user.json()["avatar_url"] == (
        "https://lh3.googleusercontent.com/avatar.jpg"
    )

    second_login = client.post(
        "/api/v1/auth/google",
        json={"idToken": "verified-firebase-id-token"},
    )
    second_user = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {second_login.json()['access_token']}"},
    )
    assert second_login.status_code == 200, second_login.text
    assert second_login.json()["welcome_email_status"] == "sent"
    assert second_user.json()["id"] == first_user.json()["id"]
    assert len(sent) == 2
    assert all(call[0] == "google.user@example.com" for call in sent)


def test_google_login_updates_existing_profile_name_from_google_claims(
    client,
    monkeypatch,
):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "google.user@example.com",
            "password": "secure-pass-123",
            "name": "Old Komsan Name",
        },
    )
    assert registration.status_code == 201, registration.text
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.verify_firebase_id_token",
        lambda token: {
            "email": "google.user@example.com",
            "email_verified": True,
            "name": "Current Google Name",
            "picture": "https://lh3.googleusercontent.com/current-avatar.jpg",
        },
    )
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.send_welcome_email",
        lambda email, name, **_kwargs: "sent",
    )

    login = client.post(
        "/api/v1/auth/google",
        json={"id_token": "verified-firebase-id-token"},
    )
    assert login.status_code == 200, login.text
    profile = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert profile.status_code == 200
    assert profile.json()["name"] == "Current Google Name"
    assert profile.json()["avatar_url"] == (
        "https://lh3.googleusercontent.com/current-avatar.jpg"
    )


def test_google_login_uses_firebase_photo_and_prioritizes_it_over_uploaded_avatar(
    client,
    monkeypatch,
):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "google.photo@example.com",
            "password": "secure-pass-123",
            "name": "Google User",
        },
    )
    assert registration.status_code == 201, registration.text
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "google.photo@example.com",
            "password": "secure-pass-123",
        },
    )
    user_id = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    ).json()["id"]

    from app.core.database import SessionLocal
    from app.models.user.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        user.avatar_filename = "existing-uploaded-avatar.png"
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.verify_firebase_id_token",
        lambda token: {
            "email": "google.photo@example.com",
            "email_verified": True,
            "name": "Google User",
        },
    )
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.send_welcome_email",
        lambda email, name, **_kwargs: "sent",
    )

    google_login = client.post(
        "/api/v1/auth/google",
        json={
            "id_token": "verified-firebase-id-token",
            "photo_url": "https://lh3.googleusercontent.com/new-google-avatar.jpg",
        },
    )
    profile = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {google_login.json()['access_token']}"
        },
    )

    assert google_login.status_code == 200, google_login.text
    assert google_login.json()["avatar_url"] == (
        "https://lh3.googleusercontent.com/new-google-avatar.jpg"
    )
    assert profile.status_code == 200
    assert profile.json()["avatar_url"] == (
        "https://lh3.googleusercontent.com/new-google-avatar.jpg"
    )


def test_google_login_rejects_untrusted_profile_avatar_url(client, monkeypatch):
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.verify_firebase_id_token",
        lambda token: {
            "email": "traveler@example.com",
            "email_verified": True,
            "name": "Traveler",
            "picture": "https://example.com/avatar.jpg",
        },
    )
    monkeypatch.setattr(
        "app.controllers.auth.auth_controller.send_welcome_email",
        lambda email, name, **_kwargs: "sent",
    )

    login = client.post(
        "/api/v1/auth/google",
        json={"id_token": "verified-firebase-id-token"},
    )
    profile = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert login.status_code == 200, login.text
    assert profile.status_code == 200
    assert profile.json()["avatar_url"] is None


def test_protected_route_rejects_missing_token(client):
    assert client.get("/api/v1/users/me").status_code == 401


def test_current_user_can_update_profile_without_changing_email(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile@example.com",
            "password": "secure-pass-123",
            "name": "Traveler",
            "profile": "Enjoys city breaks",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "profile@example.com", "password": "secure-pass-123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"name": "Updated Traveler", "profile": "Loves hiking"},
    )

    assert update.status_code == 200
    assert update.json()["name"] == "Updated Traveler"
    assert update.json()["profile"] == "Loves hiking"
    assert update.json()["email"] == "profile@example.com"

    clear_profile = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"profile": None},
    )
    assert clear_profile.status_code == 200
    assert clear_profile.json()["profile"] is None


def test_current_user_can_upload_profile_avatar(
    client,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr("app.services.user_avatar_service.settings.UPLOAD_DIR", tmp_path)

    response = client.post(
        "/api/v1/users/me/avatar",
        headers=auth_headers,
        files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\navatar", "image/png")},
    )

    assert response.status_code == 200
    avatar_url = response.json()["avatar_url"]
    assert avatar_url.startswith("/api/v1/users/avatars/")

    avatar = client.get(avatar_url)
    assert avatar.status_code == 200
    assert avatar.content == b"\x89PNG\r\n\x1a\navatar"


def test_current_user_avatar_upload_rejects_non_images(client, auth_headers):
    response = client.post(
        "/api/v1/users/me/avatar",
        headers=auth_headers,
        files={"file": ("avatar.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
