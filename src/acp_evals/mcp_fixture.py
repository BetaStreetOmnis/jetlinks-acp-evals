from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass(frozen=True)
class McpFixtureServer:
    host: str
    port: int
    path: str
    httpd: ThreadingHTTPServer
    thread: threading.Thread

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self.path}"

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


@contextmanager
def run_mcp_fixture(
    host: str = "127.0.0.1",
    port: int = 8765,
    path: str = "/mcp",
) -> Iterator[McpFixtureServer]:
    handler = _handler_for_path(path)
    httpd = ThreadingHTTPServer((host, port), handler)
    actual_port = int(httpd.server_address[1])
    thread = threading.Thread(target=httpd.serve_forever, name="acp-evals-mcp-fixture", daemon=True)
    thread.start()
    server = McpFixtureServer(host=host, port=actual_port, path=path, httpd=httpd, thread=thread)
    try:
        yield server
    finally:
        server.close()


def _handler_for_path(expected_path: str) -> type[BaseHTTPRequestHandler]:
    class McpFixtureHandler(BaseHTTPRequestHandler):
        server_version = "AcpEvalsMcpFixture/0.1"

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json({"status": "ok", "service": "acp-evals-mcp-fixture"})
                return
            self.send_error(404)

        def do_POST(self) -> None:
            if self.path != expected_path:
                self.send_error(404)
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._send_json(_error(None, -32700, "Parse error"), status=400)
                return

            if isinstance(payload, list):
                self._send_json([_handle_rpc(item) for item in payload if "id" in item])
                return

            if "id" not in payload:
                self.send_response(204)
                self.end_headers()
                return

            self._send_json(_handle_rpc(payload))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _send_json(
            self,
            payload: dict[str, Any] | list[dict[str, Any]],
            status: int = 200,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return McpFixtureHandler


def _handle_rpc(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = payload.get("id")
    method = payload.get("method")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "acp-evals-mcp-fixture", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "runtime_status",
                        "description": "Return deterministic status for ACP evals.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False,
                        },
                    }
                ]
            },
        }
    if method == "tools/call":
        params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
        name = params.get("name")
        if name != "runtime_status":
            return _error(request_id, -32602, f"Unknown tool: {name}")
        result = {
            "status": "MCP_FIXTURE_OK",
            "source": "acp-evals",
        }
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "structuredContent": result,
                "isError": False,
            },
        }
    return _error(request_id, -32601, f"Method not found: {method}")


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }
