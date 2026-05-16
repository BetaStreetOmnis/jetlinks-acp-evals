# JetLinks ACP Evals

ACP-native evaluation harness for coding agents and MCP-enabled agent runtimes.

The project is intentionally small: it connects to an Agent Client Protocol
WebSocket endpoint, creates sessions, sends prompts, records runtime
notifications, and checks assertions against the final response and event stream.

## Why this exists

There is no mature, widely adopted ACP-native benchmark yet. Existing agent
benchmarks usually test a local CLI, a hosted API, or a bespoke harness. This
project focuses on the protocol boundary:

- ACP session lifecycle compatibility
- `params._meta` extension handling
- `params.mcpServers` dynamic MCP tool injection
- runtime event and tool trajectory checks
- coding-agent task results
- future integration with `agentevals`, SWE-bench-style tasks, and ACP registry
  comparison runs

## Install

```bash
uv sync
```

Run the CLI from the project root:

```bash
uv run acp-evals --help
```

## Quick Start

Start an ACP WebSocket agent, for example JetLinks Agent Runtime:

```bash
cd ../jetlinks-agent-runtime-agent-v2-branch
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Run the smoke suite:

```bash
cd ../jetlinks-acp-evals
uv run acp-evals run \
  --endpoint ws://127.0.0.1:8010/api/acp/ws \
  --suite eval_sets/acp_smoke.json
```

Reports are written to:

```text
reports/acp-eval.json
reports/acp-eval.md
```

## Eval Suite Format

```json
{
  "name": "acp-smoke",
  "cases": [
    {
      "id": "simple-chat",
      "prompt": "Reply with exactly: ACP_SMOKE_OK",
      "session": {
        "cwd": "/tmp",
        "mcpServers": [],
        "_meta": {
          "appTemplateName": "_debug-acp-evals"
        }
      },
      "expect": [
        {
          "type": "final_contains",
          "value": "ACP_SMOKE_OK"
        }
      ]
    }
  ]
}
```

Supported assertions:

- `final_contains`: final response contains text.
- `event_type`: runtime event stream contains an event type.
- `tool_called`: runtime event stream contains a tool call.
- `json_path_equals`: final JSON response path equals a value.
- `no_error`: no JSON-RPC error or failed runtime event was observed.

## MCP Dynamic Tool Eval

`eval_sets/mcp_dynamic_tools.json` shows the intended shape:

```json
{
  "session": {
    "mcpServers": [
      {
        "name": "eval-http",
        "url": "http://127.0.0.1:9999/mcp",
        "type": "http"
      }
    ]
  }
}
```

The harness does not start MCP servers for you yet. Keep MCP fixtures explicit so
the same suite can run against multiple ACP agents.

## Roadmap

- ACP lifecycle suite: `load`, `fork`, `resume`, `cancel`, modes, config options.
- MCP fixtures: local HTTP and stdio MCP test servers.
- Coding fixtures: single-file, multi-file, large-file patch, and real-repo tasks.
- Browser E2E: Workbench send message, upload file, event inspector.
- Trace export: OpenTelemetry output for `agentevals`.
- Agent registry runner: execute the same suite against agents from the Agent
  Client Protocol registry.
- SWE-bench Lite adapter with local repository cache.

## License

Apache-2.0
