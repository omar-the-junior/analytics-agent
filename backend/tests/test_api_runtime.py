import json

from app.agent_loop import AgentRun, ModelMessage, TraceEvent
from app.api_runtime import ApiRuntime, RunState
from app.settings import Settings


class FailingModelClient:
    def complete(self, messages: list[ModelMessage]) -> str:
        raise RuntimeError("provider unavailable")


def test_runtime_system_prompt_reserves_workbook_values_for_structured_results() -> None:
    from app.api_runtime import SYSTEM_PROMPT

    assert "publishes its validated result to the UI" in SYSTEM_PROMPT
    assert "Lead with the direct answer, copied exactly from canonical fields" in SYSTEM_PROMPT
    assert "a selection value, column, and atomically paired Stable ID" in SYSTEM_PROMPT
    assert "do not copy arbitrary table cells" in SYSTEM_PROMPT
    assert "houses or house means Property Type = House" in SYSTEM_PROMPT
    assert "Write simple CommonMark prose only" in SYSTEM_PROMPT
    assert "the UI displays its typed preview" in SYSTEM_PROMPT


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


def test_runtime_supplies_backend_owned_turns_and_query_reference_to_follow_up() -> None:
    class RecordingModel:
        def __init__(self) -> None:
            self.requests: list[list[ModelMessage]] = []
            self.responses = [
                json.dumps(
                    {
                        "kind": "tool_batch",
                        "tool_calls": [
                            {
                                "name": "query_workbook",
                                "arguments": {
                                    "filters": [
                                        {"column": "State", "operator": "eq", "value": "Texas"}
                                    ],
                                    "calculation": {"kind": "count"},
                                },
                            }
                        ],
                    }
                ),
                json.dumps({"kind": "final", "answer": "There are 90 Texas listings."}),
                json.dumps({"kind": "final", "answer": "The complete result is displayed."}),
            ]

        def complete(self, messages: list[ModelMessage]) -> str:
            self.requests.append(messages.copy())
            return self.responses.pop(0)

    model = RecordingModel()
    runtime = ApiRuntime(Settings(), model_factory=lambda: model)
    session = runtime.create_session("listings")

    runtime._execute(session, RunState("run-first", "How many listings are in Texas?"))
    runtime._execute(session, RunState("run-second", "Show that result again."))

    follow_up_messages = model.requests[-1]
    assert [message.role for message in follow_up_messages] == [
        "system",
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert follow_up_messages[2].content == "How many listings are in Texas?"
    assert follow_up_messages[3].content == "There are 90 Texas listings."
    assert follow_up_messages[4].content == "Show that result again."

    query_context = json.loads(follow_up_messages[1].content)
    assert query_context["query_references"][0]["request"] == {
        "filters": [{"column": "State", "operator": "eq", "value": "Texas"}],
        "select": None,
        "order_by": [],
        "calculation": {"kind": "count", "column": None},
        "limit": 10,
    }
    assert query_context["query_references"][0]["result"]["kind"] == "metric"
    assert "rows" not in query_context["query_references"][0]["result"]


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


def test_runtime_exposes_inspectable_tool_io_without_query_rows(monkeypatch) -> None:
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
                    {
                        "iteration": 1,
                        "tool": "query_workbook",
                        "input": {"filters": {"City": "Aurora"}},
                    },
                )
            )
            self.trace_callback(
                TraceEvent(
                    "tool_result",
                    {
                        "iteration": 1,
                        "tool": "query_workbook",
                        "status": "ok",
                        "output": {
                            "kind": "table",
                            "columns": ["City"],
                            "rows": [["Aurora"]],
                            "row_count": 1,
                            "truncated": False,
                        },
                    },
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
        "input": {"filters": {"City": "Aurora"}},
    }
    assert activities[2]["output"] == {
        "status": "ok",
        "kind": "table",
        "columns": ["City"],
        "returned_rows": 1,
        "row_count": 1,
        "truncated": False,
    }
    assert "rows" not in activities[2]["output"]
    assert isinstance(activities[2]["elapsed_ms"], int)
