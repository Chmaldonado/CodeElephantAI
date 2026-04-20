from __future__ import annotations

import json
import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

try:
    from pygments import lex
    from pygments.lexers import TextLexer, get_lexer_by_name
    from pygments.token import Token
    from pygments.util import ClassNotFound

    HAS_PYGMENTS = True
except Exception:
    HAS_PYGMENTS = False

try:
    import winsound

    HAS_WINSOUND = True
except Exception:
    winsound = None
    HAS_WINSOUND = False

try:
    import ctypes

    _mci_send_string = ctypes.windll.winmm.mciSendStringW
    HAS_WIN_MCI = True
except Exception:
    _mci_send_string = None
    HAS_WIN_MCI = False

from tutor_agent.bootstrap import AppServices
from tutor_agent.topics import extract_topics, format_discussed_topics
from tutor_agent.ui_common import (
    format_progress,
    format_search_result,
    normalize_lexer_name,
    parse_quiz_topic_and_difficulty,
    split_message_segments,
)


def _runtime_base_dir() -> Path:
    # In frozen builds (PyInstaller), use the executable folder so users can
    # customize sounds/icons by dropping files next to the .exe.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _runtime_user_data_dir(base_dir: Path) -> Path:
    if not getattr(sys, "frozen", False):
        return base_dir / "data"
    if sys.platform.startswith("win"):
        local_app_data = os.getenv("LOCALAPPDATA", "").strip()
        if local_app_data:
            base = Path(local_app_data).expanduser()
            if str(base).strip():
                return base / "CodeElephantTutor" / "data"
    return Path.home() / ".codeelephanttutor" / "data"


class AIMDesktopApp:
    HELP_TEXT = (
        "Commands:\n"
        "/ask <message>\n"
        "/search <query>\n"
        "/quiz <topic> [easy|medium|hard]\n"
        "/topics\n"
        "/progress\n"
        "/quit\n\n"
        "Use the Code... button to paste multiline snippets."
    )

    def __init__(self, user_id: str, services: AppServices):
        self.user_id = user_id
        self.orchestrator = services.orchestrator
        self.memory = services.memory
        self.tools = self.orchestrator.tools
        self.busy = False
        self.enable_sounds = True
        self.base_dir = _runtime_base_dir()
        self.sounds_dir = self.base_dir / "assets" / "sounds"
        self.branding_dir = self.base_dir / "assets" / "branding"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        self.branding_dir.mkdir(parents=True, exist_ok=True)
        self.send_sound_file = self.sounds_dir / "aim-send.mp3"
        self.receive_sound_file = self.sounds_dir / "aim-instant-message.mp3"
        self.window_icon_file = self.branding_dir / "app-icon.ico"
        self.window_icon_png = self.branding_dir / "app-icon.png"
        self.chat_save_dir = _runtime_user_data_dir(self.base_dir) / "saved_chats"
        self._icon_photo = None
        self.chat_entries: list[dict[str, str]] = []

        self.root = tk.Tk()
        self.root.title("CodeElephant Tutor - AIM")
        self.root.geometry("980x640")
        self.root.minsize(860, 520)
        self.root.configure(bg="#d4d0c8")
        self._apply_window_icon()
        # Keep font setup robust across Tk builds on Windows.
        try:
            self.root.option_add("*Font", "{Segoe UI} 10")
        except Exception:
            self.root.option_add("*Font", "TkDefaultFont")

        self._build_ui()
        self._append_tutor("Welcome. Type /help for commands.", play_sound=False)

    def _apply_window_icon(self) -> None:
        try:
            if sys.platform.startswith("win") and self.window_icon_file.exists():
                self.root.iconbitmap(default=str(self.window_icon_file))
                return
            if self.window_icon_png.exists():
                self._icon_photo = tk.PhotoImage(file=str(self.window_icon_png))
                self.root.iconphoto(True, self._icon_photo)
                return
            if self.window_icon_file.exists():
                self._icon_photo = tk.PhotoImage(file=str(self.window_icon_file))
                self.root.iconphoto(True, self._icon_photo)
        except Exception:
            # Ignore icon failures so UI always starts.
            pass

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg="#d4d0c8")
        outer.pack(fill="both", expand=True, padx=8, pady=8)

        right = tk.Frame(outer, bg="#d4d0c8")
        right.pack(fill="both", expand=True)

        top_bar = tk.Frame(right, bg="#0a246a")
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="CodeElephant AIM", bg="#0a246a", fg="white", padx=10, pady=4).pack(
            side="left"
        )
        self.status_label = tk.Label(top_bar, text="Ready", bg="#0a246a", fg="#bcd8ff", padx=10)
        self.status_label.pack(side="right")

        self.transcript = ScrolledText(
            right,
            wrap="word",
            bg="white",
            fg="black",
            insertbackground="black",
            relief="sunken",
            bd=1,
            font=("Consolas", 10),
        )
        self.transcript.pack(fill="both", expand=True, pady=(8, 8))
        self.transcript.configure(state="disabled")
        self.transcript.tag_configure("meta", foreground="#666666")
        self.transcript.tag_configure("you", foreground="#0033cc")
        self.transcript.tag_configure("tutor", foreground="#0c7a2f")
        self.transcript.tag_configure("error", foreground="#b00020")
        self.transcript.tag_configure("code_base", foreground="#1f1f1f", background="#f5f5f5", font=("Consolas", 10))
        self.transcript.tag_configure(
            "code_keyword", foreground="#0000cc", background="#f5f5f5", font=("Consolas", 10, "bold")
        )
        self.transcript.tag_configure("code_string", foreground="#a31515", background="#f5f5f5", font=("Consolas", 10))
        self.transcript.tag_configure("code_comment", foreground="#008000", background="#f5f5f5", font=("Consolas", 10))
        self.transcript.tag_configure("code_number", foreground="#098658", background="#f5f5f5", font=("Consolas", 10))
        self.transcript.tag_configure("code_operator", foreground="#111111", background="#f5f5f5", font=("Consolas", 10))
        self.transcript.tag_configure(
            "code_function", foreground="#795e26", background="#f5f5f5", font=("Consolas", 10, "bold")
        )
        self.transcript.tag_configure("code_class", foreground="#267f99", background="#f5f5f5", font=("Consolas", 10))
        self.transcript.tag_configure("code_builtin", foreground="#af00db", background="#f5f5f5", font=("Consolas", 10))

        input_frame = tk.Frame(right, bg="#d4d0c8")
        input_frame.pack(fill="x")

        self.input_box = tk.Text(
            input_frame,
            height=4,
            wrap="word",
            bg="white",
            fg="black",
            insertbackground="black",
            font=("Consolas", 10),
            relief="sunken",
            bd=1,
        )
        self.input_box.pack(fill="x", expand=True)
        self.input_box.bind("<Return>", self._on_enter)

        buttons = tk.Frame(right, bg="#d4d0c8")
        buttons.pack(fill="x", pady=(6, 0))
        self.send_button = tk.Button(buttons, text="Send", width=10, command=self._on_send)
        self.send_button.pack(side="left")
        tk.Button(buttons, text="Code...", width=10, command=self._open_code_dialog).pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="Topics", width=10, command=self._open_topics_dialog).pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="Progress", width=10, command=self._open_progress_dialog).pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="Save Chat", width=10, command=self._save_chat_dialog).pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="Load Chat", width=10, command=self._load_chat_dialog).pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="Help", width=10, command=self._open_help_dialog).pack(
            side="left",
            padx=(6, 0),
        )

        hint = "Enter sends. Shift+Enter adds newline. Commands: /ask /search /quiz /topics /progress /quit"
        tk.Label(right, text=hint, bg="#d4d0c8", fg="#333333", anchor="w").pack(fill="x", pady=(6, 0))

    def _on_enter(self, event: tk.Event) -> str | None:
        if event.state & 0x0001:
            return None
        self._on_send()
        return "break"

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.send_button.configure(state="disabled" if busy else "normal")
        self.status_label.configure(text="Thinking..." if busy else "Ready")

    def _append_line(self, speaker: str, text: str, tag: str, record: bool = True) -> None:
        ts = datetime.now().strftime("%H:%M")
        message = (text or "").rstrip() or ""
        segments = split_message_segments(message)

        self.transcript.configure(state="normal")
        header_printed = False
        first_text_line = True
        for kind, lang, payload in segments:
            if kind == "text":
                lines = payload.splitlines()
                if not lines:
                    continue
                for line in lines:
                    if first_text_line:
                        self.transcript.insert("end", f"[{ts}] ", ("meta",))
                        self.transcript.insert("end", f"{speaker}: ", (tag,))
                        self.transcript.insert("end", line + "\n", (tag,))
                        header_printed = True
                        first_text_line = False
                    else:
                        self.transcript.insert("end", "       " + line + "\n", (tag,))
                continue

            if not header_printed:
                self.transcript.insert("end", f"[{ts}] ", ("meta",))
                self.transcript.insert("end", f"{speaker}:\n", (tag,))
                header_printed = True
                first_text_line = False
            self._insert_code_block(code=payload, lang=lang)

        if not header_printed:
            self.transcript.insert("end", f"[{ts}] ", ("meta",))
            self.transcript.insert("end", f"{speaker}:\n", (tag,))

        self.transcript.insert("end", "\n", ("meta",))
        self.transcript.configure(state="disabled")
        self.transcript.see("end")
        if record:
            self.chat_entries.append({"speaker": speaker, "tag": tag, "text": message})

    def _insert_code_block(self, code: str, lang: str) -> None:
        shown_lang = lang.strip() or "text"
        self.transcript.insert("end", f"       ```{shown_lang}\n", ("meta",))
        lexer_name = normalize_lexer_name(shown_lang)
        lexer = None
        if HAS_PYGMENTS:
            try:
                lexer = get_lexer_by_name(lexer_name)
            except ClassNotFound:
                lexer = TextLexer()

        code_lines = code.splitlines() or [""]
        for line in code_lines:
            self.transcript.insert("end", "       ", ("meta",))
            self._insert_highlighted_line(line, lexer=lexer)
            self.transcript.insert("end", "\n", ("code_base",))
        self.transcript.insert("end", "       ```\n", ("meta",))

    def _insert_highlighted_line(self, line: str, lexer: object | None) -> None:
        if not HAS_PYGMENTS or lexer is None:
            self.transcript.insert("end", line, ("code_base",))
            return
        for token_type, value in lex(line, lexer):
            self.transcript.insert("end", value, (self._token_tag(token_type),))

    @staticmethod
    def _token_tag(token_type: object) -> str:
        if token_type in Token.Keyword:
            return "code_keyword"
        if token_type in Token.String:
            return "code_string"
        if token_type in Token.Comment:
            return "code_comment"
        if token_type in Token.Number:
            return "code_number"
        if token_type in Token.Operator:
            return "code_operator"
        if token_type in Token.Name.Function:
            return "code_function"
        if token_type in Token.Name.Class:
            return "code_class"
        if token_type in Token.Name.Builtin:
            return "code_builtin"
        return "code_base"

    def _append_you(self, text: str, play_sound: bool = True) -> None:
        if play_sound:
            self._play_send_sound()
        self._append_line("You", text, "you")

    def _append_tutor(self, text: str, play_sound: bool = True) -> None:
        if play_sound:
            self._play_receive_sound()
        self._append_line("Tutor", text, "tutor")

    def _append_error(self, text: str, play_sound: bool = True) -> None:
        if play_sound:
            self._play_error_sound()
        self._append_line("Tutor", text, "error")

    def _play_send_sound(self) -> None:
        if not self.enable_sounds:
            return
        if self._play_custom_mp3(self.send_sound_file, alias="codeelephant_send"):
            return
        if HAS_WINSOUND and sys.platform.startswith("win"):
            try:
                winsound.MessageBeep(winsound.MB_OK)
                return
            except Exception:
                pass
        self.root.bell()

    def _play_receive_sound(self) -> None:
        if not self.enable_sounds:
            return
        if self._play_custom_mp3(self.receive_sound_file, alias="codeelephant_receive"):
            return
        if HAS_WINSOUND and sys.platform.startswith("win"):
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                return
            except Exception:
                pass
        self.root.bell()

    def _play_error_sound(self) -> None:
        if not self.enable_sounds:
            return
        if self._play_custom_mp3(self.receive_sound_file, alias="codeelephant_error"):
            return
        if HAS_WINSOUND and sys.platform.startswith("win"):
            try:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                return
            except Exception:
                pass
        self.root.bell()

    @staticmethod
    def _mci(command: str) -> int:
        if not HAS_WIN_MCI or _mci_send_string is None:
            return -1
        return int(_mci_send_string(command, None, 0, None))

    def _play_custom_mp3(self, path: Path, alias: str) -> bool:
        if not sys.platform.startswith("win"):
            return False
        if not path.exists():
            return False
        if not HAS_WIN_MCI:
            return False

        path_text = str(path.resolve()).replace('"', '""')
        self._mci(f"close {alias}")
        opened = self._mci(f'open "{path_text}" type mpegvideo alias {alias}') == 0
        if not opened:
            return False
        played = self._mci(f"play {alias} from 0") == 0
        if not played:
            self._mci(f"close {alias}")
            return False
        return True

    def _on_send(self) -> None:
        raw = self.input_box.get("1.0", "end").strip()
        self.input_box.delete("1.0", "end")
        if not raw:
            return
        self._submit_user_message(raw)

    def _submit_user_message(self, message: str) -> None:
        clean = message.strip()
        if not clean:
            return

        self._append_you(clean)
        lower = clean.lower()
        if lower in {"/help", "help"}:
            self._append_tutor(self.HELP_TEXT)
            return
        if lower in {"/quit", "quit", "exit"}:
            self.root.destroy()
            return
        if lower in {"/topics", "topics"}:
            self._show_topics()
            return
        if lower in {"/progress", "progress"}:
            self._show_progress()
            return
        if lower.startswith("/search "):
            query = clean.split(" ", 1)[1].strip()
            if not query:
                self._append_error("Usage: /search <query>")
                return
            payload = self.tools["search_docs"](query=query)
            self._append_tutor(format_search_result(payload))
            return
        if lower.startswith("/quiz "):
            body = clean.split(" ", 1)[1].strip()
            topic, difficulty = parse_quiz_topic_and_difficulty(body)
            if not topic:
                self._append_error("Usage: /quiz <topic> [easy|medium|hard]")
                return
            payload = self.tools["generate_quiz"](topic=topic, difficulty=difficulty)
            self._append_tutor(json.dumps(payload, ensure_ascii=True, indent=2))
            return
        if lower.startswith("/ask "):
            clean = clean.split(" ", 1)[1].strip()
            if not clean:
                self._append_error("Usage: /ask <message>")
                return
        elif clean.startswith("/"):
            self._append_error("Unknown command. Type /help.")
            return

        if self.busy:
            self._append_error("Still working on your previous request.")
            return

        self._set_busy(True)
        worker = threading.Thread(target=self._run_tutor_turn, args=(clean,), daemon=True)
        worker.start()

    def _run_tutor_turn(self, message: str) -> None:
        try:
            self.memory.record_discussed_topics(user_id=self.user_id, topics=extract_topics(message))
            reply = self.orchestrator.run_turn(user_id=self.user_id, user_message=message)
            self.root.after(0, lambda: self._finish_tutor_turn(reply, False))
        except Exception as exc:
            self.root.after(0, lambda: self._finish_tutor_turn(str(exc), True))

    def _finish_tutor_turn(self, output: str, is_error: bool) -> None:
        self._set_busy(False)
        if is_error:
            self._append_error(f"Error: {output}")
        else:
            self._append_tutor(output)

    def _show_topics(self) -> None:
        entries = self.memory.get_discussed_topics(user_id=self.user_id, limit=20)
        self._append_tutor(format_discussed_topics(entries, heading="Tracked topics:"))

    def _show_progress(self) -> None:
        payload = self.memory.get_user_progress(user_id=self.user_id)
        self._append_tutor(format_progress(payload))

    def _open_text_dialog(self, title: str, body: str, width: str = "760x520") -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(width)
        dialog.minsize(620, 380)
        dialog.configure(bg="#d4d0c8")

        content = ScrolledText(
            dialog,
            wrap="word",
            bg="white",
            fg="black",
            insertbackground="black",
            font=("Consolas", 10),
            relief="sunken",
            bd=1,
        )
        content.pack(fill="both", expand=True, padx=8, pady=(8, 6))
        content.insert("1.0", (body or "").rstrip() + "\n")
        content.configure(state="disabled")

        footer = tk.Frame(dialog, bg="#d4d0c8")
        footer.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(footer, text="Close", width=10, command=dialog.destroy).pack(side="right")

    def _open_help_dialog(self) -> None:
        self._open_text_dialog(title="Help", body=self.HELP_TEXT, width="760x520")

    def _open_topics_dialog(self) -> None:
        entries = self.memory.get_discussed_topics(user_id=self.user_id, limit=40)
        body = format_discussed_topics(entries, heading="Tracked topics:")
        self._open_text_dialog(title="Topics", body=body, width="760x520")

    def _open_progress_dialog(self) -> None:
        payload = self.memory.get_user_progress(user_id=self.user_id)
        body = format_progress(payload)
        self._open_text_dialog(title="Progress", body=body, width="760x520")

    def _open_code_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Code Snippet")
        dialog.geometry("760x520")
        dialog.minsize(620, 420)
        dialog.configure(bg="#d4d0c8")

        top = tk.Frame(dialog, bg="#d4d0c8")
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text="Language:", bg="#d4d0c8").pack(side="left")
        lang_var = tk.StringVar(value="python")
        tk.Entry(top, textvariable=lang_var, width=16).pack(side="left", padx=(6, 14))
        tk.Label(top, text="Optional note:", bg="#d4d0c8").pack(side="left")
        note_var = tk.StringVar(value="")
        tk.Entry(top, textvariable=note_var).pack(side="left", fill="x", expand=True, padx=(6, 0))

        editor = ScrolledText(
            dialog,
            wrap="none",
            bg="white",
            fg="black",
            insertbackground="black",
            font=("Consolas", 10),
            relief="sunken",
            bd=1,
        )
        editor.pack(fill="both", expand=True, padx=8, pady=4)

        buttons = tk.Frame(dialog, bg="#d4d0c8")
        buttons.pack(fill="x", padx=8, pady=(4, 8))

        def build_fenced() -> tuple[str, str, str]:
            lang = (lang_var.get() or "python").strip()
            code = editor.get("1.0", "end").rstrip()
            note = note_var.get().strip()
            return lang, code, note

        def send_to_tutor() -> None:
            lang, code, note = build_fenced()
            if not code:
                self._append_error("Code dialog is empty.")
                return
            fenced = f"```{lang}\n{code}\n```"
            message = f"{note}\n\n{fenced}".strip() if note else fenced
            dialog.destroy()
            self._submit_user_message(message)

        def run_local() -> None:
            lang, code, _note = build_fenced()
            if not code:
                self._append_error("Code dialog is empty.")
                return
            self._append_you(f"/run {lang}\n```{lang}\n{code}\n```")
            result = self.tools["execute_code"](snippet=code, lang=lang)
            self._append_tutor(json.dumps(result, ensure_ascii=True, indent=2))

        tk.Button(buttons, text="Send To Tutor", width=14, command=send_to_tutor).pack(side="left")
        tk.Button(buttons, text="Run Locally", width=12, command=run_local).pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="Close", width=10, command=dialog.destroy).pack(side="right")

    @staticmethod
    def _safe_filename_part(text: str) -> str:
        raw = (text or "").strip().replace(" ", "_")
        keep = []
        for ch in raw:
            if ch.isalnum() or ch in {"_", "-"}:
                keep.append(ch)
        return "".join(keep)[:40] or "session"

    def _build_chat_payload(self) -> dict[str, object]:
        return {
            "version": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "user_id": self.user_id,
            "entries": self.chat_entries,
            # Preserve planner context so loaded chats continue naturally.
            "orchestrator_history": list(self.orchestrator.history),
        }

    def _clear_transcript(self) -> None:
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")
        self.chat_entries = []

    def _render_loaded_entries(self, entries: list[dict[str, str]]) -> None:
        for entry in entries:
            speaker = str(entry.get("speaker", "Tutor"))
            tag = str(entry.get("tag", "tutor"))
            text = str(entry.get("text", ""))
            self._append_line(speaker=speaker, text=text, tag=tag, record=True)

    def _save_chat_dialog(self) -> None:
        self.chat_save_dir.mkdir(parents=True, exist_ok=True)
        default_name = (
            f"chat_{self._safe_filename_part(self.user_id)}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Chat",
            initialdir=str(self.chat_save_dir),
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not target:
            return
        try:
            payload = self._build_chat_payload()
            Path(target).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
            self._append_tutor(f"Saved chat to: {target}", play_sound=False)
        except Exception as exc:
            messagebox.showerror("Save Chat Failed", str(exc), parent=self.root)

    def _load_chat_dialog(self) -> None:
        self.chat_save_dir.mkdir(parents=True, exist_ok=True)
        source = filedialog.askopenfilename(
            parent=self.root,
            title="Load Chat",
            initialdir=str(self.chat_save_dir),
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not source:
            return
        try:
            raw = Path(source).read_text(encoding="utf-8")
            payload = json.loads(raw)
            entries = payload.get("entries", [])
            if not isinstance(entries, list):
                raise ValueError("Invalid chat file: 'entries' must be a list.")

            self._clear_transcript()
            self._render_loaded_entries(entries)

            loaded_history = payload.get("orchestrator_history", [])
            if isinstance(loaded_history, list):
                self.orchestrator.history = [
                    item
                    for item in loaded_history
                    if isinstance(item, dict) and "role" in item and "content" in item
                ]
            else:
                self.orchestrator.history = []

            self._append_tutor(f"Loaded chat from: {source}", play_sound=False)
        except Exception as exc:
            messagebox.showerror("Load Chat Failed", str(exc), parent=self.root)

    def run(self) -> None:
        self.root.mainloop()


def run_desktop_session(user_id: str, services: AppServices) -> None:
    app = AIMDesktopApp(user_id=user_id, services=services)
    app.run()
