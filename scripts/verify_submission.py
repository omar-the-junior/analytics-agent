"""Produce a truthful, reproducible submission-evidence report.

This command validates repository-level requirements that can be checked without an
LLM call. It intentionally does not treat the presence of an evaluation contract
as proof that the 72-case baseline has been implemented or passed.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPOSITORY_ROOT / "artifacts" / "submission-proof.json"


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
    case_files = list((REPOSITORY_ROOT / "evaluation").glob("cases/**/*.json"))
    tool_files = list((REPOSITORY_ROOT / "backend" / "app").glob("*workbook*.py"))
    ready = bool(case_files and tool_files)
    return Check(
        "baseline release readiness",
        ready,
        (
            "runnable evaluation cases and workbook-tool implementation are present"
            if ready
            else (
                "not release-ready: runnable evaluation cases and workbook-tool "
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
    release_ready = all(check.passed for check in checks)
    report = {
        "schema_version": "1.0",
        "release_ready": release_ready,
        "checks": [asdict(check) for check in checks],
        "next_action": (
            "Run the full baseline evaluator and attach its report."
            if release_ready
            else (
                "Implement workbook tools and runnable baseline cases; do not represent "
                "this repository as submission-ready."
            )
        ),
    }
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if release_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
