from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id TEXT PRIMARY KEY,
                skill_level TEXT DEFAULT 'beginner',
                known_topics TEXT DEFAULT '[]',
                struggled_topics TEXT DEFAULT '[]',
                last_summary TEXT DEFAULT ''
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS discussed_topics (
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                mentions INTEGER NOT NULL DEFAULT 1,
                last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, topic)
            )
            """
        )
        self.conn.commit()

    def get_user_progress(self, user_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return {
                "user_id": user_id,
                "skill_level": "beginner",
                "known_topics": [],
                "struggled_topics": [],
                "last_summary": "",
            }
        return {
            "user_id": row["user_id"],
            "skill_level": row["skill_level"],
            "known_topics": json.loads(row["known_topics"]),
            "struggled_topics": json.loads(row["struggled_topics"]),
            "last_summary": row["last_summary"],
        }

    def update_memory(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get_user_progress(user_id)
        merged = {**current, **patch}

        if "known_topics" in merged and isinstance(merged["known_topics"], list):
            merged["known_topics"] = sorted(set(str(x) for x in merged["known_topics"]))
        if "struggled_topics" in merged and isinstance(merged["struggled_topics"], list):
            merged["struggled_topics"] = sorted(set(str(x) for x in merged["struggled_topics"]))

        self.conn.execute(
            """
            INSERT INTO user_progress (user_id, skill_level, known_topics, struggled_topics, last_summary)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                skill_level = excluded.skill_level,
                known_topics = excluded.known_topics,
                struggled_topics = excluded.struggled_topics,
                last_summary = excluded.last_summary
            """,
            (
                user_id,
                str(merged.get("skill_level", "beginner")),
                json.dumps(merged.get("known_topics", [])),
                json.dumps(merged.get("struggled_topics", [])),
                str(merged.get("last_summary", "")),
            ),
        )
        self.conn.commit()
        return self.get_user_progress(user_id)

    def record_discussed_topics(self, user_id: str, topics: list[str]) -> None:
        clean_topics = sorted(
            {
                str(topic).strip().lower()
                for topic in topics
                if str(topic).strip()
            }
        )
        if not clean_topics:
            return

        self.conn.executemany(
            """
            INSERT INTO discussed_topics (user_id, topic, mentions)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, topic) DO UPDATE SET
                mentions = discussed_topics.mentions + 1,
                last_seen = CURRENT_TIMESTAMP
            """,
            [(user_id, topic) for topic in clean_topics],
        )
        self.conn.commit()

    def get_discussed_topics(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT topic, mentions, last_seen
            FROM discussed_topics
            WHERE user_id = ?
            ORDER BY mentions DESC, last_seen DESC
            LIMIT ?
            """,
            (user_id, max(1, int(limit))),
        ).fetchall()
        return [
            {
                "topic": row["topic"],
                "mentions": row["mentions"],
                "last_seen": row["last_seen"],
            }
            for row in rows
        ]
