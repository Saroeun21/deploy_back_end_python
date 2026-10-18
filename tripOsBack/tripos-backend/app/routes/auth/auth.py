from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.auth.auth_controller import AuthController
from app.core.database import get_db
from app.schemas.user.user import (
    GoogleLoginRequest,
    GoogleLoginResponse,
    Token,
    UserCreate,
    UserLogin,
    UserRegistrationResponse,
    UserRead,
)
from app.services.welcome_email_service import send_welcome_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user = AuthController(db).register(payload)
    welcome_email_status = send_welcome_email(user.email, user.name)
    return UserRegistrationResponse(
        **UserRead.model_validate(user).model_dump(),
        welcome_email_status=welcome_email_status,
    )


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    return AuthController(db).login(
        payload,
        send_login_welcome_email=payload.send_welcome_email,
    )


@router.post("/google", response_model=GoogleLoginResponse)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    return AuthController(db).google_login(payload.id_token, payload.photo_url)
