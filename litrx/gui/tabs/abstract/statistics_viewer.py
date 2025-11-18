"""Statistics viewer dialog for abstract screening results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ....tk_compat import ensure_native_macos_version

ensure_native_macos_version()

import tkinter as tk
from tkinter import messagebox, ttk

from ....i18n import t

if TYPE_CHECKING:  # pragma: no cover
    from ...base_window import BaseWindow


class StatisticsViewer:
    """Dialog for viewing abstract screening statistics."""

    def __init__(self, parent: BaseWindow, statistics: Optional[dict] = None):
        """
        Initialize the statistics viewer.

        Args:
            parent: Parent BaseWindow instance
            statistics: Statistics dictionary from AbstractScreener
        """
        self.parent = parent
        self.statistics = statistics

    def show(self) -> None:
        """Show statistics dialog."""
        if self.statistics is None:
            messagebox.showinfo(t("hint"), t("please_complete_screening"))
            return

        # Create statistics window
        win = tk.Toplevel(self.parent.root)
        win.title(t("screening_statistics"))
        win.geometry("600x500")
        win.transient(self.parent.root)

        # Header
        header = ttk.Frame(win)
        header.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(
            header,
            text=t("statistics_summary", count=self.statistics['total_articles']),
            font=("", 12, "bold")
        ).pack()

        # Notebook for different categories
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Yes/No Questions Tab
        self._create_yes_no_tab(notebook)

        # Open Questions Tab
        self._create_open_questions_tab(notebook)

        # Close button
        ttk.Button(win, text=t("close"), command=win.destroy).pack(pady=10)

    def _create_yes_no_tab(self, notebook: ttk.Notebook) -> None:
        """Create tab for yes/no questions statistics."""
        yn_frame = ttk.Frame(notebook)
        notebook.add(yn_frame, text=t("yes_no_questions_stats"))

        yn_text = tk.Text(yn_frame, wrap=tk.WORD, state=tk.DISABLED)
        yn_scroll = ttk.Scrollbar(yn_frame, orient=tk.VERTICAL, command=yn_text.yview)
        yn_text.configure(yscrollcommand=yn_scroll.set)
        yn_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yn_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        yn_text.config(state=tk.NORMAL)
        for question, stats in self.statistics.get('yes_no_results', {}).items():
            yn_text.insert(tk.END, f"\n{'='*60}\n")
            yn_text.insert(tk.END, f"问题: {question}\n")
            yn_text.insert(tk.END, f"{'-'*60}\n")
            yn_text.insert(tk.END, f"  是: {stats.get('是', 0)} 篇\n")
            yn_text.insert(tk.END, f"  否: {stats.get('否', 0)} 篇\n")
            yn_text.insert(tk.END, f"  不确定: {stats.get('不确定', 0)} 篇\n")
            yn_text.insert(tk.END, f"  其他: {stats.get('其他', 0)} 篇\n")

            if 'verification' in stats:
                yn_text.insert(tk.END, f"\n验证结果:\n")
                ver = stats['verification']
                yn_text.insert(tk.END, f"  已验证: {ver.get('已验证', 0)} 篇\n")
                yn_text.insert(tk.END, f"  未验证: {ver.get('未验证', 0)} 篇\n")
                yn_text.insert(tk.END, f"  不确定: {ver.get('不确定', 0)} 篇\n")
        yn_text.config(state=tk.DISABLED)

    def _create_open_questions_tab(self, notebook: ttk.Notebook) -> None:
        """Create tab for open questions statistics."""
        oq_frame = ttk.Frame(notebook)
        notebook.add(oq_frame, text=t("open_questions_stats"))

        oq_text = tk.Text(oq_frame, wrap=tk.WORD, state=tk.DISABLED)
        oq_scroll = ttk.Scrollbar(oq_frame, orient=tk.VERTICAL, command=oq_text.yview)
        oq_text.configure(yscrollcommand=oq_scroll.set)
        oq_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        oq_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        oq_text.config(state=tk.NORMAL)
        for question, stats in self.statistics.get('open_question_stats', {}).items():
            oq_text.insert(tk.END, f"\n{'='*60}\n")
            oq_text.insert(tk.END, f"{t('question')}: {question}\n")
            oq_text.insert(tk.END, f"{'-'*60}\n")
            oq_text.insert(tk.END, f"  已回答: {stats.get('answered', 0)} 篇\n")
            oq_text.insert(tk.END, f"  未回答: {stats.get('missing', 0)} 篇\n")
        oq_text.config(state=tk.DISABLED)
