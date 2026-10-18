import json
from typing import Any

import pymupdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.ai.ai_extraction import AIExtraction, AIExtractionStatus
from app.models.trip.trip import Trip
from app.models.user.user import User
from app.services.ai_service import AIService
from app.services.google_vision_service import extract_document_text

router = APIRouter(prefix="/api/v1/ai", tags=["AI documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 5
IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


def _document_images(file_bytes: bytes, content_type: str) -> list[bytes]:
    if content_type in IMAGE_TYPES:
        return [file_bytes]

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
            images = []
            for page in document:
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(1.5, 1.5),
                    alpha=False,
                )
                images.append(pixmap.tobytes("png"))
            return images
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


def _get_extraction_type(parsed: dict[str, Any], document_text: str) -> str:
    booking = parsed.get("booking")
    booking_kind = booking.get("kind", "").casefold() if isinstance(booking, dict) else ""
    text = document_text.casefold()

    if booking_kind == "flight":
        return "flight_boarding_pass"
    if booking_kind in {"stay", "hotel", "accommodation"}:
        return "hotel_booking"
    if any(word in text for word in ("ferry", "transit", "rail pass", "island pass", "train ticket")):
        return "transit_pass"
    if parsed.get("expense") is not None:
        return "expense_receipt"
    if booking is not None:
        return "travel_booking"
    return "other"


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
    document_images = _document_images(file_bytes, content_type)
    document_text = extract_document_text(document_images)
    prompt = (
        "Read this travel booking, ticket, or receipt and return only a JSON object "
        "with exactly these keys: booking, expense, reminder. Use null for any item "
        "that is not supported by the document. A booking should have kind (stay or "
        "flight), the relevant name or route, ISO-8601 date-times, and any confirmation "
        "number and cost. An expense should have description, a positive numeric amount, "
        "and currency when visible. A reminder should have title, ISO-8601 due_date, "
        "and an optional description. Do not guess missing dates, prices, or identifiers."
        f"\n\nOCR text from the uploaded document:\n{document_text}"
    )
    response = AIService().generate_response(
        [
            {
                "role": "user",
                "content": prompt,
            }
        ]
    )
    parsed = _parse_json_response(response)
    db.add(
        AIExtraction(
            user_id=current_user.id,
            trip_id=trip.id,
            type=_get_extraction_type(parsed, document_text),
            extracted_data=parsed,
            status=AIExtractionStatus.COMPLETED,
            requires_human_review=not any(
                parsed.get(key) is not None for key in ("booking", "expense", "reminder")
            ),
        )
    )
    db.commit()
    return {"parsed": parsed}
