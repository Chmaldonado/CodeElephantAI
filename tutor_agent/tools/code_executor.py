from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class ExecuteCodeTool:
    name = "execute_code"
    description = "Executes user code snippets in a local constrained subprocess."

    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds

    def __call__(self, snippet: str, lang: str = "python") -> dict:
        lang = lang.lower().strip()
        if lang != "python":
            return {
                "ok": False,
                "error": "Only 'python' is supported in this local executor. Swap this tool with E2B/Judge0 for multi-language."
            }

        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "snippet.py"
            file_path.write_text(snippet, encoding="utf-8")
            try:
                completed = subprocess.run(
                    ["python", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                return {
                    "ok": completed.returncode == 0,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "exit_code": completed.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": f"Execution timed out after {self.timeout_seconds}s."}

