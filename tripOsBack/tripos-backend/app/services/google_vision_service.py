import base64

import httpx
from fastapi import HTTPException

from app.core.config import settings

GOOGLE_VISION_ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"


def extract_document_text(images: list[bytes]) -> str:
    api_key = settings.GOOGLE_VISION_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Google Vision is not configured on the API server.",
        )

    try:
        response = httpx.post(
            GOOGLE_VISION_ANNOTATE_URL,
            headers={"X-Goog-Api-Key": api_key},
            json={
                "requests": [
                    {
                        "image": {
                            "content": base64.b64encode(image).decode("ascii")
                        },
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    }
                    for image in images
                ]
            },
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Google Vision rejected the document (HTTP "
                f"{error.response.status_code}). Check the API key, API enablement, "
                "and Google Cloud quota."
            ),
        ) from error
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach Google Vision "
                f"({type(error).__name__}). Check the API server's network connection."
            ),
        ) from error

    try:
        payload = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="Google Vision returned an invalid response.",
        ) from error

    results = payload.get("responses") if isinstance(payload, dict) else None
    if not isinstance(results, list) or len(results) != len(images):
        raise HTTPException(
            status_code=502,
            detail="Google Vision returned an invalid document response.",
        )

    page_text = []
    for result in results:
        if not isinstance(result, dict):
            raise HTTPException(
                status_code=502,
                detail="Google Vision returned an invalid page response.",
            )
        if result.get("error"):
            raise HTTPException(
                status_code=502,
                detail="Google Vision could not process one of the document pages.",
            )
        annotation = result.get("fullTextAnnotation")
        text = annotation.get("text") if isinstance(annotation, dict) else None
        if isinstance(text, str) and text.strip():
            page_text.append(text.strip())

    combined_text = "\n\n".join(page_text)
    if not combined_text:
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in the uploaded document.",
        )
    return combined_text
