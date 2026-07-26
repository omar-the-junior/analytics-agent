"""Bounded, transactional workbook operations for one Session Workbook."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, ValidationError

from app.agent_loop import ToolCall, ToolResult

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "listings": ROOT / "docs" / "task-reqs" / "Real Estate Listings.xlsx",
    "campaigns": ROOT / "docs" / "task-reqs" / "Marketing Campaigns.xlsx",
}
ID_COLUMNS = {"listings": "Listing ID", "campaigns": "Campaign ID"}
MAX_ROWS = 100

FilterValue = str | int | float | bool | None


class QueryRequest(BaseModel):
    """The complete, bounded representation accepted by ``query_workbook``."""

    model_config = ConfigDict(extra="forbid")

    filters: dict[str, FilterValue] = Field(default_factory=dict)
    aggregate: Literal["rows", "count", "sum"] = "rows"
    column: str | None = None
    limit: StrictInt = Field(default=10, ge=1, le=MAX_ROWS)


class MutationRequest(BaseModel):
    """The complete, bounded representation accepted by ``stage_mutation``."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["insert", "update", "delete"]
    target_id: StrictStr = Field(min_length=1, pattern=r"\S")
    values: dict[str, FilterValue] = Field(default_factory=dict)


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
        self._source_identity = _digest(self._active)
        self._version = 1
        self._staged: StagedMutation | None = None

    @property
    def source_hash(self) -> str:
        return self._source_identity

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
                "source_identity": self._source_identity,
                "version": self._version,
            },
        )

    def query_workbook(self, arguments: Any) -> ToolResult:
        try:
            query = QueryRequest.model_validate(arguments, strict=True)
        except ValidationError:
            return ToolResult(status="rejected", payload={"error_code": "invalid_query"})

        filters = query.filters
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
        aggregate = query.aggregate
        if aggregate == "count":
            return ToolResult(
                status="ok", payload={"count": len(frame), "calculation_source": "tool_computed"}
            )
        if aggregate == "sum":
            column = query.column
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
        limit = query.limit
        rows = [
            {key: _value(value) for key, value in row.items()}
            for row in frame.head(limit).to_dict("records")
        ]
        return ToolResult(
            status="ok",
            payload={"count": len(frame), "rows": rows, "truncated": len(frame) > limit},
        )

    def _validate_mutation_values(
        self, frame: pd.DataFrame, values: dict[str, FilterValue]
    ) -> ToolResult | None:
        invalid = []
        for column, value in values.items():
            series = frame[column]
            if pd.api.types.is_numeric_dtype(series) and (
                isinstance(value, bool) or not isinstance(value, int | float)
            ):
                invalid.append(column)
            elif pd.api.types.is_datetime64_any_dtype(series) and (
                not isinstance(value, str) or pd.isna(pd.to_datetime(value, errors="coerce"))
            ):
                invalid.append(column)
        if invalid:
            return ToolResult(
                status="rejected", payload={"error_code": "invalid_field_value", "fields": invalid}
            )
        if self.workbook == "listings" and "Listing Status" in values:
            statuses = set(frame["Listing Status"].dropna().unique())
            if values["Listing Status"] not in statuses:
                return ToolResult(
                    status="rejected", payload={"error_code": "invalid_listing_status"}
                )
        return None

    def stage_mutation(self, arguments: Any) -> ToolResult:
        try:
            mutation = MutationRequest.model_validate(arguments, strict=True)
        except ValidationError:
            return ToolResult(status="rejected", payload={"error_code": "invalid_mutation"})
        operation = mutation.operation
        target_id = mutation.target_id
        values = mutation.values
        if operation == "delete" and values:
            return ToolResult(status="rejected", payload={"error_code": "invalid_delete_values"})
        frame = self._frame()
        identifier = ID_COLUMNS[self.workbook]
        if set(values) - set(frame.columns):
            return ToolResult(status="rejected", payload={"error_code": "unknown_field"})
        if operation == "update" and identifier in values:
            return ToolResult(status="rejected", payload={"error_code": "stable_id_immutable"})
        invalid_values = self._validate_mutation_values(frame, values)
        if invalid_values:
            return invalid_values
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
        if self.workbook == "listings" and after is not None:
            if after.get("Listing Status") == "Sold" and after.get("Sale Price") is None:
                return ToolResult(status="rejected", payload={"error_code": "missing_sale_price"})
        warnings = []
        if self.workbook == "listings" and after is not None:
            if after.get("Listing Status") == "Active" and after.get("Sale Price") is not None:
                warnings.append("active_listing_retains_sale_price")
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
                "before": before if operation != "update" else {key: before[key] for key in values},
                "after": after if operation != "update" else {key: after[key] for key in values},
                "warnings": warnings,
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
        verification = self._verify(stage, candidate)
        if verification is None:
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
                "verification": verification,
            },
        )

    def _verify(self, stage: StagedMutation, candidate: Path) -> dict[str, int] | None:
        """Reopen an artifact and prove the authorized diff is its only data change."""
        before_book = load_workbook(self._active, data_only=False)
        candidate_book = load_workbook(candidate, data_only=False)
        before_sheet = before_book.active
        candidate_sheet = candidate_book.active
        before_headers = {cell.value: cell.column for cell in before_sheet[1]}
        candidate_headers = {cell.value: cell.column for cell in candidate_sheet[1]}
        identifier = ID_COLUMNS[self.workbook]
        if before_headers != candidate_headers or identifier not in before_headers:
            return None

        def rows_by_id(sheet: Any, headers: dict[Any, int]) -> dict[str, dict[Any, Any]]:
            return {
                str(sheet.cell(row, headers[identifier]).value): {
                    name: sheet.cell(row, column).value for name, column in headers.items()
                }
                for row in range(2, sheet.max_row + 1)
            }

        before_rows = rows_by_id(before_sheet, before_headers)
        candidate_rows = rows_by_id(candidate_sheet, candidate_headers)
        before_row_count = before_sheet.max_row - 1
        candidate_row_count = candidate_sheet.max_row - 1
        if len(before_rows) != before_row_count or len(candidate_rows) != candidate_row_count:
            return None
        row_delta = 1 if stage.operation == "insert" else -1 if stage.operation == "delete" else 0
        expected_count = before_row_count + row_delta
        if candidate_row_count != expected_count:
            return None
        if stage.operation == "delete":
            if stage.target_id in candidate_rows:
                return None
        elif stage.operation == "insert":
            if candidate_rows.get(stage.target_id) != stage.after:
                return None
        elif stage.target_id not in before_rows or stage.target_id not in candidate_rows:
            return None
        else:
            for column, before_value in before_rows[stage.target_id].items():
                expected = stage.values[column] if column in stage.values else before_value
                if candidate_rows[stage.target_id].get(column) != expected:
                    return None

        unchanged_ids = set(before_rows) & set(candidate_rows) - {stage.target_id}
        if any(before_rows[row_id] != candidate_rows[row_id] for row_id in unchanged_ids):
            return None
        formula_row_ids = unchanged_ids | (
            {stage.target_id} if stage.operation == "update" else set()
        )
        preserved_formula_cells = sum(
            1
            for row_id in formula_row_ids
            for column, before_value in before_rows[row_id].items()
            if isinstance(before_value, str)
            and before_value.startswith("=")
            and candidate_rows[row_id].get(column) == before_value
        )
        return {
            "expected_row_count": expected_count,
            "observed_row_count": candidate_row_count,
            "unchanged_rows_verified": len(unchanged_ids),
            "preserved_formula_cells": preserved_formula_cells,
        }


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
