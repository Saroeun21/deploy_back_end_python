from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user.user import User


class UserController:
    def __init__(self, user: User | None = None, db: Session | None = None):
        self.user = user
        self.db = db

    def _require_db(self) -> Session:
        if self.db is None:
            raise ValueError("Database session is required")
        return self.db

    def create_user(self, data: dict) -> User:
        db = self._require_db()
        user = User(
            email=data["email"],
            name=data.get("name", ""),
            hashed_password=hash_password(data["password"]),
            profile=data.get("profile"),
            status=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_current_user(self) -> User:
        if self.user is None:
            raise ValueError("User is not authenticated")
        return self.user

    def update_profile(self, data: dict[str, str | None]) -> User:
        db = self._require_db()
        user = self.get_current_user()
        if "name" in data:
            user.name = data["name"] or ""
        if "profile" in data:
            user.profile = data["profile"]
        db.commit()
        db.refresh(user)
        return user

    def change_password(self, current_password: str, new_password: str) -> User:
        db = self._require_db()
        user = self.get_current_user()
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        db.commit()
        db.refresh(user)
        return user

    def delete_current_user(self) -> None:
        db = self._require_db()
        user = self.get_current_user()
        db.delete(user)
        db.commit()
        self.user = None
