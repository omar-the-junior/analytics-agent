from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "workbook-agent-api"


class AgentConfigurationResponse(BaseModel):
    provider: str
    model: str
    write_confirmation_required: bool
    available_tools: list[str] = Field(
        default_factory=lambda: [
            "inspect_workbook",
            "query_rows",
            "stage_insert_rows",
            "stage_update_cells",
            "stage_delete_rows",
            "commit_staged_workbook",
        ]
    )
