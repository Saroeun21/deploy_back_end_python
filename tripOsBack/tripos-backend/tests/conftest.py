import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-with-more-than-32-bytes"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "traveler@example.com", "password": "secure-pass-123", "full_name": "Traveler"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "traveler@example.com", "password": "secure-pass-123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def destination_id(client, auth_headers):
    response = client.post(
        "/api/v1/destinations",
        headers=auth_headers,
        json={
            "name": "Japan",
            "country": "Japan",
            "country_code": "JP",
            "average_daily_cost_usd": 125,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def trip_id(client, auth_headers, destination_id):
    response = client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "destination_id": destination_id,
            "name": "Japan trip",
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "currency": "JPY",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def budget_category_id(client, auth_headers, trip_id):
    budget = client.post(
        "/api/v1/budgets",
        headers=auth_headers,
        json={"trip_id": trip_id, "total_budget": 2500, "currency": "JPY"},
    )
    assert budget.status_code == 201
    category = client.post(
        "/api/v1/budget-categories",
        headers=auth_headers,
        json={
            "budget_id": budget.json()["id"],
            "name": "Transport",
            "allocated_amount": 500,
        },
    )
    assert category.status_code == 201
    return category.json()["id"]
