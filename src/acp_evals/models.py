from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class AcpMessage(BaseModel):
    type: str = "text"
    text: str


class AcpMcpServer(BaseModel):
    name: str
    url: str | None = None
    type: str = "http"
    headers: list[dict[str, str]] = Field(default_factory=list)
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class AcpSessionParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cwd: str | None = None
    mcpServers: list[AcpMcpServer] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict, alias="_meta")


class AssertionSpec(BaseModel):
    type: Literal[
        "final_contains",
        "event_type",
        "tool_called",
        "json_path_equals",
        "no_error",
    ]
    value: Any
    path: str | None = None


class EvalCase(BaseModel):
    id: str
    description: str = ""
    prompt: str | list[AcpMessage]
    session: AcpSessionParams = Field(default_factory=AcpSessionParams)
    timeout_seconds: float = 120.0
    expect: list[AssertionSpec] = Field(default_factory=list)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str | list[AcpMessage]) -> str | list[AcpMessage]:
        if isinstance(value, str) and not value.strip():
            raise ValueError("prompt cannot be empty")
        return value


class EvalSuite(BaseModel):
    name: str
    description: str = ""
    cases: list[EvalCase]


class AcpEvent(BaseModel):
    kind: Literal["response", "notification"]
    payload: dict[str, Any]


class CaseResult(BaseModel):
    id: str
    passed: bool
    duration_seconds: float
    final: dict[str, Any] | None = None
    events: list[AcpEvent] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class SuiteResult(BaseModel):
    name: str
    endpoint: HttpUrl | str
    passed: bool
    total: int
    passed_count: int
    failed_count: int
    cases: list[CaseResult]
