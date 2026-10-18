import httpx
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.google_vision_service import extract_document_text


def test_google_vision_rejects_missing_server_key(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_VISION_API_KEY", None)

    with pytest.raises(HTTPException) as error:
        extract_document_text([b"image bytes"])

    assert error.value.status_code == 503
    assert "not configured" in error.value.detail


def test_google_vision_sends_images_and_combines_page_text(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_VISION_API_KEY", "test-key")
    requested = {}
    response = httpx.Response(
        200,
        json={
            "responses": [
                {"fullTextAnnotation": {"text": "Flight ticket"}},
                {"fullTextAnnotation": {"text": "Total USD 25"}},
            ]
        },
        request=httpx.Request(
            "POST",
            "https://vision.googleapis.com/v1/images:annotate",
        ),
    )

    def fake_post(url, **kwargs):
        requested["url"] = url
        requested["kwargs"] = kwargs
        return response

    monkeypatch.setattr("app.services.google_vision_service.httpx.post", fake_post)

    assert extract_document_text([b"first page", b"second page"]) == (
        "Flight ticket\n\nTotal USD 25"
    )
    assert requested["url"] == "https://vision.googleapis.com/v1/images:annotate"
    assert requested["kwargs"]["headers"] == {"X-Goog-Api-Key": "test-key"}
    assert "key" not in requested["kwargs"]
    requests = requested["kwargs"]["json"]["requests"]
    assert len(requests) == 2
    assert requests[0]["features"] == [{"type": "DOCUMENT_TEXT_DETECTION"}]


def test_google_vision_reports_api_rejection_without_exposing_key(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_VISION_API_KEY", "test-key")
    response = httpx.Response(
        403,
        request=httpx.Request(
            "POST",
            "https://vision.googleapis.com/v1/images:annotate",
        ),
    )
    monkeypatch.setattr(
        "app.services.google_vision_service.httpx.post",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(HTTPException) as error:
        extract_document_text([b"image bytes"])

    assert error.value.status_code == 502
    assert "HTTP 403" in error.value.detail
    assert "test-key" not in error.value.detail


def test_google_vision_rejects_image_without_readable_text(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_VISION_API_KEY", "test-key")
    response = httpx.Response(
        200,
        json={"responses": [{}]},
        request=httpx.Request(
            "POST",
            "https://vision.googleapis.com/v1/images:annotate",
        ),
    )
    monkeypatch.setattr(
        "app.services.google_vision_service.httpx.post",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(HTTPException) as error:
        extract_document_text([b"image bytes"])

    assert error.value.status_code == 422
    assert "No readable text" in error.value.detail
