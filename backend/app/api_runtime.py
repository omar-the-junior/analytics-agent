"""In-memory API sessions and safe event delivery for the workbook agent."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from app.agent_loop import AgentLoop, ModelClient, TraceEvent
from app.schemas import SafeError, StreamEvent, WorkbookResultEventData
from app.settings import Settings
from app.workbook_session import WorkbookSession, WorkbookToolExecutor

EVENT_WINDOW = 100
logger = logging.getLogger("workbook_agent.api")
SYSTEM_PROMPT = (
    "Use query_workbook whenever workbook data is needed. Use min or max for highest/lowest "
    "values, and order_by with limit for ranked lists. Quote values, Stable IDs, and rows exactly "
    "as returned; never calculate, sort, match, or re-pair them in prose. Request presentation "
    "table for a user-facing workbook result, explain its scope concisely, and never make a "
    "Markdown table from workbook data. For a requested workbook change, stage exactly one "
    "mutation and explain the proposed change; never commit a Staged Mutation. Never claim a "
    "change was made until confirmed."
)


class ProviderUnavailable(RuntimeError):
    pass


@dataclass
class RunState:
    run_id: str
    message: str
    status: str = "active"
    events: deque[StreamEvent] = field(default_factory=lambda: deque(maxlen=EVENT_WINDOW))
    next_event_id: int = 1
    started_at: float = field(default_factory=time.monotonic)
    condition: threading.Condition = field(default_factory=threading.Condition)

    def emit(self, event_type: str, data: dict[str, object] | None = None) -> None:
        if event_type == "workbook_result":
            data = WorkbookResultEventData.model_validate(data or {}).model_dump()
        with self.condition:
            self.events.append(
                StreamEvent(
                    event_id=self.next_event_id,
                    run_id=self.run_id,
                    type=event_type,  # type: ignore[arg-type]
                    data=data or {},
                )
            )
            self.next_event_id += 1
            self.condition.notify_all()


@dataclass
class SessionState:
    session_id: str
    workbook: str
    workbook_session: WorkbookSession
    runs: dict[str, RunState] = field(default_factory=dict)
    artifacts: dict[str, Path] = field(default_factory=dict)


class ApiRuntime:
    """Owns process-lifetime sessions; the browser receives only safe event envelopes."""

    def __init__(
        self,
        settings: Settings,
        model_factory: Callable[[], ModelClient] | None = None,
    ) -> None:
        self._settings = settings
        self._model_factory = model_factory or self._default_model_factory
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.RLock()

    def _default_model_factory(self) -> ModelClient:
        if self._settings.nvidia_api_key is None:
            raise ProviderUnavailable()
        from app.agent_loop import NvidiaModelClient

        return NvidiaModelClient(
            api_key=self._settings.nvidia_api_key.get_secret_value(),
            model=self._settings.model_name,
            base_url=self._settings.nvidia_base_url,
            timeout_seconds=self._settings.model_timeout_seconds,
        )

    def create_session(self, workbook: str) -> SessionState:
        session = SessionState(uuid.uuid4().hex, workbook, WorkbookSession(workbook))
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._sessions.get(session_id)

    def create_run(self, session: SessionState, message: str) -> RunState:
        run = RunState(uuid.uuid4().hex, message)
        with self._lock:
            session.runs[run.run_id] = run
        run.emit("run_started", {"started_at": time.time()})
        threading.Thread(target=self._execute, args=(session, run), daemon=True).start()
        return run

    def _execute(self, session: SessionState, run: RunState) -> None:
        try:
            def emit_trace(event: TraceEvent) -> None:
                activity = self._safe_activity(run, event)
                if activity is not None:
                    run.emit("activity", activity)

            agent = AgentLoop(
                self._model_factory(),
                WorkbookToolExecutor(
                    session.workbook_session,
                    query_result_callback=lambda result: run.emit(
                        "workbook_result", WorkbookResultEventData(result=result).model_dump()
                    ),
                ),
                max_iterations=self._settings.agent_max_iterations,
                run_timeout_seconds=self._settings.agent_run_timeout_seconds,
                trace_callback=emit_trace,
            )
            outcome = agent.run(run.message, SYSTEM_PROMPT)
        except ProviderUnavailable:
            self.fail(
                run, "provider_error", "The model provider is unavailable. Please try again.", True
            )
            return
        except Exception:
            self.fail(
                run, "internal_error", "The request could not be completed. Please try again.", True
            )
            return

        with run.condition:
            if run.status == "cancelled":
                return

        if outcome.answer:
            run.emit(
                "assistant_message",
                {"message": outcome.answer, "elapsed_ms": self._elapsed_ms(run)},
            )

        stage = session.workbook_session.pending_stage
        if stage is not None:
            with run.condition:
                if run.status == "cancelled":
                    return
                run.status = "awaiting_confirmation"
            run.emit("confirmation_required", stage)
            return

        if outcome.status == "completed":
            self.complete(run)
            return
        terminal_event = outcome.trace[-1].event if outcome.trace else "internal_error"
        error_code = {
            "provider_error": "provider_error",
            "invalid_action": "invalid_model_action",
            "policy_rejected": "policy_rejected",
            "needs_clarification": "clarification_required",
            "rejected": "policy_rejected",
            "budget_exhausted": "budget_exhausted",
            "iteration_limit_reached": "budget_exhausted",
            "stopped": "budget_exhausted",
        }.get(terminal_event, "internal_error")
        message = {
            "provider_error": "The model provider is temporarily unavailable. Please try again.",
            "invalid_model_action": "The model returned an invalid response. Please try again.",
            "budget_exhausted": self._budget_message(outcome.trace[-1]),
            "iteration_limit_reached": self._budget_message(outcome.trace[-1]),
        }.get(error_code, "The request could not be completed. Please try again.")
        self.fail(
            run,
            error_code,
            message,
            error_code != "policy_rejected",
        )

    @staticmethod
    def _budget_message(event: object) -> str:
        detail = getattr(event, "detail", {})
        resource = detail.get("resource") if isinstance(detail, dict) else None
        limit = detail.get("limit") if isinstance(detail, dict) else None
        if resource == "run_timeout_seconds" and isinstance(limit, (int, float)):
            return f"The request timed out after {limit:g} seconds. Please try again."
        if resource == "iteration_limit" and isinstance(limit, int):
            return f"The request reached its {limit}-step limit. Please try again."
        return "The request exceeded its execution budget. Please try again."

    @staticmethod
    def _elapsed_ms(run: RunState) -> int:
        return round((time.monotonic() - run.started_at) * 1000)

    def _safe_activity(self, run: RunState, event: TraceEvent) -> dict[str, object] | None:
        """Translate internal trace signals into UI-safe progress only.

        Model reasoning, prompts, tool arguments, and workbook results deliberately do
        not cross this boundary. The UI receives a concise activity label instead.
        """

        detail = event.detail
        iteration = detail.get("iteration")
        base: dict[str, object] = {
            "activity": event.event,
            "elapsed_ms": self._elapsed_ms(run),
        }
        if isinstance(iteration, int):
            base["iteration"] = iteration

        if event.event == "model_request":
            return {
                **base,
                "kind": "reasoning",
                "status": "active",
                "summary": "Reviewing the request and selecting the next safe step.",
            }
        if event.event == "model_response":
            return {
                **base,
                "kind": "reasoning",
                "status": "completed",
                "summary": "Prepared the next action.",
            }
        if event.event == "tool_started":
            tool = detail.get("tool")
            if not isinstance(tool, str):
                return None
            return {
                **base,
                "kind": "tool",
                "status": "active",
                "tool": tool,
                "summary": self._tool_summary(tool, "active"),
            }
        if event.event == "tool_result":
            tool = detail.get("tool")
            result = detail.get("status")
            if not isinstance(tool, str) or not isinstance(result, str):
                return None
            return {
                **base,
                "kind": "tool",
                "status": "completed" if result == "ok" else result,
                "tool": tool,
                "summary": self._tool_summary(tool, result),
            }
        if event.event == "final_answer":
            return {
                **base,
                "kind": "response",
                "status": "completed",
                "summary": "Prepared the response.",
            }
        return None

    @staticmethod
    def _tool_summary(tool: str, status: str) -> str:
        labels = {
            "describe_workbook": "Inspecting the workbook structure",
            "query_workbook": "Querying workbook data",
            "stage_mutation": "Preparing the proposed workbook change",
            "commit_mutation": "Committing the confirmed workbook change",
        }
        label = labels.get(tool, "Using an approved workbook tool")
        return f"{label}{'.' if status == 'active' else f' ({status}).'}"

    def complete(self, run: RunState) -> None:
        with run.condition:
            if run.status == "cancelled":
                return
            run.status = "completed"
        run.emit("completed", {"elapsed_ms": self._elapsed_ms(run)})

    def fail(self, run: RunState, code: str, message: str, retryable: bool) -> None:
        with run.condition:
            if run.status == "cancelled":
                return
            run.status = "failed"
        correlation_id = uuid.uuid4().hex
        logger.warning(
            "workbook run failed correlation_id=%s run_id=%s code=%s retryable=%s",
            correlation_id,
            run.run_id,
            code,
            retryable,
        )
        run.emit(
            "failed",
            SafeError(
                code=code,
                message=message,
                retryable=retryable,
                run_id=run.run_id,
                correlation_id=correlation_id,
            ).model_dump()
            | {"elapsed_ms": self._elapsed_ms(run)},
        )

    def cancel(self, session: SessionState, run: RunState) -> bool:
        with run.condition:
            if run.status not in {"active", "awaiting_confirmation"}:
                return False
            run.status = "cancelled"
        session.workbook_session.discard_stage()
        run.emit("cancelled", {"elapsed_ms": self._elapsed_ms(run)})
        return True

    def confirm(self, session: SessionState, run: RunState, stage_id: str) -> bool:
        with run.condition:
            if run.status != "awaiting_confirmation":
                return False
        run.emit(
            "activity",
            {
                "activity": "tool_started",
                "kind": "tool",
                "status": "active",
                "tool": "commit_mutation",
                "summary": self._tool_summary("commit_mutation", "active"),
                "elapsed_ms": self._elapsed_ms(run),
            },
        )
        result = session.workbook_session.commit_mutation({"stage_id": stage_id})
        if result.status != "ok":
            return False
        artifact_id = uuid.uuid4().hex
        session.artifacts[artifact_id] = session.workbook_session.active_path
        run.emit(
            "activity",
            {
                "activity": "tool_result",
                "kind": "tool",
                "status": "completed",
                "tool": "commit_mutation",
                "summary": self._tool_summary("commit_mutation", "ok"),
                "elapsed_ms": self._elapsed_ms(run),
            },
        )
        run.emit(
            "artifact_ready",
            {"artifact_id": artifact_id, "version": result.payload["version"], "verified": True},
        )
        self.complete(run)
        return True

    def events_after(self, run: RunState, last_event_id: int) -> Iterator[str]:
        cursor = last_event_id
        while True:
            with run.condition:
                available = [event for event in run.events if event.event_id > cursor]
                if not available and run.status not in {"completed", "cancelled", "failed"}:
                    run.condition.wait(timeout=15)
                    available = [event for event in run.events if event.event_id > cursor]
                terminal = run.status in {"completed", "cancelled", "failed"}
            for event in available:
                cursor = event.event_id
                encoded_event = json.dumps(event.model_dump())
                yield f"id: {event.event_id}\nevent: message\ndata: {encoded_event}\n\n"
            if terminal:
                return
            if not available:
                yield ": keepalive\n\n"
