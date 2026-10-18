import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user.user import User
from app.schemas.user.user import (
    GoogleLoginResponse,
    Token,
    UserCreate,
    UserLogin,
)
from app.services.firebase_auth_service import verify_firebase_id_token
from app.services.welcome_email_service import send_welcome_email


def _verified_google_avatar_url(claims: dict) -> str | None:
    picture = claims.get("picture")
    if not isinstance(picture, str) or len(picture) > 2048:
        return None
    parsed = urlsplit(picture)
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or not (
            hostname == "googleusercontent.com"
            or hostname.endswith(".googleusercontent.com")
        )
    ):
        return None
    return picture


def _google_avatar_url(picture: str | None, claims: dict) -> str | None:
    if isinstance(picture, str):
        validated_picture = _verified_google_avatar_url({"picture": picture})
        if validated_picture is not None:
            return validated_picture
    return _verified_google_avatar_url(claims)


class AuthController:
    def __init__(self, db: Session):
        self.db = db

    def register(self, payload: UserCreate) -> User:
        email = str(payload.email).lower()
        if self.db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=409, detail="Email is already registered")
        user = User(
            email=email,
            name=payload.name,
            profile=payload.profile,
            hashed_password=hash_password(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(
        self,
        payload: UserLogin,
        send_login_welcome_email: bool = True,
    ) -> Token:
        user = self.db.query(User).filter(User.email == str(payload.email).lower()).first()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        welcome_email_status = (
            send_welcome_email(user.email, user.name, is_returning_user=True)
            if send_login_welcome_email
            else "not_applicable"
        )
        return Token(
            access_token=create_access_token(str(user.id)),
            welcome_email_status=welcome_email_status,
        )

    def google_login(
        self,
        id_token: str,
        photo_url: str | None = None,
    ) -> GoogleLoginResponse:
        claims = verify_firebase_id_token(id_token)
        email = claims["email"].strip().lower()
        user = self.db.query(User).filter(User.email == email).first()
        is_new_user = user is None
        google_avatar_url = _google_avatar_url(photo_url, claims)
        if user is None:
            name = claims.get("name")
            user = User(
                email=email,
                name=name[:200] if isinstance(name, str) else "",
                hashed_password=hash_password(secrets.token_urlsafe(32)),
                google_avatar_url=google_avatar_url,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        elif user.status is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is disabled.",
            )
        else:
            changed = False
            name = claims.get("name")
            if isinstance(name, str) and name.strip():
                google_name = name.strip()[:200]
                if user.name != google_name:
                    user.name = google_name
                    changed = True
            if google_avatar_url and user.google_avatar_url != google_avatar_url:
                user.google_avatar_url = google_avatar_url
                changed = True
            if changed:
                self.db.commit()
        welcome_email_status = send_welcome_email(
            user.email,
            user.name,
            is_returning_user=not is_new_user,
        )
        return GoogleLoginResponse(
            access_token=create_access_token(str(user.id)),
            avatar_url=user.avatar_url,
            welcome_email_status=welcome_email_status,
        )
