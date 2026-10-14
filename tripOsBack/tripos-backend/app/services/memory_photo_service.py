import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_MEMORY_PHOTO_SIZE = 10 * 1024 * 1024
MEMORY_PHOTO_TYPES = {
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
    b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
    b"GIF87a": ("image/gif", ".gif"),
    b"GIF89a": ("image/gif", ".gif"),
}


def memory_photo_directory() -> Path:
    return settings.UPLOAD_DIR / "memory-photos"


def memory_photo_file_path(filename: str) -> Path:
    if re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|gif|webp)", filename) is None:
        raise HTTPException(status_code=404, detail="Memory photo not found.")
    return memory_photo_directory() / filename


async def save_memory_photo(upload: UploadFile) -> str:
    content = await upload.read(MAX_MEMORY_PHOTO_SIZE + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Choose a non-empty image.")
    if len(content) > MAX_MEMORY_PHOTO_SIZE:
        raise HTTPException(
            status_code=413,
            detail="The photo is too large. Maximum file size is 10 MB.",
        )

    image_type = next(
        (
            image_type
            for signature, image_type in MEMORY_PHOTO_TYPES.items()
            if content.startswith(signature)
        ),
        None,
    )
    if image_type is None and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        image_type = ("image/webp", ".webp")
    if image_type is None:
        raise HTTPException(
            status_code=415,
            detail="Upload a valid JPEG, PNG, GIF, or WebP image.",
        )

    filename = f"{uuid4().hex}{image_type[1]}"
    directory = memory_photo_directory()
    directory.mkdir(parents=True, exist_ok=True)
    memory_photo_file_path(filename).write_bytes(content)
    return filename
