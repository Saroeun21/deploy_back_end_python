from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.controllers.user.user_controller import UserController
from app.models.user.user import User
from app.schemas.user.user import UserProfileUpdate, UserRead
from app.services.user_avatar_service import save_user_avatar, user_avatar_path

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return UserController(current_user).get_current_user()


@router.patch("/me", response_model=UserRead)
def update_current_user_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one profile field to update.",
        )
    return UserController(current_user, db).update_profile(updates)


@router.post("/me/avatar", response_model=UserRead)
async def update_current_user_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = await save_user_avatar(file)
    old_filename = current_user.avatar_filename
    try:
        current_user.avatar_filename = filename
        db.commit()
        db.refresh(current_user)
    except Exception:
        user_avatar_path(filename).unlink(missing_ok=True)
        raise

    if old_filename:
        user_avatar_path(old_filename).unlink(missing_ok=True)
    return current_user


@router.get("/avatars/{filename}")
def get_user_avatar(filename: str):
    path = user_avatar_path(filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Profile avatar not found.")
    return FileResponse(path)
