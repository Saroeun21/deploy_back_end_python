import base64
import json
from typing import Any

import pymupdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.trip.trip import Trip
from app.models.user.user import User
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 5
IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


def _image_content(file_bytes: bytes, content_type: str) -> list[dict[str, Any]]:
    if content_type in IMAGE_TYPES:
        encoded = base64.b64encode(file_bytes).decode("ascii")
        return [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{content_type};base64,{encoded}",
                    "detail": "high",
                },
            }
        ]

    if content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="Upload a PDF, JPEG, PNG, or WebP file.",
        )

    try:
        with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
            if document.page_count == 0:
                raise HTTPException(status_code=422, detail="The PDF has no pages.")
            if document.page_count > MAX_PDF_PAGES:
                raise HTTPException(
                    status_code=422,
                    detail=f"PDF files can contain at most {MAX_PDF_PAGES} pages.",
                )
            image_parts = []
            for page in document:
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(1.5, 1.5),
                    alpha=False,
                )
                encoded = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
                image_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded}",
                            "detail": "high",
                        },
                    }
                )
            return image_parts
    except pymupdf.FileDataError as error:
        raise HTTPException(
            status_code=422,
            detail="The uploaded PDF could not be read.",
        ) from error


def _parse_json_response(content: str) -> dict[str, Any]:
    raw = content.strip()
    code_block = raw.partition("```")[2].partition("```")[0].strip()
    if code_block.lower().startswith("json"):
        code_block = code_block[4:].strip()
    candidate = code_block or raw
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=502,
            detail="The AI document parser returned invalid JSON.",
        ) from error
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=502,
            detail="The AI document parser returned an invalid response.",
        )
    for key in ("booking", "expense", "reminder"):
        if parsed.get(key) is not None and not isinstance(parsed[key], dict):
            raise HTTPException(
                status_code=502,
                detail=f"The AI document parser returned an invalid {key}.",
            )
    return parsed


@router.post("/parse-document")
async def parse_document(
    trip_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == current_user.id,
    ).first()
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Choose a non-empty document.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The upload is too large. Maximum file size is 10 MB.",
        )

    content_type = (file.content_type or "").lower()
    image_parts = _image_content(file_bytes, content_type)
    prompt = (
        "Read this travel booking, ticket, or receipt and return only a JSON object "
        "with exactly these keys: booking, expense, reminder. Use null for any item "
        "that is not supported by the document. A booking should have kind (stay or "
        "flight), the relevant name or route, ISO-8601 date-times, and any confirmation "
        "number and cost. An expense should have description, a positive numeric amount, "
        "and currency when visible. A reminder should have title, ISO-8601 due_date, "
        "and an optional description. Do not guess missing dates, prices, or identifiers."
    )
    response = AIService().generate_response(
        [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}, *image_parts],
            }
        ]
    )
    return {"parsed": _parse_json_response(response)}
