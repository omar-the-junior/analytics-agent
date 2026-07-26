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
    workbook_mutation_policy: WorkbookMutationPolicy = Field(
        default_factory=WorkbookMutationPolicy
    )
    conversation_scope: str = "exactly_one_session_workbook"
    available_tools: list[str] = Field(
        default_factory=lambda: [
            "describe_workbook",
            "query_workbook",
            "stage_mutation",
            "commit_mutation",
        ]
    )
