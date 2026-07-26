from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "workbook-agent-api"}


def test_agent_configuration_exposes_guardrails() -> None:
    response = client.get("/api/agent/configuration")

    assert response.status_code == 200
    payload = response.json()
    assert payload["write_confirmation_required"] is True
    assert "commit_staged_workbook" in payload["available_tools"]
