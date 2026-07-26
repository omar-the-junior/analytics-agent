"""Bounded, transactional workbook operations for one Session Workbook."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook

from app.agent_loop import ToolCall, ToolResult

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "listings": ROOT / "docs" / "task-reqs" / "Real Estate Listings.xlsx",
    "campaigns": ROOT / "docs" / "task-reqs" / "Marketing Campaigns.xlsx",
}
ID_COLUMNS = {"listings": "Listing ID", "campaigns": "Campaign ID"}
MAX_ROWS = 100


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _value(value: Any) -> Any:
    """Convert pandas scalars into JSON-safe, user-facing values."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value.item() if hasattr(value, "item") else value


@dataclass(frozen=True)
class StagedMutation:
    stage_id: str
    operation: str
    target_id: str
    values: dict[str, Any]
    source_hash: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class WorkbookSession:
    """A chat-scoped service with no authority outside one supplied workbook."""

    def __init__(self, workbook: str, workspace: Path | None = None) -> None:
        if workbook not in SOURCES:
            raise ValueError("unknown_workbook")
        self.workbook = workbook
        self._source = SOURCES[workbook]
        self._root = workspace or Path(tempfile.mkdtemp(prefix="workbook-session-"))
        self._root.mkdir(parents=True, exist_ok=True)
        self._active = self._root / f"{workbook}-v1.xlsx"
        shutil.copy2(self._source, self._active)
        self._version = 1
        self._staged: StagedMutation | None = None

    @property
    def source_hash(self) -> str:
        return _digest(self._source)

    @property
    def active_path(self) -> Path:
        return self._active

    def _frame(self) -> pd.DataFrame:
        return pd.read_excel(self._active)

    def describe_workbook(self) -> ToolResult:
        frame = self._frame()
        return ToolResult(
            status="ok",
            payload={
                "workbook": self.workbook,
                "rows": len(frame),
                "columns": list(frame.columns),
                "stable_id": ID_COLUMNS[self.workbook],
                "version": self._version,
            },
        )

    def query_workbook(self, arguments: dict[str, Any]) -> ToolResult:
        allowed = {"filters", "aggregate", "column", "limit"}
        if set(arguments) - allowed:
            return ToolResult(status="rejected", payload={"error_code": "unsupported_query_field"})
        filters = arguments.get("filters", {})
        if not isinstance(filters, dict):
            return ToolResult(status="rejected", payload={"error_code": "invalid_filters"})
        frame = self._frame()
        unknown = sorted(set(filters) - set(frame.columns))
        if unknown:
            return ToolResult(
                status="rejected", payload={"error_code": "unknown_field", "fields": unknown}
            )
        # City names may occur in multiple states, so require a City Scope.
        if self.workbook == "listings" and "City" in filters and "State" not in filters:
            states = sorted(
                str(value)
                for value in frame.loc[frame["City"] == filters["City"], "State"].dropna().unique()
            )
            if len(states) > 1:
                return ToolResult(
                    status="needs_clarification",
                    payload={"error_code": "ambiguous_city_scope", "candidates": states},
                )
        for column, expected in filters.items():
            frame = frame.loc[frame[column] == expected]
        aggregate = arguments.get("aggregate", "rows")
        if aggregate == "count":
            return ToolResult(
                status="ok", payload={"count": len(frame), "calculation_source": "tool_computed"}
            )
        if aggregate == "sum":
            column = arguments.get("column")
            if column not in frame.columns or not pd.api.types.is_numeric_dtype(frame[column]):
                return ToolResult(
                    status="rejected", payload={"error_code": "invalid_aggregate_column"}
                )
            return ToolResult(
                status="ok",
                payload={
                    "column": column,
                    "value": _value(frame[column].sum()),
                    "calculation_source": "tool_computed",
                },
            )
        if aggregate != "rows":
            return ToolResult(status="rejected", payload={"error_code": "unsupported_aggregate"})
        limit = arguments.get("limit", 10)
        if not isinstance(limit, int) or limit < 1 or limit > MAX_ROWS:
            return ToolResult(status="rejected", payload={"error_code": "invalid_limit"})
        rows = [
            {key: _value(value) for key, value in row.items()}
            for row in frame.head(limit).to_dict("records")
        ]
        return ToolResult(
            status="ok",
            payload={"count": len(frame), "rows": rows, "truncated": len(frame) > limit},
        )

    def stage_mutation(self, arguments: dict[str, Any]) -> ToolResult:
        allowed = {"operation", "target_id", "values"}
        if set(arguments) - allowed or arguments.get("operation") not in {
            "insert",
            "update",
            "delete",
        }:
            return ToolResult(status="rejected", payload={"error_code": "invalid_mutation"})
        operation = arguments["operation"]
        target_id = arguments.get("target_id")
        values = arguments.get("values", {})
        if not isinstance(target_id, str) or not isinstance(values, dict):
            return ToolResult(
                status="rejected", payload={"error_code": "invalid_mutation_arguments"}
            )
        frame = self._frame()
        identifier = ID_COLUMNS[self.workbook]
        if set(values) - set(frame.columns):
            return ToolResult(status="rejected", payload={"error_code": "unknown_field"})
        matches = frame.loc[frame[identifier].astype(str) == target_id]
        if operation == "insert":
            if (
                not values
                or str(values.get(identifier, target_id)) != target_id
                or not matches.empty
            ):
                return ToolResult(
                    status="rejected", payload={"error_code": "invalid_insert_target"}
                )
            missing = set(frame.columns) - set(values)
            if missing:
                return ToolResult(
                    status="rejected",
                    payload={"error_code": "missing_insert_fields", "fields": sorted(missing)},
                )
            before, after = None, {key: _value(value) for key, value in values.items()}
        else:
            if len(matches) != 1:
                return ToolResult(status="rejected", payload={"error_code": "stable_id_not_found"})
            before = {key: _value(value) for key, value in matches.iloc[0].to_dict().items()}
            after = (
                None
                if operation == "delete"
                else {**before, **{key: _value(value) for key, value in values.items()}}
            )
        stage_id = hashlib.sha256(
            f"{self._version}:{operation}:{target_id}:{values}".encode()
        ).hexdigest()[:16]
        self._staged = StagedMutation(
            stage_id, operation, target_id, values, _digest(self._active), before, after
        )
        return ToolResult(
            status="ok",
            payload={
                "status": "confirmation_required",
                "stage_id": stage_id,
                "operation": operation,
                "stable_id": target_id,
                "before": before,
                "after": after,
            },
        )

    def commit_mutation(self, arguments: dict[str, Any]) -> ToolResult:
        stage = self._staged
        if stage is None or arguments != {"stage_id": stage.stage_id}:
            return ToolResult(status="rejected", payload={"error_code": "confirmation_required"})
        if _digest(self._active) != stage.source_hash:
            return ToolResult(status="rejected", payload={"error_code": "stale_stage"})
        candidate = self._root / f"{self.workbook}-v{self._version + 1}.xlsx"
        shutil.copy2(self._active, candidate)
        workbook = load_workbook(candidate)
        sheet = workbook.active
        headers = {cell.value: cell.column for cell in sheet[1]}
        identifier = ID_COLUMNS[self.workbook]
        row_numbers = [
            row
            for row in range(2, sheet.max_row + 1)
            if str(sheet.cell(row, headers[identifier]).value) == stage.target_id
        ]
        if stage.operation == "insert":
            row = sheet.max_row + 1
            for column, value in (stage.after or {}).items():
                sheet.cell(row, headers[column]).value = value
        elif stage.operation == "update" and len(row_numbers) == 1:
            for column, value in stage.values.items():
                sheet.cell(row_numbers[0], headers[column]).value = value
        elif stage.operation == "delete" and len(row_numbers) == 1:
            sheet.delete_rows(row_numbers[0])
        else:
            candidate.unlink(missing_ok=True)
            return ToolResult(status="rejected", payload={"error_code": "stable_id_not_found"})
        workbook.save(candidate)
        verified = self._verify(stage, candidate)
        if not verified:
            candidate.unlink(missing_ok=True)
            return ToolResult(
                status="rejected", payload={"error_code": "artifact_verification_failed"}
            )
        self._active = candidate
        self._version += 1
        self._staged = None
        return ToolResult(
            status="ok",
            payload={
                "artifact": candidate.name,
                "version": self._version,
                "verified": True,
                "stable_id": stage.target_id,
            },
        )

    def _verify(self, stage: StagedMutation, candidate: Path) -> bool:
        frame = pd.read_excel(candidate)
        identifier = ID_COLUMNS[self.workbook]
        matches = frame.loc[frame[identifier].astype(str) == stage.target_id]
        if stage.operation == "delete":
            return matches.empty
        if len(matches) != 1 or stage.after is None:
            return False
        observed = {key: _value(value) for key, value in matches.iloc[0].to_dict().items()}
        return all(observed.get(key) == value for key, value in stage.after.items())


class WorkbookToolExecutor:
    """Adapter that gives AgentLoop exactly the four permitted tools."""

    def __init__(self, session: WorkbookSession) -> None:
        self._session = session

    def execute(self, tool_call: ToolCall) -> ToolResult:
        if tool_call.name == "describe_workbook":
            return self._session.describe_workbook()
        if tool_call.name == "query_workbook":
            return self._session.query_workbook(tool_call.arguments)
        if tool_call.name == "stage_mutation":
            return self._session.stage_mutation(tool_call.arguments)
        if tool_call.name == "commit_mutation":
            return self._session.commit_mutation(tool_call.arguments)
        return ToolResult(status="rejected", payload={"error_code": "unknown_tool"})
