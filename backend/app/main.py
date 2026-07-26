from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import AgentConfigurationResponse, HealthResponse
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


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    return HealthResponse()


@app.get("/api/agent/configuration", response_model=AgentConfigurationResponse, tags=["agent"])
def get_agent_configuration() -> AgentConfigurationResponse:
    return AgentConfigurationResponse(
        provider=settings.model_provider,
        model=settings.model_name,
        write_confirmation_required=settings.require_write_confirmation,
    )
