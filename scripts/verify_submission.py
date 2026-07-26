"""Produce a truthful, reproducible submission-evidence report.

This command validates repository-level requirements that can be checked without an
LLM call. It intentionally does not treat the presence of an evaluation contract
as proof that the 72-case baseline has been implemented or passed.
"""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPOSITORY_ROOT / "artifacts" / "submission-proof.json"
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))
sys.path.insert(0, str(REPOSITORY_ROOT))

from evaluation.baseline import evaluate  # noqa: E402


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    evidence: str


def exists(relative_path: str) -> Check:
    path = REPOSITORY_ROOT / relative_path
    status = "exists" if path.is_file() else "is missing"
    return Check(relative_path, path.is_file(), f"{relative_path} {status}")


def contract_shape() -> Check:
    path = REPOSITORY_ROOT / "evaluation" / "contract.json"
    if not path.is_file():
        return Check("evaluation contract", False, "evaluation/contract.json is missing")
    contract = json.loads(path.read_text(encoding="utf-8"))
    expected_cases = contract.get("corpus", {}).get("total_cases")
    return Check(
        "evaluation contract",
        expected_cases == 72,
        f"evaluation/contract.json declares {expected_cases!r} baseline cases (expected 72)",
    )


def no_agent_framework_dependencies() -> Check:
    project = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    forbidden = ["langchain", "llamaindex", "autogen", "crewai"]
    found = [name for name in forbidden if name in project]
    return Check(
        "framework-free dependencies",
        not found,
        (
            "no forbidden agent-framework dependency found"
            if not found
            else f"forbidden dependencies: {', '.join(found)}"
        ),
    )


def implementation_readiness() -> Check:
    """Keep release status honest until runnable cases and workbook tools exist."""
    case_module = REPOSITORY_ROOT / "evaluation" / "baseline.py"
    tool_module = REPOSITORY_ROOT / "backend" / "app" / "workbook_session.py"
    ready = case_module.is_file() and tool_module.is_file()
    return Check(
        "baseline release readiness",
        ready,
        (
            "runnable evaluation corpus and WorkbookSession implementation are present"
            if ready
            else (
                "not release-ready: runnable evaluation corpus and WorkbookSession "
                "implementation are required"
            )
        ),
    )


def main() -> int:
    checks = [
        exists("README.md"),
        exists("DECISIONS.md"),
        exists("docs/submission-evidence.md"),
        exists("docs/live-defense.md"),
        exists("docs/task-reqs/Real Estate Listings.xlsx"),
        exists("docs/task-reqs/Marketing Campaigns.xlsx"),
        contract_shape(),
        no_agent_framework_dependencies(),
        implementation_readiness(),
    ]
    baseline = evaluate()
    release_ready = all(check.passed for check in checks) and baseline["release_ready"]
    report = {
        "schema_version": "1.0",
        "release_ready": release_ready,
        "checks": [asdict(check) for check in checks],
        "next_action": (
            "Attach the generated full baseline report to the release evidence."
            if release_ready
            else (
                "Fix failing baseline cases or release checks; do not represent this repository "
                "as submission-ready."
            )
        ),
        "baseline_evaluation": baseline,
    }
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if release_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
