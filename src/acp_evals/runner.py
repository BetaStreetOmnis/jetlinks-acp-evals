from __future__ import annotations

import asyncio
import json
from pathlib import Path

from acp_evals.client import AcpClient
from acp_evals.models import EvalSuite, SuiteResult


def load_suite(path: Path) -> EvalSuite:
    return EvalSuite.model_validate_json(path.read_text(encoding="utf-8"))


async def run_suite(
    suite: EvalSuite,
    *,
    endpoint: str,
    headers: dict[str, str] | None = None,
    concurrency: int = 1,
) -> SuiteResult:
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(case):
        async with semaphore:
            return await AcpClient(endpoint, headers=headers).run_case(case)

    case_results = await asyncio.gather(*(run_one(case) for case in suite.cases))
    passed_count = sum(1 for case in case_results if case.passed)
    failed_count = len(case_results) - passed_count
    return SuiteResult(
        name=suite.name,
        endpoint=endpoint,
        passed=failed_count == 0,
        total=len(case_results),
        passed_count=passed_count,
        failed_count=failed_count,
        cases=case_results,
    )


def write_json_report(result: SuiteResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_markdown_report(result: SuiteResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {result.name}",
        "",
        f"- Endpoint: `{result.endpoint}`",
        f"- Result: {'PASS' if result.passed else 'FAIL'}",
        f"- Passed: {result.passed_count}/{result.total}",
        "",
        "| Case | Status | Duration | Failures |",
        "|---|---:|---:|---|",
    ]
    for case in result.cases:
        failures = "<br>".join(case.failures) if case.failures else ""
        lines.append(
            f"| `{case.id}` | {'PASS' if case.passed else 'FAIL'} | "
            f"{case.duration_seconds:.3f}s | {failures} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
