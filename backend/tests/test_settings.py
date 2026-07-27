from app.settings import Settings


def test_nvidia_is_the_default_provider_and_reads_its_environment(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("WORKBOOK_AGENT_MODEL_NAME", "nvidia/test-model")

    settings = Settings(_env_file=None)

    assert settings.model_provider == "nvidia"
    assert settings.nvidia_api_key is not None
    assert settings.active_model == "nvidia/test-model"


def test_nvidia_provider_configuration_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("WORKBOOK_AGENT_MODEL_PROVIDER", "nvidia")
    monkeypatch.setenv("WORKBOOK_AGENT_MODEL_NAME", "nvidia/test-model")

    settings = Settings(_env_file=None)

    assert settings.model_provider == "nvidia"
    assert settings.active_model == "nvidia/test-model"
