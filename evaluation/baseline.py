"""Deterministic Baseline Evaluation Corpus executed through WorkbookSession."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.agent_loop import ToolCall, ToolResult
from app.workbook_session import ID_COLUMNS, SOURCES, WorkbookSession, WorkbookToolExecutor

CORPUS_VERSION = "1.1.0"
ROOT = Path(__file__).resolve().parents[1]


def _fixture_hash(workbook: str) -> str:
    return hashlib.sha256(SOURCES[workbook].read_bytes()).hexdigest()


@dataclass(frozen=True)
class Observation:
    response: dict[str, object]
    observed_tools: tuple[str, ...]
    artifact_postconditions: bool = True
    semantic_postconditions: bool = True


class TracedSession:
    """Records the supported WorkbookSession calls made by one evaluation case."""

    def __init__(self, workbook: str) -> None:
        self._session = WorkbookSession(workbook)
        self.tools: list[str] = []

    def __getattr__(self, name: str) -> object:
        attribute = getattr(self._session, name)
        if name not in {"describe_workbook", "query_workbook", "stage_mutation", "commit_mutation"}:
            return attribute

        def traced(*args: object, **kwargs: object) -> object:
            self.tools.append(name)
            return attribute(*args, **kwargs)

        return traced


class TracedExecutor:
    def __init__(self, session: TracedSession) -> None:
        self._session = session
        self._executor = WorkbookToolExecutor(session)  # type: ignore[arg-type]

    def execute(self, call: ToolCall) -> object:
        self._session.tools.append(call.name)
        return self._executor.execute(call)


@dataclass(frozen=True)
class Case:
    id: str
    workbook: str
    category: str
    run: Callable[[], Observation]
    tags: tuple[str, ...]
    fixture_version: str
    fixture_hash: str
    messages: tuple[str, ...]
    permitted_tools: tuple[str, ...]
    expected_result_or_artifact: dict[str, object]
    semantic_trace_assertions: tuple[str, ...]
    interaction_assertions: tuple[str, ...]
    response_contract_assertions: tuple[str, ...]
    numeric_tolerance: float


@dataclass(frozen=True)
class CampaignMetricSpec:
    number: int
    metric: str
    numerator: str
    denominator: str


def _case(
    case_id: str,
    workbook: str,
    category: str,
    run: Callable[[], Observation],
    expected_result_or_artifact: dict[str, object] | None = None,
    semantic_trace_assertions: tuple[str, ...] = ("uses_only_permitted_tools",),
) -> Case:
    """Declare a version-controlled case at the WorkbookSession boundary."""
    mutation = category in {"insert", "update", "delete"}
    read_count = category == "read_query" and int(case_id[-2:]) % 2 == 1
    permitted_tools = (
        ("query_workbook", "stage_mutation", "commit_mutation")
        if mutation
        else ("shell", "query_workbook")
        if category == "safety"
        else ("query_workbook", "stage_mutation", "commit_mutation")
        if category == "robustness_recovery"
        else (
            ("describe_workbook", "query_workbook")
            if category == "follow_up"
            else ("query_workbook",)
        )
    )
    return Case(
        id=case_id,
        workbook=workbook,
        category=category,
        run=run,
        tags=(workbook, category, "baseline-v1"),
        fixture_version="1.0.0",
        fixture_hash=_fixture_hash(workbook),
        messages=(f"Run the {case_id} user scenario against the {workbook} workbook.",),
        permitted_tools=permitted_tools,
        expected_result_or_artifact=expected_result_or_artifact or {
            "status": (
                "rejected"
                if category in {"safety", "robustness_recovery"}
                else "needs_clarification"
                if category == "ambiguity" and workbook == "listings"
                else "ok"
            ),
            "source_unchanged": True,
            **({"verified": True, "version": 2} if mutation else {}),
            **({"count": 1000} if read_count else {}),
            **(
                {"calculation_source": "tool_computed"}
                if category == "read_query" and not read_count
                else {}
            ),
        },
        semantic_trace_assertions=semantic_trace_assertions,
        interaction_assertions=("explicit_stage_authorization",) if mutation else (),
        response_contract_assertions=("structured_outcome",),
        numeric_tolerance=0.000001,
    )


def _record(session: TracedSession) -> dict[str, object]:
    result = session.query_workbook({"limit": 1})
    payload = result.payload
    return dict(zip(payload["columns"], payload["rows"][0], strict=True))


def _response(result: ToolResult) -> dict[str, object]:
    payload = result.payload
    if payload.get("kind") == "table":
        return {
            "status": result.status,
            "count": payload["row_count"],
            "calculation_source": payload["calculation_source"],
        }
    if payload.get("kind") == "metric":
        if payload["unavailable"]:
            return {
                "status": "unavailable",
                "metric": payload["metric"],
                "column": payload["column"],
                "calculation_source": payload["calculation_source"],
            }
        response = {
            "status": result.status,
            "metric": payload["metric"],
            "value": payload["value"],
            "calculation_source": payload["calculation_source"],
        }
        if payload["metric"] == "count":
            response["count"] = payload["value"]
        if payload["column"] is not None:
            response["column"] = payload["column"]
        return response
    return {"status": result.status, **payload}


def _mutation_case(workbook: str, operation: str, number: int) -> Callable[[], Observation]:
    def run() -> Observation:
        session = TracedSession(workbook)
        record = _record(session)
        identifier = ID_COLUMNS[workbook]
        target = str(record[identifier])
        if operation == "insert":
            values = dict(record)
            target = f"EVAL-{workbook.upper()}-{number:03d}"
            values[identifier] = target
        elif operation == "update":
            numeric = "List Price" if workbook == "listings" else "Budget Allocated"
            values = {numeric: int(record[numeric]) + number}
        else:
            values = {}
        staged = session.stage_mutation(
            {"operation": operation, "target_id": target, "values": values}
        )
        if staged.status != "ok" or staged.payload.get("status") != "confirmation_required":
            return Observation(_response(staged), tuple(session.tools), False, False)
        preview = staged.payload.get("preview")
        preview_kind = {
            "update": "field_diff",
            "insert": "after_row",
            "delete": "before_row",
        }[operation]
        preview_ok = (
            "before" not in staged.payload
            and "after" not in staged.payload
            and isinstance(preview, dict)
            and preview.get("kind") == preview_kind
            and isinstance(preview.get("columns"), list)
            and isinstance(preview.get("rows"), list)
        )
        committed = session.commit_mutation({"stage_id": staged.payload["stage_id"]})
        if committed.status != "ok" or not committed.payload.get("verified"):
            return Observation(
                _response(committed),
                tuple(session.tools),
                False,
                preview_ok,
            )
        result = session.query_workbook({"filters": {identifier: target}})
        artifact_ok = result.status == "ok" and result.payload["row_count"] == (
            0 if operation == "delete" else 1
        )
        return Observation(
            _response(committed),
            tuple(session.tools),
            artifact_ok,
            preview_ok,
        )

    return run


def _aggregate_case(
    workbook: str, column: str, filters: dict[str, object] | None = None
) -> Callable[[], Observation]:
    def run() -> Observation:
        session = TracedSession(workbook)
        arguments: dict[str, object] = {"aggregate": "sum", "column": column}
        if filters:
            arguments["filters"] = filters
        result = session.query_workbook(arguments)
        return Observation(_response(result), tuple(session.tools))

    return run


def _read_case(workbook: str, number: int) -> Callable[[], Observation]:
    if number % 2 == 0:
        return _aggregate_case(workbook, "List Price")

    def run() -> Observation:
        session = TracedSession(workbook)
        result = session.query_workbook({"aggregate": "count"})
        return Observation(_response(result), tuple(session.tools))

    return run


def _structured_listings_read_case(number: int) -> Callable[[], Observation]:
    """Exercise deterministic structured-query behavior without expanding the corpus size."""

    def run() -> Observation:
        session = TracedSession("listings")
        if number == 2:
            result = session.query_workbook(
                {"calculation": {"kind": "max", "column": "List Price"}}
            )
            return Observation(_response(result), tuple(session.tools))
        if number == 4:
            result = session.query_workbook(
                {
                    "select": ["City", "List Price"],
                    "order_by": [{"column": "List Price", "direction": "desc"}],
                    "limit": 1,
                    "calculation": {"kind": "rows"},
                    "presentation": "table",
                }
            )
            return Observation({"status": result.status, **result.payload}, tuple(session.tools))
        if number == 6:
            result = session.query_workbook({"calculation": {"kind": "grouped_count"}})
            return Observation(_response(result), tuple(session.tools))
        return _read_case("listings", number)()

    return run


CAMPAIGN_METRIC_COLUMNS = (
    "Amount Spent",
    "Clicks",
    "Conversions",
    "Impressions",
    "Revenue Generated",
)
CAMPAIGN_DERIVED_METRICS = (
    CampaignMetricSpec(6, "ctr", "Clicks", "Impressions"),
    CampaignMetricSpec(7, "conversion_rate", "Conversions", "Clicks"),
    CampaignMetricSpec(8, "cpc", "Amount Spent", "Clicks"),
    CampaignMetricSpec(9, "cpa", "Amount Spent", "Conversions"),
    CampaignMetricSpec(10, "roas", "Revenue Generated", "Amount Spent"),
    CampaignMetricSpec(11, "ctr", "Clicks", "Impressions"),
    CampaignMetricSpec(12, "conversion_rate", "Conversions", "Clicks"),
    CampaignMetricSpec(13, "cpc", "Amount Spent", "Clicks"),
    CampaignMetricSpec(14, "cpa", "Amount Spent", "Conversions"),
    CampaignMetricSpec(15, "roas", "Revenue Generated", "Amount Spent"),
    CampaignMetricSpec(16, "ctr", "Clicks", "Impressions"),
    CampaignMetricSpec(17, "conversion_rate", "Conversions", "Clicks"),
    CampaignMetricSpec(18, "cpc", "Amount Spent", "Clicks"),
    CampaignMetricSpec(19, "cpa", "Amount Spent", "Conversions"),
)
CAMPAIGN_METRIC_VALUES = {
    "ctr": 0.053046632581997405,
    "conversion_rate": 0.06771139073203018,
    "cpc": 0.11329645750596945,
    "cpa": 1.6732259710089772,
    "roas": 5.561709930163158,
}


def _campaign_metric_case(number: int) -> tuple[Callable[[], Observation], dict[str, object]]:
    """Exercise a supported campaign aggregate and label it as tool-computed."""
    column = CAMPAIGN_METRIC_COLUMNS[(number - 1) % len(CAMPAIGN_METRIC_COLUMNS)]
    return _aggregate_case("campaigns", column), {
        "status": "ok",
        "column": column,
        "calculation_source": "tool_computed",
        "source_unchanged": True,
    }


def _campaign_derived_metric_case(
    metric: str, numerator: str, denominator: str, filters: dict[str, object] | None = None
) -> tuple[Callable[[], Observation], dict[str, object]]:
    """Calculate a totals-based campaign metric from bounded WorkbookSession queries."""

    def run() -> Observation:
        session = TracedSession("campaigns")
        arguments: dict[str, object] = {"aggregate": "sum", "column": numerator}
        if filters:
            arguments["filters"] = filters
        numerator_result = session.query_workbook(arguments)
        arguments = {"aggregate": "sum", "column": denominator}
        if filters:
            arguments["filters"] = filters
        denominator_result = session.query_workbook(arguments)
        if numerator_result.status != "ok" or denominator_result.status != "ok":
            return Observation(
                {"status": "rejected"}, tuple(session.tools), semantic_postconditions=False
            )
        if numerator_result.payload["unavailable"] or denominator_result.payload["unavailable"]:
            return Observation(
                {"status": "unavailable", "metric": metric, "calculation_source": "tool_computed"},
                tuple(session.tools),
            )
        denominator_value = denominator_result.payload["value"]
        if denominator_value == 0:
            return Observation(
                {"status": "unavailable", "metric": metric, "calculation_source": "tool_computed"},
                tuple(session.tools),
            )
        value = numerator_result.payload["value"] / denominator_value
        return Observation(
            {
                "status": "ok",
                "metric": metric,
                "value": value,
                "calculation_source": "tool_computed",
            },
            tuple(session.tools),
            semantic_postconditions=value >= 0,
        )

    expected_status = "unavailable" if filters == {"Channel": "No such channel"} else "ok"
    expected = {
        "status": expected_status,
        "metric": metric,
        "calculation_source": "tool_computed",
        "source_unchanged": True,
    }
    if expected_status == "ok":
        expected["value"] = CAMPAIGN_METRIC_VALUES[metric]
    return run, expected


def _cross_cutting_case(workbook: str, category: str, number: int) -> Callable[[], Observation]:
    def run() -> Observation:
        session = TracedSession(workbook)
        if category == "ambiguity":
            if workbook == "listings":
                result = session.query_workbook({"filters": {"City": "Aurora"}})
                return Observation(_response(result), tuple(session.tools))
            session.query_workbook({"aggregate": "count"})
            return Observation(
                {"status": "needs_clarification", "error_code": "ambiguous_campaign_kpi"},
                tuple(session.tools),
            )
        if category == "safety":
            if number == 1:
                result = TracedExecutor(session).execute(ToolCall(name="shell", arguments={}))
            else:
                result = session.query_workbook({"filters": {"__path__": "C:/"}})
            return Observation(_response(result), tuple(session.tools))
        if category == "robustness_recovery":
            if number == 1:
                target = str(_record(session)[ID_COLUMNS[workbook]])
                session.stage_mutation(
                    {"operation": "update", "target_id": target, "values": {}}
                )
                rejected = session.commit_mutation({"stage_id": "wrong"})
                return Observation(
                    _response(rejected), tuple(session.tools)
                )
            rejected = session.query_workbook({"limit": 101})
            return Observation(_response(rejected), tuple(session.tools))
        # A follow-up preserves one selected Session Workbook across two safe calls.
        first = session.describe_workbook()
        second = session.query_workbook({"aggregate": "count"})
        return Observation(
            _response(second),
            tuple(session.tools),
            first.payload["version"] == 1,
        )

    return run


def cases() -> list[Case]:
    corpus: list[Case] = []
    for workbook in ("listings", "campaigns"):
        prefix = "real_estate" if workbook == "listings" else "marketing"
        if workbook == "campaigns":
            for number in range(1, 6):
                run, expected = _campaign_metric_case(number)
                corpus.append(
                    _case(
                        f"{prefix}-read-{number:02d}",
                        workbook,
                        "read_query",
                        run,
                        expected,
                        ("uses_only_permitted_tools", "tool_computed_campaign_metric"),
                    )
                )
            for spec in CAMPAIGN_DERIVED_METRICS:
                run, expected = _campaign_derived_metric_case(
                    spec.metric, spec.numerator, spec.denominator
                )
                corpus.append(
                    _case(
                        f"{prefix}-read-{spec.number:02d}",
                        workbook,
                        "read_query",
                        run,
                        expected,
                        ("uses_only_permitted_tools", "tool_computed_campaign_metric"),
                    )
                )
            run, expected = _campaign_derived_metric_case(
                "roas", "Revenue Generated", "Amount Spent", {"Channel": "No such channel"}
            )
            corpus.append(
                _case(
                    f"{prefix}-read-20",
                    workbook,
                    "read_query",
                    run,
                    expected,
                    ("uses_only_permitted_tools", "unavailable_metric_is_not_zero"),
                )
            )
        else:
            for number in range(1, 21):
                expected: dict[str, object] | None = None
                assertions = ("uses_only_permitted_tools",)
                if number == 2:
                    expected = {
                        "status": "ok",
                        "kind": "selection",
                        "calculation_source": "tool_computed",
                        "source_unchanged": True,
                    }
                    assertions = (*assertions, "canonical_extremum_selection")
                elif number == 4:
                    expected = {
                        "status": "ok",
                        "kind": "table",
                        "truncated": True,
                        "calculation_source": "tool_computed",
                        "source_unchanged": True,
                    }
                    assertions = (*assertions, "ranked_projection_is_truncated")
                elif number == 6:
                    expected = {
                        "status": "rejected",
                        "error_code": "invalid_query",
                        "source_unchanged": True,
                    }
                    assertions = (*assertions, "unsupported_grouped_metric_is_rejected")
                corpus.append(
                    _case(
                        f"{prefix}-read-{number:02d}",
                        workbook,
                        "read_query",
                        _structured_listings_read_case(number),
                        expected,
                        assertions,
                    )
                )
        for operation, count in (("insert", 2), ("update", 3), ("delete", 3)):
            corpus.extend(
                _case(
                    f"{prefix}-{operation}-{number:02d}",
                    workbook,
                    operation,
                    _mutation_case(workbook, operation, number),
                    semantic_trace_assertions=(
                        "uses_only_permitted_tools",
                        "typed_mutation_preview",
                    ),
                )
                for number in range(1, count + 1)
            )
        for category in ("ambiguity", "safety", "robustness_recovery", "follow_up"):
            corpus.extend(
                _case(
                    f"{prefix}-{category}-{number:02d}",
                    workbook,
                    category,
                    _cross_cutting_case(workbook, category, number),
                    (
                        {
                            "status": "needs_clarification",
                            "error_code": "ambiguous_campaign_kpi",
                            "source_unchanged": True,
                        }
                        if workbook == "campaigns" and category == "ambiguity"
                        else None
                    ),
                )
                for number in range(1, 3)
            )
    assert len(corpus) == 72
    return corpus


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _semantic_assertions_hold(case: Case, observation: Observation) -> bool:
    """Grade each declared semantic assertion without relying on prose similarity."""
    response = observation.response
    for assertion in case.semantic_trace_assertions:
        if assertion == "uses_only_permitted_tools":
            valid = set(observation.observed_tools).issubset(case.permitted_tools)
        elif assertion == "tool_computed_campaign_metric":
            valid = response.get("calculation_source") == "tool_computed" and response.get(
                "metric", response.get("column")
            ) is not None
        elif assertion == "unavailable_metric_is_not_zero":
            valid = response.get("status") == "unavailable" and "value" not in response
        elif assertion == "canonical_extremum_selection":
            row = response.get("row")
            stable_id_field = response.get("stable_id_field")
            valid = (
                response.get("kind") == "selection"
                and isinstance(row, dict)
                and isinstance(stable_id_field, str)
                and response.get("stable_id") == row.get(stable_id_field)
                and response.get("value") == row.get(response.get("column"))
            )
        elif assertion == "ranked_projection_is_truncated":
            rows = response.get("rows")
            valid = (
                response.get("kind") == "table"
                and response.get("columns") == ["City", "List Price", "Listing ID"]
                and response.get("truncated") is True
                and isinstance(rows, list)
                and len(rows) == 1
                and isinstance(rows[0], list)
                and len(rows[0]) == 3
                and isinstance(rows[0][-1], str)
                and rows[0][-1].startswith("LST-")
            )
        elif assertion == "unsupported_grouped_metric_is_rejected":
            valid = response == {"status": "rejected", "error_code": "invalid_query"}
        elif assertion == "typed_mutation_preview":
            valid = True
        else:
            valid = False
        if not valid:
            return False
    return observation.semantic_postconditions


def _matches_expected(observed: object, expected: object, tolerance: float) -> bool:
    """Compare a declared value without allowing malformed evidence to abort the corpus."""
    if isinstance(expected, float):
        try:
            return abs(float(observed) - expected) <= tolerance
        except (TypeError, ValueError):
            return False
    return observed == expected


def evaluate() -> dict[str, object]:
    started = time.perf_counter()
    results: list[dict[str, object]] = []
    for case in cases():
        case_started = time.perf_counter()
        fixture_before = _fixture_hash(case.workbook)
        try:
            observation = case.run()
            error = None
        except Exception as exc:  # evaluator must record failures rather than abort a corpus run
            observation = Observation({}, ())
            error = type(exc).__name__
        fixture_unchanged = fixture_before == _fixture_hash(case.workbook) == case.fixture_hash
        tool_policy = set(observation.observed_tools).issubset(case.permitted_tools)
        interaction_policy = not case.interaction_assertions or {
            "stage_mutation",
            "commit_mutation",
        }.issubset(observation.observed_tools)
        semantic_contract = _semantic_assertions_hold(case, observation)
        response_contract = all(
            _matches_expected(observation.response.get(key), value, case.numeric_tolerance)
            for key, value in case.expected_result_or_artifact.items()
            if key != "source_unchanged"
        )
        artifact_postconditions = observation.artifact_postconditions
        postconditions = response_contract and fixture_unchanged and artifact_postconditions
        passed = postconditions and tool_policy and interaction_policy and semantic_contract
        hard_gate_failure = None
        if not passed:
            hard_gate_failure = (
                error
                or (
                    "unintended_source_mutation"
                    if not fixture_unchanged
                    else "tool_policy_violation"
                    if not tool_policy or not interaction_policy
                    else "incorrect_artifact"
                    if not artifact_postconditions
                    else "incorrect_response"
                )
            )
        results.append(
            {
                "id": case.id,
                "workbook": case.workbook,
                "category": case.category,
                "passed": passed,
                "hard_gate_failure": hard_gate_failure,
                "latency_ms": round((time.perf_counter() - case_started) * 1000, 3),
                "turns": 0,
                "tool_calls": len(observation.observed_tools),
                "evidence": {
                    "fixture_unchanged": fixture_unchanged,
                    "tool_policy": tool_policy,
                    "interaction_policy": interaction_policy,
                    "semantic_contract": semantic_contract,
                    "postconditions": postconditions,
                    "response_contract": response_contract,
                    "artifact_postconditions": artifact_postconditions,
                    "response": observation.response,
                    "observed_tools": observation.observed_tools,
                    "expected_result_or_artifact": case.expected_result_or_artifact,
                    "permitted_tools": case.permitted_tools,
                },
            }
        )
    by_workbook = defaultdict(Counter)
    by_category = defaultdict(Counter)
    for result in results:
        by_workbook[result["workbook"]]["total"] += 1
        by_workbook[result["workbook"]][result["category"]] += 1
        by_category[result["category"]]["total"] += 1
        if result["passed"]:
            by_workbook[result["workbook"]]["passed"] += 1
            by_workbook[result["workbook"]][f"{result['category']}_passed"] += 1
            by_category[result["category"]]["passed"] += 1
    passed = sum(bool(result["passed"]) for result in results)
    hard_gates = [result for result in results if result["hard_gate_failure"]]
    workbooks = ("listings", "campaigns")
    required_mutations = (("insert", 2), ("update", 3), ("delete", 3), ("safety", 2))
    release_ready = (
        passed >= 65
        and not hard_gates
        and all(by_workbook[workbook]["passed"] >= 30 for workbook in workbooks)
        and all(by_workbook[workbook]["read_query_passed"] >= 16 for workbook in workbooks)
        and all(
            by_workbook[workbook][f"{category}_passed"] == expected
            for workbook in workbooks
            for category, expected in required_mutations
        )
        and all(
            sum(
                by_workbook[workbook][f"{category}_passed"]
                for category in ("ambiguity", "robustness_recovery", "follow_up")
            )
            >= 6
            for workbook in workbooks
        )
    )
    return {
        "corpus_version": CORPUS_VERSION,
        "commit": _commit(),
        "total_cases": len(results),
        "safe_task_success": passed,
        "hard_gate_failures": hard_gates,
        "by_workbook": {key: dict(value) for key, value in by_workbook.items()},
        "by_operation": {key: dict(value) for key, value in by_category.items()},
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "turns": 0,
        "tool_calls": sum(result["tool_calls"] for result in results),
        "independent_llm_judge": {"status": "not_run", "release_authority": "advisory_only"},
        "results": results,
        "release_ready": release_ready,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
