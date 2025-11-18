"""Question editor dialog for abstract screening modes."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING, Callable, Optional

from ....i18n import t

if TYPE_CHECKING:  # pragma: no cover
    from ...base_window import BaseWindow


class QuestionEditor:
    """Dialog for editing screening mode questions."""

    def __init__(
        self,
        parent: BaseWindow,
        mode: str,
        q_config_path: Path,
        modes_data: dict,
        on_save_callback: Optional[Callable[[dict, str], None]] = None
    ):
        """
        Initialize the question editor.

        Args:
            parent: Parent BaseWindow instance
            mode: Current screening mode name
            q_config_path: Path to questions_config.json
            modes_data: Current modes configuration data
            on_save_callback: Callback function to execute after successful save
        """
        self.parent = parent
        self.mode = mode
        self.q_config_path = q_config_path
        self.modes_data = modes_data
        self.on_save_callback = on_save_callback

    def show(self) -> None:
        """Show question editor dialog."""
        try:
            with self.q_config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        mode_data = data.get(
            self.mode,
            {"description": "", "open_questions": [], "yes_no_questions": []}
        )
        open_q = mode_data.get("open_questions", [])
        yes_no_q = mode_data.get("yes_no_questions", [])

        win = tk.Toplevel(self.parent.root)
        win.title(t("edit_questions"))
        win.geometry("640x420")
        win.transient(self.parent.root)
        win.grab_set()

        content = ttk.Frame(win)
        content.pack(fill=tk.BOTH, expand=True)

        # Create sections for open and yes/no questions
        self._make_section(content, t("open_questions"), open_q, win)
        self._make_section(content, t("yes_no_questions"), yes_no_q, win)

        # Save and cancel buttons
        def close_window() -> None:
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        def save():
            if not self.mode:
                messagebox.showerror(t("error"), t("please_select_mode"), parent=win)
                return

            updated_mode = dict(mode_data)
            updated_mode["open_questions"] = deepcopy(open_q)
            updated_mode["yes_no_questions"] = deepcopy(yes_no_q)

            data[self.mode] = updated_mode
            try:
                with self.q_config_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except OSError as exc:
                messagebox.showerror(t("error"), t("save_question_config_failed", error=exc), parent=win)
                return

            messagebox.showinfo(t("success"), t("question_config_saved"), parent=win)

            # Execute callback if provided
            if self.on_save_callback:
                self.on_save_callback(data, self.mode)

            close_window()

        action_frame = ttk.Frame(win)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(action_frame, text=t("cancel"), command=close_window).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text=t("save"), command=save).pack(side=tk.RIGHT, padx=5)
        win.protocol("WM_DELETE_WINDOW", close_window)

    def _make_section(self, parent: ttk.Frame, title: str, items: list, win: tk.Toplevel) -> ttk.LabelFrame:
        """
        Create a section for editing a list of questions.

        Args:
            parent: Parent frame
            title: Section title
            items: List of question dictionaries
            win: Parent window for dialogs

        Returns:
            Created LabelFrame
        """
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        lb = tk.Listbox(frame)
        lb.pack(fill=tk.BOTH, expand=True)
        for q in items:
            lb.insert(tk.END, q["question"])

        def add_item():
            new_item = self._prompt_question(win)
            if not new_item:
                return
            items.append(new_item)
            lb.insert(tk.END, new_item["question"])

        def edit_item():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning(t("hint"), t("please_select_question"))
                return
            idx = sel[0]
            item = items[idx]
            updated_item = self._prompt_question(win, item)
            if not updated_item:
                return
            # 保留原有字典对象，避免其他引用失效
            item.clear()
            item.update(updated_item)
            lb.delete(idx)
            lb.insert(idx, updated_item["question"])
            lb.selection_set(idx)

        def del_item():
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                lb.delete(idx)
                items.pop(idx)

        btn_f = ttk.Frame(frame)
        btn_f.pack(pady=5)
        ttk.Button(btn_f, text=t("add"), command=add_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text=t("edit"), command=edit_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text=t("delete"), command=del_item).pack(side=tk.LEFT, padx=5)
        lb.bind("<Double-Button-1>", lambda _event: edit_item())
        return frame

    def _prompt_question(
        self,
        parent: tk.Toplevel,
        initial: Optional[dict[str, str]] = None
    ) -> Optional[dict[str, str]]:
        """
        Show dialog to create or edit a question.

        Args:
            parent: Parent window
            initial: Initial question data for editing

        Returns:
            Question dictionary with keys: key, column_name, question
            Returns None if cancelled
        """
        dialog = tk.Toplevel(parent)
        dialog.title(t("setup_question"))
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(True, True)
        dialog.geometry("400x320")

        ttk.Label(dialog, text="Key:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=(10, 5))
        key_var = tk.StringVar(value=(initial or {}).get("key", ""))
        key_entry = ttk.Entry(dialog, textvariable=key_var)
        key_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 10), pady=(10, 5))

        ttk.Label(dialog, text="Column Name:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        column_var = tk.StringVar(value=(initial or {}).get("column_name", ""))
        column_entry = ttk.Entry(dialog, textvariable=column_var)
        column_entry.grid(row=1, column=1, sticky=tk.EW, padx=(0, 10), pady=5)

        ttk.Label(dialog, text="Question:").grid(row=2, column=0, sticky=tk.NW, padx=10, pady=5)
        question_text = tk.Text(dialog, wrap=tk.WORD)
        question_text.grid(row=2, column=1, sticky=tk.NSEW, padx=(0, 10), pady=5)
        question_text.insert("1.0", (initial or {}).get("question", ""))

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        result: Optional[dict[str, str]] = None

        def on_save() -> None:
            nonlocal result
            key = key_var.get().strip()
            column_name = column_var.get().strip()
            question = question_text.get("1.0", tk.END).strip()
            if not key:
                messagebox.showerror(t("error"), t("key_cannot_empty"), parent=dialog)
                return
            if not question:
                messagebox.showerror(t("error"), t("question_cannot_empty"), parent=dialog)
                return
            if not column_name:
                messagebox.showerror(t("error"), t("column_name_cannot_empty"), parent=dialog)
                return
            result = {"key": key, "question": question, "column_name": column_name}
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        ttk.Button(button_frame, text=t("save"), command=on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=t("cancel"), command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.columnconfigure(1, weight=1)
        dialog.rowconfigure(2, weight=1)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        key_entry.focus_set()
        parent.wait_window(dialog)
        return result
