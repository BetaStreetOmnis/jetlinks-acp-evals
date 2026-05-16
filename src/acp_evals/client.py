from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import websockets

from acp_evals.assertions import evaluate_assertions
from acp_evals.models import AcpEvent, CaseResult, EvalCase


class AcpClient:
    def __init__(
        self,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        subprotocol: str = "acp.v1",
    ) -> None:
        self.endpoint = endpoint
        self.headers = headers or {}
        self.subprotocol = subprotocol
        self._next_id = 1

    async def run_case(self, case: EvalCase) -> CaseResult:
        started = time.perf_counter()
        events: list[AcpEvent] = []
        failures: list[str] = []
        final: dict[str, Any] | None = None

        try:
            async with websockets.connect(
                self.endpoint,
                additional_headers=self.headers,
                subprotocols=[self.subprotocol],
                open_timeout=10,
            ) as websocket:
                await self._send(websocket, "initialize", {})
                initialize = await self._read_response(websocket, self._next_id - 1, events, 15)
                if "error" in initialize:
                    failures.append(f"initialize failed: {initialize['error']}")

                session_params = case.session.model_dump(exclude_none=True, by_alias=True)
                await self._send(websocket, "session/new", session_params)
                created = await self._read_response(websocket, self._next_id - 1, events, 15)
                session_id = _get(created, "result.sessionId")
                if not session_id:
                    failures.append(f"new_session did not return sessionId: {created}")

                prompt_params = dict(session_params)
                prompt_params["sessionId"] = session_id
                prompt_params["prompt"] = _prompt_payload(case.prompt)
                await self._send(websocket, "session/prompt", prompt_params)
                final = await self._read_response(
                    websocket,
                    self._next_id - 1,
                    events,
                    case.timeout_seconds,
                )
        except Exception as exc:  # noqa: BLE001 - eval runner should produce a report.
            message = str(exc) or repr(exc)
            failures.append(f"{type(exc).__name__}: {message}")

        result = CaseResult(
            id=case.id,
            passed=False,
            duration_seconds=round(time.perf_counter() - started, 3),
            final=final,
            events=events,
            failures=failures,
        )
        result.failures.extend(evaluate_assertions(result, case.expect))
        result.passed = not result.failures
        return result

    async def _send(self, websocket: Any, method: str, params: dict[str, Any]) -> None:
        packet = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params,
        }
        self._next_id += 1
        await websocket.send(json.dumps(packet, ensure_ascii=False))

    async def _read_response(
        self,
        websocket: Any,
        request_id: int,
        events: list[AcpEvent],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timed out waiting for response id {request_id}")
            raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            payload = json.loads(raw)
            if payload.get("id") == request_id:
                events.append(AcpEvent(kind="response", payload=payload))
                return payload
            events.append(AcpEvent(kind="notification", payload=payload))


def _prompt_payload(prompt: str | list[Any]) -> list[dict[str, Any]]:
    if isinstance(prompt, str):
        return [{"type": "text", "text": prompt}]
    return [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in prompt]


def _get(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current
