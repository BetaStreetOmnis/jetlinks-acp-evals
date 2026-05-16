from __future__ import annotations

import json
from urllib.request import Request, urlopen

from acp_evals.mcp_fixture import run_mcp_fixture


def test_mcp_fixture_lists_and_calls_runtime_status_tool() -> None:
    with run_mcp_fixture(port=0) as fixture:
        listed = _post(
            fixture.url,
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        assert listed["result"]["tools"][0]["name"] == "runtime_status"

        called = _post(
            fixture.url,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "runtime_status", "arguments": {}},
            },
        )

    assert called["result"]["structuredContent"]["status"] == "MCP_FIXTURE_OK"


def _post(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:  # noqa: S310 - local test fixture.
        return json.loads(response.read())
