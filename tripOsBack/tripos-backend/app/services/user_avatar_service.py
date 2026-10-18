import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_USER_AVATAR_SIZE = 5 * 1024 * 1024
USER_AVATAR_TYPES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
}


def user_avatar_directory() -> Path:
    return settings.UPLOAD_DIR / "user-avatars"


def user_avatar_path(filename: str) -> Path:
    if re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|gif|webp)", filename) is None:
        raise HTTPException(status_code=404, detail="Profile avatar not found.")
    return user_avatar_directory() / filename


async def save_user_avatar(upload: UploadFile) -> str:
    content = await upload.read(MAX_USER_AVATAR_SIZE + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Choose a non-empty image.")
    if len(content) > MAX_USER_AVATAR_SIZE:
        raise HTTPException(
            status_code=413,
            detail="The avatar is too large. Maximum file size is 5 MB.",
        )

    extension = next(
        (
            extension
            for signature, extension in USER_AVATAR_TYPES.items()
            if content.startswith(signature)
        ),
        None,
    )
    if extension is None and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        extension = ".webp"
    if extension is None:
        raise HTTPException(
            status_code=415,
            detail="Upload a valid JPEG, PNG, GIF, or WebP image.",
        )

    filename = f"{uuid4().hex}{extension}"
    directory = user_avatar_directory()
    directory.mkdir(parents=True, exist_ok=True)
    user_avatar_path(filename).write_bytes(content)
    return filename
