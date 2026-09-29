from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_google_login_requires_server_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", None)
    monkeypatch.setattr(settings, "google_client_secret", None)
    with TestClient(app) as client:
        response = client.get("/api/auth/google/login")
    assert response.status_code == 503
    assert response.json()["error"] == "Google authentication is not configured"


def test_current_user_requires_a_session() -> None:
    with TestClient(app) as client:
        response = client.get("/api/auth/me")
    assert response.status_code == 401
