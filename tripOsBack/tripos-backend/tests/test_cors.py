def test_local_frontend_can_preflight_login(client):
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": ["http://localhost:5173", "https://deoloy-front-end-python.vercel.app/"],
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "content-type" in allowed_headers
