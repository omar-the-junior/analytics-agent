from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.api_runtime import ApiRuntime
from app.schemas import (
    AgentConfigurationResponse,
    ConfirmationRequest,
    CreateRunRequest,
    CreateSessionRequest,
    HealthResponse,
    RunResponse,
    SafeError,
    SessionResponse,
)
from app.settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="The API boundary for the framework-free spreadsheet agent.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
runtime = ApiRuntime(settings)


def error_response(
    status_code: int, code: str, message: str, retryable: bool = False, run_id: str | None = None
) -> JSONResponse:
    payload = SafeError(
        code=code, message=message, retryable=retryable, run_id=run_id, correlation_id="request"
    ).model_dump()
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    return HealthResponse()


@app.get("/api/agent/configuration", response_model=AgentConfigurationResponse, tags=["agent"])
def get_agent_configuration() -> AgentConfigurationResponse:
    return AgentConfigurationResponse(
        provider=settings.model_provider,
        model=settings.active_model,
        write_confirmation_required=settings.require_write_confirmation,
    )


@app.post("/api/sessions", response_model=SessionResponse, status_code=201, tags=["sessions"])
def create_session(request: CreateSessionRequest) -> SessionResponse:
    session = runtime.create_session(request.workbook)
    return SessionResponse(session_id=session.session_id, workbook=request.workbook)


@app.post(
    "/api/sessions/{session_id}/runs", response_model=RunResponse, status_code=202, tags=["runs"]
)
def create_run(session_id: str, request: CreateRunRequest) -> RunResponse | JSONResponse:
    session = runtime.get_session(session_id)
    if session is None:
        return error_response(404, "policy_rejected", "This session is no longer available.")
    run = runtime.create_run(session, request.message)
    return RunResponse(run_id=run.run_id)


@app.get("/api/sessions/{session_id}/runs/{run_id}/events", response_model=None, tags=["runs"])
def stream_events(
    session_id: str,
    run_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse | JSONResponse:
    session = runtime.get_session(session_id)
    run = session.runs.get(run_id) if session else None
    if run is None:
        return error_response(
            404, "policy_rejected", "This run is no longer available.", run_id=run_id
        )
    try:
        cursor = int(last_event_id or 0)
    except ValueError:
        cursor = 0
    return StreamingResponse(
        runtime.events_after(run, cursor),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/sessions/{session_id}/runs/{run_id}/confirmation", tags=["runs"])
def confirm_run(session_id: str, run_id: str, request: ConfirmationRequest) -> JSONResponse:
    session = runtime.get_session(session_id)
    run = session.runs.get(run_id) if session else None
    if run is None or not runtime.confirm(session, run, request.stage_id):
        return error_response(
            409, "policy_rejected", "This staged change can no longer be confirmed.", run_id=run_id
        )
    return JSONResponse(status_code=202, content={"run_id": run_id})


@app.post("/api/sessions/{session_id}/runs/{run_id}/cancel", tags=["runs"])
def cancel_run(session_id: str, run_id: str) -> JSONResponse:
    session = runtime.get_session(session_id)
    run = session.runs.get(run_id) if session else None
    if run is None or not runtime.cancel(session, run):
        return error_response(
            409, "policy_rejected", "This run is no longer active.", run_id=run_id
        )
    return JSONResponse(status_code=202, content={"run_id": run_id})


@app.get(
    "/api/sessions/{session_id}/artifacts/{artifact_id}", response_model=None, tags=["artifacts"]
)
def download_artifact(session_id: str, artifact_id: str) -> FileResponse | JSONResponse:
    session = runtime.get_session(session_id)
    artifact = session.artifacts.get(artifact_id) if session else None
    if artifact is None or not artifact.exists():
        return error_response(404, "policy_rejected", "This artifact is no longer available.")
    return FileResponse(
        artifact,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{session.workbook}-verified.xlsx",
    )
