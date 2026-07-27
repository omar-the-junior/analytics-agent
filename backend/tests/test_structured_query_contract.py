from pathlib import Path

import pandas as pd
from app.agent_loop import ModelMessage
from app.api_runtime import ApiRuntime, RunState
from app.settings import Settings
from app.workbook_session import WorkbookSession


def test_rows_query_projects_orders_and_adds_the_stable_id(tmp_path: Path) -> None:
    session = WorkbookSession("listings", tmp_path)
    arguments = {
        "filters": [{"column": "Listing Status", "operator": "eq", "value": "Active"}],
        "select": ["City", "List Price"],
        "order_by": [{"column": "List Price", "direction": "desc"}],
        "limit": 5,
        "calculation": {"kind": "rows"},
        "presentation": "table",
    }

    first = session.query_workbook(arguments)
    second = session.query_workbook(arguments)

    assert first.status == "ok"
    assert first.payload == second.payload
    assert first.payload["kind"] == "table"
    assert first.payload["columns"] == ["City", "List Price", "Listing ID"]
    assert first.payload["row_count"] >= len(first.payload["rows"])
    assert first.payload["truncated"] is True
    prices = [row[1] for row in first.payload["rows"]]
    assert prices == sorted(prices, reverse=True)
    assert all(row[2].startswith("LST-") for row in first.payload["rows"])


def test_filter_operators_and_extrema_return_a_canonical_query_result(tmp_path: Path) -> None:
    session = WorkbookSession("listings", tmp_path)
    result = session.query_workbook(
        {
            "filters": [
                {"column": "Listing Status", "operator": "in", "value": ["Active", "Pending"]},
                {"column": "List Price", "operator": "gte", "value": 500000},
                {"column": "Sale Price", "operator": "not_null"},
            ],
            "calculation": {"kind": "max", "column": "List Price"},
        }
    )

    assert result.status == "ok"
    assert result.payload["kind"] == "selection"
    assert result.payload["stable_id_field"] == "Listing ID"
    assert result.payload["stable_id"] == result.payload["row"]["Listing ID"]
    assert result.payload["value"] == result.payload["row"]["List Price"]
    assert result.payload["calculation_source"] == "tool_computed"


def test_texas_houses_count_requires_both_state_and_property_type(tmp_path: Path) -> None:
    session = WorkbookSession("listings", tmp_path)

    all_texas_listings = session.query_workbook(
        {"filters": {"State": "Texas"}, "calculation": {"kind": "count"}}
    )
    texas_houses = session.query_workbook(
        {
            "filters": [
                {"column": "State", "operator": "eq", "value": "Texas"},
                {"column": "Property Type", "operator": "eq", "value": "House"},
            ],
            "calculation": {"kind": "count"},
        }
    )

    assert all_texas_listings.payload["value"] == 90
    assert texas_houses.payload["value"] == 29


def test_filters_enforce_city_scope_and_exact_value_types(tmp_path: Path) -> None:
    session = WorkbookSession("listings", tmp_path)

    ambiguous = session.query_workbook(
        {"filters": [{"column": "City", "operator": "in", "value": ["Aurora"]}]}
    )
    incompatible = session.query_workbook(
        {"filters": [{"column": "List Price", "operator": "eq", "value": "500000"}]}
    )

    assert ambiguous.status == "needs_clarification"
    assert ambiguous.payload["error_code"] == "ambiguous_city_scope"
    assert incompatible.payload == {"error_code": "invalid_filter_value"}


def test_ordering_and_extrema_break_ties_by_stable_id(tmp_path: Path, monkeypatch) -> None:
    session = WorkbookSession("listings", tmp_path)
    frame = pd.DataFrame(
        {
            "Listing ID": ["LST-2", "LST-1", "LST-3"],
            "List Price": [500000, 500000, 450000],
        }
    )
    monkeypatch.setattr(session, "_frame", lambda: frame)

    ranked = session.query_workbook(
        {
            "select": ["Listing ID", "List Price"],
            "order_by": [{"column": "List Price", "direction": "desc"}],
            "limit": 3,
        }
    )
    maximum = session.query_workbook({"calculation": {"kind": "max", "column": "List Price"}})

    assert ranked.payload["rows"] == [
        ["LST-1", 500000],
        ["LST-2", 500000],
        ["LST-3", 450000],
    ]
    assert maximum.payload["stable_id"] == "LST-1"


def test_stage_mutation_uses_a_typed_preview_instead_of_before_after_json(tmp_path: Path) -> None:
    session = WorkbookSession("campaigns", tmp_path)
    staged = session.stage_mutation(
        {
            "operation": "update",
            "target_id": "CMP-8001",
            "values": {"Budget Allocated": 200001},
        }
    )

    assert staged.status == "ok"
    assert "before" not in staged.payload
    assert "after" not in staged.payload
    assert staged.payload["stable_id_field"] == "Campaign ID"
    assert staged.payload["preview"] == {
        "kind": "field_diff",
        "columns": ["Field", "Before", "After"],
        "rows": [["Budget Allocated", 25000, 200001]],
    }


def test_runtime_publishes_structured_query_results_outside_activity_events(tmp_path: Path) -> None:
    class QueryingModel:
        def __init__(self) -> None:
            self._responses = [
                '{"kind":"tool_batch","tool_calls":[{"name":"query_workbook",'
                '"arguments":{"filters":{"Listing ID":"LST-5001"},'
                '"select":["City","List Price"],"presentation":"table"}}]}',
                '{"kind":"final","answer":"The listing is shown above."}',
            ]

        def complete(self, messages: list[ModelMessage]) -> str:
            return self._responses.pop(0)

    runtime = ApiRuntime(Settings(), model_factory=QueryingModel)
    session = runtime.create_session("listings")
    run = RunState("run-query-result", "Show listing LST-5001")

    runtime._execute(session, run)

    result_events = [event for event in run.events if event.type == "workbook_result"]
    assert len(result_events) == 1
    result = result_events[0].data["result"]
    assert result["kind"] == "table"
    assert result["stable_id_field"] == "Listing ID"
    assert result["rows"][0][-1] == "LST-5001"
    assert all("rows" not in event.data for event in run.events if event.type == "activity")
