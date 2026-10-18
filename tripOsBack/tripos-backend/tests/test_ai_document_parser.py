import json

import pymupdf

from app.core.database import SessionLocal
from app.models.ai.ai_extraction import AIExtraction


def create_trip(client, auth_headers, destination_id):
    response = client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Japan trip",
            "start_date": "2026-11-01",
            "end_date": "2026-11-08",
            "currency": "JPY",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_document_parser_returns_structured_results(
    client,
    auth_headers,
    destination_id,
    monkeypatch,
):
    trip_id = create_trip(client, auth_headers, destination_id)
    parsed_document = {
        "booking": {
            "kind": "flight",
            "from": "Tokyo",
            "to": "Osaka",
            "departure_time": "2026-11-02T10:00:00+09:00",
            "arrival_time": "2026-11-02T11:30:00+09:00",
        },
        "expense": {
            "description": "Flight ticket",
            "amount": 12500,
            "currency": "JPY",
        },
        "reminder": None,
    }

    class FakeAIService:
        def generate_response(self, messages):
            content = messages[0]["content"]
            assert content.startswith("Read this travel booking")
            assert "OCR text from the uploaded document:" in content
            assert "Flight to Osaka" in content
            return json.dumps(parsed_document)

    monkeypatch.setattr("app.routes.ai.document_parser.AIService", FakeAIService)
    monkeypatch.setattr(
        "app.routes.ai.document_parser.extract_document_text",
        lambda images: "Flight to Osaka",
    )
    response = client.post(
        "/api/v1/ai/parse-document",
        headers=auth_headers,
        data={"trip_id": str(trip_id)},
        files={"file": ("ticket.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"parsed": parsed_document}
    with SessionLocal() as db:
        extraction = db.query(AIExtraction).filter_by(trip_id=trip_id).one()
        extraction_id = extraction.id
        assert extraction.type == "flight_boarding_pass"
        assert extraction.requires_human_review is False
        assert extraction.extracted_data == parsed_document
    review_response = client.patch(
        f"/api/v1/ai/extractions/{extraction_id}",
        headers=auth_headers,
        json={"requires_human_review": True},
    )
    assert review_response.status_code == 200, review_response.text
    assert review_response.json()["requires_human_review"] is True


def test_document_parser_requires_authentication(client):
    response = client.post(
        "/api/v1/ai/parse-document",
        data={"trip_id": "1"},
        files={"file": ("ticket.png", b"image bytes", "image/png")},
    )

    assert response.status_code == 401


def test_document_parser_rejects_unknown_trip(
    client,
    auth_headers,
):
    response = client.post(
        "/api/v1/ai/parse-document",
        headers=auth_headers,
        data={"trip_id": "999"},
        files={"file": ("ticket.png", b"image bytes", "image/png")},
    )

    assert response.status_code == 404


def test_document_parser_rejects_invalid_pdf(
    client,
    auth_headers,
    destination_id,
    monkeypatch,
):
    trip_id = create_trip(client, auth_headers, destination_id)

    class UnexpectedAIService:
        def __init__(self):
            raise AssertionError("The AI service should not receive an invalid PDF.")

    monkeypatch.setattr(
        "app.routes.ai.document_parser.AIService",
        UnexpectedAIService,
    )
    response = client.post(
        "/api/v1/ai/parse-document",
        headers=auth_headers,
        data={"trip_id": str(trip_id)},
        files={"file": ("ticket.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 422


def test_document_parser_renders_pdf_pages_for_vision(
    client,
    auth_headers,
    destination_id,
    monkeypatch,
):
    trip_id = create_trip(client, auth_headers, destination_id)
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Flight ticket")
    pdf_bytes = document.tobytes()
    document.close()

    class FakeAIService:
        def generate_response(self, messages):
            content = messages[0]["content"]
            assert content.startswith("Read this travel booking")
            assert "OCR text from the uploaded document:\nFlight ticket" in content
            return '{"booking": null, "expense": null, "reminder": null}'

    monkeypatch.setattr("app.routes.ai.document_parser.AIService", FakeAIService)
    monkeypatch.setattr(
        "app.routes.ai.document_parser.extract_document_text",
        lambda images: "Flight ticket",
    )
    response = client.post(
        "/api/v1/ai/parse-document",
        headers=auth_headers,
        data={"trip_id": str(trip_id)},
        files={"file": ("ticket.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["parsed"]["booking"] is None
    with SessionLocal() as db:
        extraction = db.query(AIExtraction).filter_by(trip_id=trip_id).one()
        assert extraction.requires_human_review is True
