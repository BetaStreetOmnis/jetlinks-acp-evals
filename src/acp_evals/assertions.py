from __future__ import annotations

from typing import Any

from acp_evals.jsonpath import get_path
from acp_evals.models import AssertionSpec, CaseResult


def evaluate_assertions(result: CaseResult, specs: list[AssertionSpec]) -> list[str]:
    failures: list[str] = []
    for spec in specs:
        try:
            failure = _evaluate(result, spec)
        except Exception as exc:  # noqa: BLE001 - assertions should report, not crash the suite.
            failure = f"{spec.type} assertion raised {type(exc).__name__}: {exc}"
        if failure:
            failures.append(failure)
    return failures


def _evaluate(result: CaseResult, spec: AssertionSpec) -> str | None:
    if spec.type == "final_contains":
        haystack = _final_text(result.final)
        if str(spec.value) not in haystack:
            return f"final response does not contain {spec.value!r}"
        return None

    if spec.type == "event_type":
        event_types = [_runtime_event_type(event.payload) for event in result.events]
        if spec.value not in event_types:
            seen = sorted(set(filter(None, event_types)))
            return f"event type {spec.value!r} not found; saw {seen}"
        return None

    if spec.type == "tool_called":
        tools = [_tool_name(event.payload) for event in result.events]
        if spec.value not in tools:
            return f"tool {spec.value!r} not called; saw {sorted(set(filter(None, tools)))}"
        return None

    if spec.type == "json_path_equals":
        if not spec.path:
            return "json_path_equals requires path"
        actual = get_path(result.final or {}, spec.path)
        if actual != spec.value:
            return f"{spec.path} expected {spec.value!r}, got {actual!r}"
        return None

    if spec.type == "no_error":
        errors = [event.payload for event in result.events if _is_error_event(event.payload)]
        if result.final and "error" in result.final:
            errors.append(result.final["error"])
        if errors:
            return f"unexpected errors: {errors}"
        return None

    return f"unknown assertion type {spec.type}"


def _final_text(final: dict[str, Any] | None) -> str:
    if not final:
        return ""
    candidates = [
        "result.result.reply",
        "result.reply",
        "result.content[0].text",
        "result.text",
    ]
    for path in candidates:
        try:
            value = get_path(final, path)
        except KeyError:
            continue
        if isinstance(value, str):
            return value
    return str(final)


def _runtime_event_type(payload: dict[str, Any]) -> str | None:
    candidates = [
        "params.update._meta.jetlinksRuntimeEvent.type",
        "params.update.sessionUpdate",
        "method",
    ]
    for path in candidates:
        try:
            value = get_path(payload, path)
        except KeyError:
            continue
        if isinstance(value, str):
            return value
    return None


def _tool_name(payload: dict[str, Any]) -> str | None:
    candidates = [
        "params.update._meta.jetlinksRuntimeEvent.data.tool_name",
        "params.update._meta.jetlinksRuntimeEvent.data.tool",
    ]
    for path in candidates:
        try:
            value = get_path(payload, path)
        except KeyError:
            continue
        if isinstance(value, str):
            return value
    return None


def _is_error_event(payload: dict[str, Any]) -> bool:
    if "error" in payload:
        return True
    event_type = _runtime_event_type(payload)
    return bool(event_type and (event_type.endswith(".failed") or event_type == "error"))
