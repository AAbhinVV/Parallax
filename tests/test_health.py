from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "parallax-api"
    assert response.headers["X-Correlation-ID"]


def test_drive_compatible_health_path() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
