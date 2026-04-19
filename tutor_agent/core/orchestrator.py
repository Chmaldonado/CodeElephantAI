from __future__ import annotations

import json
from typing import Any, Callable

from tutor_agent.llm import LocalLLM
from tutor_agent.models import AgentAction, ToolResult
from tutor_agent.prompts.system_prompt import SYSTEM_PROMPT


ToolFn = Callable[..., Any]


class TutorOrchestrator:
    def __init__(self, llm: LocalLLM, max_steps: int, tools: dict[str, ToolFn]):
        self.llm = llm
        self.max_steps = max_steps
        self.tools = tools
        self.history: list[dict[str, str]] = []
        self.history_limit = 40

    def _append_history(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit :]

    @staticmethod
    def _compact(data: Any, max_chars: int = 1800) -> str:
        text = json.dumps(data, ensure_ascii=True, default=str)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "...(truncated)"

    def _plan_step(self, user_id: str, user_message: str, tool_results: list[ToolResult]) -> AgentAction:
        # Keep planning context bounded so each step stays fast and predictable.
        tools_list = "\n".join(f"- {name}" for name in self.tools.keys())
        transcript = "\n".join(
            [f"{m['role'].upper()}: {m['content']}" for m in self.history[-6:]]
        )
        tool_context = "\n".join(
            [f"{r.tool_name}: {self._compact(r.result)}" for r in tool_results[-2:]]
        )
        user_prompt = f"""
User id: {user_id}
Current message: {user_message}

Available tools:
{tools_list}

Recent transcript:
{transcript}

Recent tool results:
{tool_context}
"""
        try:
            parsed = self.llm.chat_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
            return AgentAction.model_validate(parsed)
        except Exception:
            # Fail closed to a direct response if planning JSON is malformed.
            return AgentAction(action="respond", response="I hit a planning error. Please try again.")

    def run_turn(self, user_id: str, user_message: str) -> str:
        self._append_history(role="user", content=user_message)
        tool_results: list[ToolResult] = []

        # Agent loop: plan -> maybe call tool -> repeat until model returns "respond".
        for _ in range(self.max_steps):
            action = self._plan_step(user_id=user_id, user_message=user_message, tool_results=tool_results)
            if action.action == "respond":
                text = action.response or "I do not have a response yet."
                self._append_history(role="assistant", content=text)
                return text

            if action.action == "tool":
                tool_name = action.tool_name or ""
                args = action.tool_args or {}
                tool = self.tools.get(tool_name)
                if tool is None:
                    tool_results.append(
                        ToolResult(
                            tool_name=tool_name,
                            ok=False,
                            result=f"Tool '{tool_name}' not found.",
                        )
                    )
                    continue
                try:
                    # Tool results are appended as planner context for the next step.
                    result = tool(**args)
                    tool_results.append(ToolResult(tool_name=tool_name, ok=True, result=result))
                except Exception as exc:
                    tool_results.append(ToolResult(tool_name=tool_name, ok=False, result=str(exc)))
                continue

        fallback = (
            "I reached the maximum planning steps. "
            "Please ask again and I will answer directly or with fewer tool calls."
        )
        self._append_history(role="assistant", content=fallback)
        return fallback
