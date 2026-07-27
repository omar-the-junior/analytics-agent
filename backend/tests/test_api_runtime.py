from app.agent_loop import AgentRun, ModelMessage, TraceEvent
from app.api_runtime import ApiRuntime, RunState
from app.settings import Settings


class FailingModelClient:
    def complete(self, messages: list[ModelMessage]) -> str:
        raise RuntimeError("provider unavailable")


def test_provider_failure_is_logged_as_a_safe_provider_error(caplog) -> None:
    runtime = ApiRuntime(Settings(), model_factory=FailingModelClient)
    session = runtime.create_session("listings")
    run = RunState("run-123", "Count listings")

    runtime._execute(session, run)

    event = run.events[-1]
    assert event.type == "failed"
    assert event.data["code"] == "provider_error"
    assert event.data["message"] == (
        "The model provider is temporarily unavailable. Please try again."
    )
    assert event.data["run_id"] == "run-123"
    assert "correlation_id=" in caplog.text


def test_runtime_uses_configured_agent_budgets(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class RecordingAgentLoop:
        def __init__(
            self, model, executor, *, max_iterations, run_timeout_seconds, trace_callback
        ) -> None:
            observed["max_iterations"] = max_iterations
            observed["run_timeout_seconds"] = run_timeout_seconds

        def run(self, message: str, system_prompt: str) -> AgentRun:
            return AgentRun("completed", "Done.", [])

    monkeypatch.setattr("app.api_runtime.AgentLoop", RecordingAgentLoop)
    runtime = ApiRuntime(
        Settings(agent_max_iterations=8, agent_run_timeout_seconds=360),
        model_factory=FailingModelClient,
    )
    session = runtime.create_session("listings")
    run = RunState("run-456", "Count listings")

    runtime._execute(session, run)

    assert observed == {"max_iterations": 8, "run_timeout_seconds": 360}


def test_runtime_reports_the_specific_exhausted_budget(monkeypatch) -> None:
    class BudgetExhaustedAgentLoop:
        def __init__(
            self, model, executor, *, max_iterations, run_timeout_seconds, trace_callback
        ) -> None:
            pass

        def run(self, message: str, system_prompt: str) -> AgentRun:
            return AgentRun(
                "stopped",
                None,
                [TraceEvent("budget_exhausted", {"resource": "run_timeout_seconds", "limit": 360})],
            )

    monkeypatch.setattr("app.api_runtime.AgentLoop", BudgetExhaustedAgentLoop)
    runtime = ApiRuntime(Settings(), model_factory=FailingModelClient)
    session = runtime.create_session("listings")
    run = RunState("run-789", "Count listings")

    runtime._execute(session, run)

    assert run.events[-1].data["code"] == "budget_exhausted"
    assert run.events[-1].data["message"] == (
        "The request timed out after 360 seconds. Please try again."
    )


def test_runtime_exposes_a_safe_activity_trace_without_tool_data(monkeypatch) -> None:
    class TracingAgentLoop:
        def __init__(
            self, model, executor, *, max_iterations, run_timeout_seconds, trace_callback
        ) -> None:
            self.trace_callback = trace_callback

        def run(self, message: str, system_prompt: str) -> AgentRun:
            self.trace_callback(TraceEvent("model_request", {"iteration": 1}))
            self.trace_callback(
                TraceEvent(
                    "tool_started",
                    {"iteration": 1, "tool": "query_workbook", "filters": {"City": "Aurora"}},
                )
            )
            self.trace_callback(
                TraceEvent(
                    "tool_result",
                    {"iteration": 1, "tool": "query_workbook", "status": "ok", "payload": {"rows": []}},
                )
            )
            return AgentRun("completed", "Done.", [])

    monkeypatch.setattr("app.api_runtime.AgentLoop", TracingAgentLoop)
    runtime = ApiRuntime(Settings(), model_factory=FailingModelClient)
    session = runtime.create_session("listings")
    run = RunState("run-activity", "Count listings")

    runtime._execute(session, run)

    activities = [event.data for event in run.events if event.type == "activity"]
    assert activities[0]["kind"] == "reasoning"
    assert activities[1] == {
        "activity": "tool_started",
        "elapsed_ms": activities[1]["elapsed_ms"],
        "iteration": 1,
        "kind": "tool",
        "status": "active",
        "tool": "query_workbook",
        "summary": "Querying workbook data.",
    }
    assert "filters" not in activities[1]
    assert "payload" not in activities[2]
    assert isinstance(activities[2]["elapsed_ms"], int)
