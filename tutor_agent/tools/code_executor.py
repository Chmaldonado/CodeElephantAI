from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


class ExecuteCodeTool:
    name = "execute_code"
    description = "Executes user code snippets in an isolated subprocess with basic safety guards."
    BLOCKED_PATTERNS: list[tuple[str, str]] = [
        (
            r"\b(import|from)\s+(os|subprocess|socket|shutil|ctypes|requests|httpx|urllib)\b",
            "Blocked module import for safety.",
        ),
        (
            r"\b(open|exec|eval|compile|__import__)\s*\(",
            "Blocked runtime primitive for safety.",
        ),
    ]

    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds

    def _validate_snippet(self, snippet: str) -> str | None:
        if not snippet.strip():
            return "Snippet is empty."
        if len(snippet) > 12000:
            return "Snippet too long for local executor (max 12000 characters)."
        for pattern, reason in self.BLOCKED_PATTERNS:
            if re.search(pattern, snippet, flags=re.IGNORECASE):
                return reason
        return None

    def __call__(self, snippet: str, lang: str = "python") -> dict:
        lang = lang.lower().strip()
        if lang != "python":
            return {
                "ok": False,
                "error": "Only 'python' is supported in this local executor. Swap this tool with E2B/Judge0 for multi-language."
            }
        validation_error = self._validate_snippet(snippet)
        if validation_error:
            return {
                "ok": False,
                "error": validation_error,
            }

        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "snippet.py"
            file_path.write_text(snippet, encoding="utf-8")
            env = dict(os.environ)
            env.update(
                {
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONNOUSERSITE": "1",
                }
            )
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=tmp,
                    env=env,
                )
                return {
                    "ok": completed.returncode == 0,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "exit_code": completed.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": f"Execution timed out after {self.timeout_seconds}s."}
