import json

import pymupdf


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
            assert content[0]["type"] == "text"
            assert content[1]["type"] == "image_url"
            return json.dumps(parsed_document)

    monkeypatch.setattr("app.routes.ai.document_parser.AIService", FakeAIService)
    response = client.post(
        "/api/v1/ai/parse-document",
        headers=auth_headers,
        data={"trip_id": str(trip_id)},
        files={"file": ("ticket.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"parsed": parsed_document}


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
            assert content[0]["type"] == "text"
            assert content[1]["type"] == "image_url"
            assert content[1]["image_url"]["url"].startswith(
                "data:image/png;base64,"
            )
            return '{"booking": null, "expense": null, "reminder": null}'

    monkeypatch.setattr("app.routes.ai.document_parser.AIService", FakeAIService)
    response = client.post(
        "/api/v1/ai/parse-document",
        headers=auth_headers,
        data={"trip_id": str(trip_id)},
        files={"file": ("ticket.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["parsed"]["booking"] is None
