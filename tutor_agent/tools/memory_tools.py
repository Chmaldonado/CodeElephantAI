from __future__ import annotations

from typing import Any

from tutor_agent.memory.store import MemoryStore


class GetUserProgressTool:
    name = "get_user_progress"
    description = "Gets long-term learner profile and progress."

    def __init__(self, store: MemoryStore):
        self.store = store

    def __call__(self, user_id: str) -> dict:
        return self.store.get_user_progress(user_id=user_id)


class UpdateMemoryTool:
    name = "update_memory"
    description = "Updates long-term learner memory/profile."

    def __init__(self, store: MemoryStore):
        self.store = store

    def __call__(self, user_id: str, patch: dict[str, Any]) -> dict:
        return self.store.update_memory(user_id=user_id, patch=patch)

