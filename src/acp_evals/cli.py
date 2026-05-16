from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from acp_evals.mcp_fixture import run_mcp_fixture
from acp_evals.runner import load_suite, run_suite, write_json_report, write_markdown_report

console = Console()


@click.group()
def main() -> None:
    """Run ACP-native agent evaluations."""


@main.command("run")
@click.option("--endpoint", required=True, help="ACP WebSocket endpoint, for example ws://127.0.0.1:8010/api/acp/ws")
@click.option("--suite", "suite_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--header", multiple=True, help="HTTP header in Name:Value form. May be repeated.")
@click.option("--concurrency", default=1, show_default=True, type=int)
@click.option(
    "--with-mcp-fixture",
    is_flag=True,
    help="Start a local HTTP MCP fixture at 127.0.0.1:8765/mcp.",
)
@click.option("--mcp-fixture-port", default=8765, show_default=True, type=int)
@click.option(
    "--json-report",
    type=click.Path(path_type=Path),
    default=Path("reports/acp-eval.json"),
)
@click.option("--md-report", type=click.Path(path_type=Path), default=Path("reports/acp-eval.md"))
def run_command(
    endpoint: str,
    suite_path: Path,
    header: tuple[str, ...],
    concurrency: int,
    with_mcp_fixture: bool,
    mcp_fixture_port: int,
    json_report: Path,
    md_report: Path,
) -> None:
    """Run an eval suite against an ACP agent endpoint."""
    headers = _parse_headers(header)
    suite = load_suite(suite_path)
    if with_mcp_fixture:
        with run_mcp_fixture(port=mcp_fixture_port) as fixture:
            console.print(f"Started MCP fixture at {fixture.url}")
            result = asyncio.run(
                run_suite(suite, endpoint=endpoint, headers=headers, concurrency=concurrency)
            )
    else:
        result = asyncio.run(
            run_suite(suite, endpoint=endpoint, headers=headers, concurrency=concurrency)
        )
    write_json_report(result, json_report)
    write_markdown_report(result, md_report)
    _print_summary(result)
    raise SystemExit(0 if result.passed else 1)


def _parse_headers(headers: tuple[str, ...]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for header in headers:
        if ":" not in header:
            raise click.BadParameter(f"header must use Name:Value form: {header}")
        name, value = header.split(":", 1)
        parsed[name.strip()] = value.strip()
    return parsed


def _print_summary(result) -> None:
    table = Table(title=f"{result.name}: {'PASS' if result.passed else 'FAIL'}")
    table.add_column("Case")
    table.add_column("Status")
    table.add_column("Duration", justify="right")
    table.add_column("Failures")
    for case in result.cases:
        table.add_row(
            case.id,
            "PASS" if case.passed else "FAIL",
            f"{case.duration_seconds:.3f}s",
            "\n".join(case.failures),
        )
    console.print(table)
