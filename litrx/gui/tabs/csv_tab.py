from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from typing import TYPE_CHECKING, Optional

import pandas as pd

from ...csv_analyzer import LiteratureAnalyzer
from ...i18n import t, get_i18n

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from ..base_window import BaseWindow


class CsvTab:
    """Tab for CSV relevance analysis."""

    def __init__(self, app: BaseWindow) -> None:
        self.app = app
        self.frame = ttk.Frame(app.notebook)
        app.notebook.add(self.frame, text=t("csv_tab"))

        # Store widget references for i18n updates
        self.topic_label = ttk.Label(self.frame, text=t("research_topic_label"))
        self.topic_label.pack(anchor=tk.W, padx=5, pady=2)
        self.topic_var = tk.StringVar()
        ttk.Entry(self.frame, textvariable=self.topic_var, width=40).pack(fill=tk.X, padx=5)

        self.file_label = ttk.Label(self.frame, text=t("select_csv_file"))
        self.file_label.pack(anchor=tk.W, padx=5, pady=(8, 2))
        file_frame = ttk.Frame(self.frame)
        file_frame.pack(fill=tk.X, padx=5)
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.browse_btn = ttk.Button(
            file_frame,
            text=t("browse"),
            command=self._browse_file,
        )
        self.browse_btn.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(self.frame, text=t("start_analysis"), command=self.start_analysis)
        self.start_btn.pack(pady=5)

        self.progress = tk.DoubleVar()
        ttk.Progressbar(self.frame, variable=self.progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)

        table_frame = ttk.Frame(self.frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        columns = ("title", "score", "analysis")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("title", text=t("table_title"))
        self.tree.heading("score", text=t("table_score"))
        self.tree.heading("analysis", text=t("table_analysis"))
        self.tree.column("title", width=200)
        self.tree.column("score", width=80, anchor=tk.CENTER)
        self.tree.column("analysis", width=300)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", self.show_full_analysis)

        self.export_btn = ttk.Button(self.frame, text=t("export_results"), command=self.export_results, state=tk.DISABLED)
        self.export_btn.pack(pady=(0, 5))

        self.df: Optional[pd.DataFrame] = None
        self.analyzer: Optional[LiteratureAnalyzer] = None

        # Register for language change notifications
        get_i18n().add_observer(self.update_language)

    # ------------------------------------------------------------------
    # Language Support
    # ------------------------------------------------------------------
    def update_language(self) -> None:
        """Update UI text when language changes."""
        # Update tab text in notebook
        tab_id = self.app.notebook.index(self.frame)
        self.app.notebook.tab(tab_id, text=t("csv_tab"))

        # Update labels
        self.topic_label.config(text=t("research_topic_label"))
        self.file_label.config(text=t("select_csv_file"))

        # Update buttons
        self.browse_btn.config(text=t("browse"))
        self.start_btn.config(text=t("start_analysis"))
        self.export_btn.config(text=t("export_results"))

        # Update tree headings
        self.tree.heading("title", text=t("table_title"))
        self.tree.heading("score", text=t("table_score"))
        self.tree.heading("analysis", text=t("table_analysis"))

    def _browse_file(self) -> None:
        """Browse for CSV file."""
        self.app.browse_file(self.file_var, (t("csv_files"), "*.csv"))

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def start_analysis(self) -> None:
        path = self.file_var.get()
        topic = self.topic_var.get()
        if not path or not topic:
            messagebox.showerror(t("error"), t("error_fill_fields"))
            return
        self.export_btn.config(state=tk.DISABLED)
        self.progress.set(0)
        self.df = None
        self.analyzer = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        threading.Thread(target=self.process_csv, args=(path, topic), daemon=True).start()

    def process_csv(self, path: str, topic: str) -> None:
        """Process CSV file with thread-safe DataFrame updates.

        This method runs in a worker thread. All DataFrame modifications
        are applied through root.after() to ensure thread safety.
        """
        config = self.app.build_config()
        analyzer = LiteratureAnalyzer(config, topic)
        try:
            df = analyzer.read_scopus_csv(path)
        except Exception as e:  # pragma: no cover - UI feedback
            self.app.root.after(0, lambda: messagebox.showerror(t("error"), t("error_read_file", error=str(e))))
            return

        self.df = df
        self.analyzer = analyzer
        total = len(df)

        # Define progress callback for thread-safe updates
        def progress_callback(idx, total_papers, result):
            """Called from worker thread - schedules UI updates on main thread."""
            if result is None:
                # Paper skipped due to missing data
                return

            # Apply result to DataFrame in main thread (thread-safe)
            def apply_update():
                analyzer.apply_result_to_dataframe(df, idx, result)
                summary = result['analysis'].replace('\n', ' ')[:80]
                self.update_row(idx, result['title'], result['relevance_score'], summary)

            self.app.root.after(0, apply_update)

        # Process all papers
        for i, (idx, row) in enumerate(df.iterrows(), start=1):
            try:
                res = analyzer.analyze_paper(row['Title'], row['Abstract'])
                res['title'] = row['Title']
                res['index'] = idx

                # Schedule DataFrame update and UI update on main thread
                progress_callback(idx, total, res)

            except Exception as e:  # pragma: no cover - UI feedback
                error_msg = t("error_analysis", error=str(e))
                self.app.root.after(0, self.update_row, idx, row['Title'], '', error_msg)

            # Update progress bar
            self.app.root.after(0, lambda v=i / total * 100: self.progress.set(v))

        # Enable export button when done
        self.app.root.after(0, lambda: self.export_btn.config(state=tk.NORMAL))

    def update_row(self, idx: int, title: str, score: float | str, analysis: str) -> None:
        iid = str(idx)
        values = (title, score, analysis)
        if self.tree.exists(iid):
            self.tree.item(iid, values=values)
        else:
            self.tree.insert('', 'end', iid=iid, values=values)

    def show_full_analysis(self, event: tk.Event) -> None:
        item = self.tree.focus()
        if not item or self.df is None:
            return
        idx = int(item)
        analysis = self.df.at[idx, 'Analysis Result']
        if analysis is None:
            return
        title = self.df.at[idx, 'Title']
        win = tk.Toplevel(self.app.root)
        win.title(title)
        text = ScrolledText(win, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, analysis)
        text.config(state=tk.DISABLED)

    def export_results(self) -> None:
        if self.df is None or self.analyzer is None:
            messagebox.showerror(t("error"), t("error_no_results"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[(t("csv_files"), "*.csv")])
        if path:
            self.analyzer.save_results(self.df, path)
            messagebox.showinfo(t("success"), t("results_exported"))
