"""Pure state transitions for the WorkbookSession prototype."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PendingMutation:
    operation: str
    workbook: str
    summary: str


@dataclass(frozen=True)
class SessionState:
    active_version: int = 1
    retained_versions: tuple[int, ...] = (1,)
    pending: PendingMutation | None = None
    confirmed: bool = False
    last_status: str = "Ready"


def stage(state: SessionState, mutation: PendingMutation) -> SessionState:
    return replace(state, pending=mutation, confirmed=False, last_status="Mutation staged")


def confirm(state: SessionState) -> SessionState:
    if state.pending is None:
        return replace(state, last_status="Nothing is staged to confirm")
    return replace(state, confirmed=True, last_status="Explicit confirmation recorded")


def reject_unconfirmed_commit(state: SessionState) -> SessionState:
    return replace(state, last_status="Rejected: explicit confirmation is required")


def commit(state: SessionState) -> SessionState:
    if state.pending is None:
        return replace(state, last_status="Nothing is staged to commit")
    if not state.confirmed:
        return reject_unconfirmed_commit(state)
    next_version = state.active_version + 1
    versions = (*state.retained_versions, next_version)[-5:]
    return SessionState(
        active_version=next_version,
        retained_versions=versions,
        last_status=f"Committed verified version {next_version}",
    )
