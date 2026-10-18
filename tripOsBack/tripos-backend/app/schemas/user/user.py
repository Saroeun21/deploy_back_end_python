from datetime import datetime

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(
        default="",
        max_length=200,
        validation_alias=AliasChoices("name", "full_name"),
    )
    password: str = Field(min_length=8)
    profile: str | None = Field(default=None, max_length=255)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    profile: str | None = Field(default=None, max_length=255)
    status: bool | None = None


class UserProfileUpdate(BaseModel):
    name: str = Field(default="", min_length=1, max_length=200)
    profile: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    send_welcome_email: bool = True


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(
        min_length=1,
        validation_alias=AliasChoices("id_token", "idToken"),
    )
    photo_url: str | None = Field(
        default=None,
        max_length=2048,
        validation_alias=AliasChoices("photo_url", "photoUrl"),
    )


class UserRead(BaseModel):
    id: int
    email: str
    name: str
    profile: str | None
    avatar_url: str | None
    status: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRegistrationResponse(UserRead):
    welcome_email_status: Literal["sent", "failed", "not_configured"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    welcome_email_status: Literal[
        "sent",
        "failed",
        "not_configured",
        "not_applicable",
    ]


class GoogleLoginResponse(Token):
    avatar_url: str | None = None
    welcome_email_status: Literal[
        "sent",
        "failed",
        "not_configured",
        "not_applicable",
    ]
