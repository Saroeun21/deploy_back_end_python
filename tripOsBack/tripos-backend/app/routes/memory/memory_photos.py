from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.controllers.memory.memory_photo_controller import MemoryPhotoController
from app.core.database import get_db
from app.models.memory.memory_photo import MemoryPhoto
from app.models.user.user import User
from app.routes.common.scoped_factory import create_scoped_router
from app.schemas.memory.memory_photo import (
    MemoryPhotoCreate,
    MemoryPhotoRead,
    MemoryPhotoUpdate,
)
from app.services.memory_photo_service import (
    memory_photo_file_path,
    save_memory_photo,
)

# Register upload and protected file routes before the generic integer-ID routes.
router = APIRouter(tags=["Memory photos"])


@router.post(
    "/api/v1/memory-photos/upload",
    response_model=MemoryPhotoRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_memory_photo(
    memory_id: int = Form(...),
    file: UploadFile = File(...),
    caption: str | None = Form(default=None, max_length=255),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    controller = MemoryPhotoController(db, current_user)
    controller.validate_create({"memory_id": memory_id})

    filename = await save_memory_photo(file)
    image_path = f"/api/v1/memory-photos/files/{filename}"
    try:
        return controller.create(
            {
                "memory_id": memory_id,
                "image_path": image_path,
                "caption": caption,
            }
        )
    except Exception:
        memory_photo_file_path(filename).unlink(missing_ok=True)
        raise


@router.get("/api/v1/memory-photos/files/{filename}")
def get_uploaded_memory_photo(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_path = f"/api/v1/memory-photos/files/{filename}"
    photo = (
        MemoryPhotoController(db, current_user)
        .query_owned()
        .filter(MemoryPhotoController.model.image_path == image_path)
        .first()
    )
    if photo is None:
        raise HTTPException(status_code=404, detail="Memory photo not found.")

    path = memory_photo_file_path(filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Memory photo file not found.")
    return FileResponse(path, media_type=content_type_for_filename(filename))


def content_type_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return {
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }[suffix]


router.include_router(
    create_scoped_router(
        MemoryPhotoController,
        MemoryPhotoCreate,
        MemoryPhotoRead,
        "memory-photos",
        "Memory photos",
        MemoryPhotoUpdate,
    )
)