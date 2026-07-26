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
    assert payload["available_tools"] == [
        "describe_workbook",
        "query_workbook",
        "stage_mutation",
        "commit_mutation",
    ]
    assert payload["workbook_mutation_policy"] == {
        "confirmation_required_for": ["insert", "update", "delete"],
        "authorization": "explicit_user_confirmation_after_exact_diff",
        "target_identity": "stable_id_only",
        "source_preservation": "source_workbook_is_never_overwritten",
        "output_artifact": "new_artifact_reopened_and_verified",
    }
    assert payload["conversation_scope"] == "exactly_one_session_workbook"
