from __future__ import annotations

from acp_evals.assertions import evaluate_assertions
from acp_evals.models import AcpEvent, AssertionSpec, CaseResult


def test_final_contains_reads_jetlinks_reply_shape() -> None:
    result = CaseResult(
        id="case",
        passed=False,
        duration_seconds=0,
        final={"result": {"result": {"reply": "hello ACP_SMOKE_OK"}}},
    )

    failures = evaluate_assertions(
        result,
        [AssertionSpec(type="final_contains", value="ACP_SMOKE_OK")],
    )

    assert failures == []


def test_tool_called_reads_runtime_event_metadata() -> None:
    result = CaseResult(
        id="case",
        passed=False,
        duration_seconds=0,
        events=[
            AcpEvent(
                kind="notification",
                payload={
                    "params": {
                        "update": {
                            "_meta": {
                                "jetlinksRuntimeEvent": {
                                    "type": "tool.started",
                                    "data": {"tool_name": "eval-http__runtime_status"},
                                }
                            }
                        }
                    }
                },
            )
        ],
    )

    failures = evaluate_assertions(
        result,
        [AssertionSpec(type="tool_called", value="eval-http__runtime_status")],
    )

    assert failures == []
