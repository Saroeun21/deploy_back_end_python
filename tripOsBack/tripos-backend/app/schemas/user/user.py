from datetime import datetime

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


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: str
    name: str
    profile: str | None
    status: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
