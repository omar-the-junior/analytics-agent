from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "workbook-agent-api"


class WorkbookMutationPolicy(BaseModel):
    """The non-negotiable guardrails for all workbook-changing operations."""

    confirmation_required_for: list[str] = Field(
        default_factory=lambda: ["insert", "update", "delete"]
    )
    authorization: str = "explicit_user_confirmation_after_exact_diff"
    target_identity: str = "stable_id_only"
    source_preservation: str = "source_workbook_is_never_overwritten"
    output_artifact: str = "new_artifact_reopened_and_verified"


class AgentConfigurationResponse(BaseModel):
    provider: str
    model: str
    write_confirmation_required: bool
    workbook_mutation_policy: WorkbookMutationPolicy = Field(default_factory=WorkbookMutationPolicy)
    conversation_scope: str = "exactly_one_session_workbook"
    available_tools: list[str] = Field(
        default_factory=lambda: [
            "describe_workbook",
            "query_workbook",
            "stage_mutation",
            "commit_mutation",
        ]
    )


class CreateSessionRequest(BaseModel):
    workbook: Literal["listings", "campaigns"]


class SessionResponse(BaseModel):
    session_id: str
    workbook: Literal["listings", "campaigns"]


class CreateRunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)


class RunResponse(BaseModel):
    run_id: str


class ConfirmationRequest(BaseModel):
    stage_id: str = Field(min_length=1)


class SafeError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    run_id: str | None = None
    correlation_id: str


class StreamEvent(BaseModel):
    event_id: int
    run_id: str
    type: Literal[
        "run_started",
        "activity",
        "assistant_message",
        "confirmation_required",
        "artifact_ready",
        "completed",
        "cancelled",
        "failed",
    ]
    data: dict[str, Any] = Field(default_factory=dict)
