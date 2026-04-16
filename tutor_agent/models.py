from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    action: Literal["tool", "respond"] = Field(
        description="Either call a tool or respond directly to the user."
    )
    tool_name: str | None = Field(default=None)
    tool_args: dict[str, Any] | None = Field(default=None)
    response: str | None = Field(default=None)
    reasoning: str | None = Field(default=None)


class ToolResult(BaseModel):
    tool_name: str
    ok: bool
    result: Any


class DocChunk(BaseModel):
    id: str
    source: str
    text: str

