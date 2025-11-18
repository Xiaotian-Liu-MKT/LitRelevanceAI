"""Abstract screening tab - main UI component."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import TYPE_CHECKING, Callable, Optional

import pandas as pd

from ....ai_client import AIClient
from ....abstract_screener import (
    load_mode_questions,
    load_and_validate_data,
    prepare_dataframe,
    AbstractScreener,
    ColumnNotFoundError,
    InvalidFileFormatError,
    DEFAULT_CONFIG as ABSTRACT_CONFIG,
)
from ....i18n import get_i18n, t
from .statistics_viewer import StatisticsViewer
from .question_editor import QuestionEditor

if TYPE_CHECKING:  # pragma: no cover
    from ...base_window import BaseWindow


class AbstractTab:
    """Tab for abstract screening with enhanced UI."""

    def __init__(self, app: BaseWindow) -> None:
        self.app = app
        self.frame = ttk.Frame(app.notebook)
        self.tab_index = app.notebook.index("end")
        app.notebook.add(self.frame, text=t("abstract_tab"))

        # Left panel - Controls
        left_panel = ttk.Frame(self.frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        # File selection
        self.file_label = ttk.Label(left_panel, text=t("select_file_label"))
        self.file_label.pack(anchor=tk.W, pady=2)
        file_frame = ttk.Frame(left_panel)
        file_frame.pack(fill=tk.X, pady=2)
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.browse_btn = ttk.Button(
            file_frame,
            text=t("browse"),
            command=lambda: self.app.browse_file(self.file_var, ("CSV or Excel", "*.csv *.xlsx")),
        )
        self.browse_btn.pack(side=tk.LEFT, padx=5)

        # Mode selection
        self.mode_label = ttk.Label(left_panel, text=t("screening_mode_label"))
        self.mode_label.pack(anchor=tk.W, pady=(8, 2))
        mode_frame = ttk.Frame(left_panel)
        mode_frame.pack(fill=tk.X, pady=2)
        self._load_modes()
        self.mode_var = tk.StringVar(value=self.mode_options[0] if self.mode_options else "")
        self.mode_cb = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=self.mode_options)
        self.mode_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.add_mode_btn = ttk.Button(mode_frame, text=t("add_mode"), command=self.add_mode)
        self.add_mode_btn.pack(side=tk.LEFT, padx=5)

        # Column selection (optional)
        self.col_selection_label = ttk.Label(left_panel, text=t("column_selection_optional"))
        self.col_selection_label.pack(anchor=tk.W, pady=(8, 2))
        col_frame = ttk.Frame(left_panel)
        col_frame.pack(fill=tk.X, pady=2)
        self.title_col_label = ttk.Label(col_frame, text=t("title_column"))
        self.title_col_label.pack(side=tk.LEFT)
        self.title_col_var = tk.StringVar()
        ttk.Entry(col_frame, textvariable=self.title_col_var, width=15).pack(side=tk.LEFT, padx=2)
        self.abstract_col_label = ttk.Label(col_frame, text=t("abstract_column"))
        self.abstract_col_label.pack(side=tk.LEFT, padx=(10, 0))
        self.abstract_col_var = tk.StringVar()
        ttk.Entry(col_frame, textvariable=self.abstract_col_var, width=15).pack(side=tk.LEFT, padx=2)

        # Options
        self.options_frame = ttk.LabelFrame(left_panel, text=t("processing_options"))
        self.options_frame.pack(fill=tk.X, pady=(8, 2))
        self.verify_var = tk.BooleanVar(value=True)
        self.verify_check = ttk.Checkbutton(self.options_frame, text=t("enable_verification"), variable=self.verify_var)
        self.verify_check.pack(anchor=tk.W, padx=5, pady=2)

        workers_frame = ttk.Frame(self.options_frame)
        workers_frame.pack(fill=tk.X, padx=5, pady=2)
        self.workers_label = ttk.Label(workers_frame, text=t("concurrent_workers"))
        self.workers_label.pack(side=tk.LEFT)
        self.workers_var = tk.IntVar(value=3)
        ttk.Spinbox(workers_frame, from_=1, to=10, textvariable=self.workers_var, width=10).pack(side=tk.LEFT, padx=5)

        # Action buttons
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(pady=10)
        self.start_btn = ttk.Button(btn_frame, text=t("start_screening"), command=self.start_screen)
        self.start_btn.grid(row=0, column=0, padx=2, pady=2)
        self.stop_event = threading.Event()
        self.stop_btn = ttk.Button(btn_frame, text=t("stop_task"), command=self.stop_event.set, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=2, pady=2)
        self.edit_btn = ttk.Button(btn_frame, text=t("edit_questions"), command=self.edit_questions)
        self.edit_btn.grid(row=1, column=0, padx=2, pady=2)
        self.stats_btn = ttk.Button(btn_frame, text=t("view_statistics"), command=self.show_statistics)
        self.stats_btn.grid(row=1, column=1, padx=2, pady=2)

        # Progress
        self.progress = tk.DoubleVar()
        ttk.Progressbar(left_panel, variable=self.progress, maximum=100).pack(fill=tk.X, pady=5)
        self.status = tk.StringVar()
        ttk.Label(left_panel, textvariable=self.status, wraplength=300).pack(pady=2)

        # Log
        self.log_label = ttk.Label(left_panel, text=t("log_label"))
        self.log_label.pack(anchor=tk.W, pady=(5, 2))
        log_frame = ttk.Frame(left_panel)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Export buttons
        export_frame = ttk.Frame(left_panel)
        export_frame.pack(pady=5)
        self.export_csv_btn = ttk.Button(export_frame, text=t("export_csv"), command=self.export_csv, state=tk.DISABLED)
        self.export_csv_btn.pack(side=tk.LEFT, padx=2)
        self.export_excel_btn = ttk.Button(export_frame, text=t("export_excel"), command=self.export_excel, state=tk.DISABLED)
        self.export_excel_btn.pack(side=tk.LEFT, padx=2)

        # Right panel - Results preview
        self.right_panel = ttk.LabelFrame(self.frame, text=t("results_preview"))
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview with scrollbars
        tree_frame = ttk.Frame(self.right_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        # Treeview
        self.results_tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            selectmode='browse'
        )
        v_scroll.config(command=self.results_tree.yview)
        h_scroll.config(command=self.results_tree.xview)

        # Grid layout
        self.results_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Status label for preview
        self.preview_status = tk.StringVar(value=t("no_data"))
        ttk.Label(self.right_panel, textvariable=self.preview_status).pack(pady=2)

        # Data storage
        self.df: Optional[pd.DataFrame] = None
        self.statistics: Optional[dict] = None
        self.title_col: Optional[str] = None
        self.abstract_col: Optional[str] = None

        # Register language observer
        get_i18n().add_observer(self.update_language)

    def _load_modes(self) -> None:
        """Load available screening modes from both unified and legacy configs."""
        modes = set()

        # Load from unified configs
        unified_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "configs" / "abstract"
        if unified_dir.exists():
            for yaml_file in unified_dir.glob("*.yaml"):
                modes.add(yaml_file.stem)

        # Load from legacy config
        q_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "questions_config.json"
        try:
            with q_path.open("r", encoding="utf-8") as f:
                self.modes_data = json.load(f)
                modes.update(self.modes_data.keys())
        except Exception:
            self.modes_data = {}

        self.mode_options = sorted(list(modes)) if modes else ["weekly_screening"]
        self.q_config_path = q_path

    # ------------------------------------------------------------------
    # Screening
    # ------------------------------------------------------------------
    def start_screen(self) -> None:
        """Start the screening process."""
        path = self.file_var.get()
        if not path:
            messagebox.showerror(t("error"), t("error_select_file"))
            return
        mode = self.mode_var.get()
        self.export_csv_btn.config(state=tk.DISABLED)
        self.export_excel_btn.config(state=tk.DISABLED)
        self.stop_event.clear()
        self.stop_btn.config(state=tk.NORMAL)
        self._clear_log()
        threading.Thread(target=self.process_abstract, args=(path, mode), daemon=True).start()

    def process_abstract(self, path: str, mode: str) -> None:
        """Process abstracts using concurrent screening."""
        config = ABSTRACT_CONFIG.copy()
        config.update(self.app.build_config())
        config["INPUT_FILE_PATH"] = path
        config["CONFIG_MODE"] = mode
        config["ENABLE_VERIFICATION"] = self.verify_var.get()
        config["MAX_WORKERS"] = self.workers_var.get()

        try:
            # Load questions
            q = load_mode_questions(mode)
            open_q = q.get("open_questions", [])
            yes_no_q = q.get("yes_no_questions", [])

            # Apply settings from mode config if available
            mode_settings = q.get("settings", {})
            if mode_settings:
                # Normalize lowercase keys to uppercase for consistency
                normalized_settings = {
                    "MAX_WORKERS": mode_settings.get("max_workers"),
                    "API_REQUEST_DELAY": mode_settings.get("api_request_delay"),
                    "ENABLE_VERIFICATION": mode_settings.get("enable_verification"),
                }
                # Only update config with non-None values
                config.update({k: v for k, v in normalized_settings.items() if v is not None})

            # Get column names
            title_col = self.title_col_var.get().strip() or None
            abstract_col = self.abstract_col_var.get().strip() or None

            # Load and validate data
            try:
                df, title_col, abstract_col = load_and_validate_data(
                    path, config, title_col, abstract_col
                )
            except ColumnNotFoundError as e:
                # Show column selection dialog
                self._schedule(lambda: self._show_column_selector_error(str(e), path, config))
                return
            except (InvalidFileFormatError, IOError) as e:
                self._schedule(self._log, f"{t('error')}: {e}")
                self._schedule(lambda: messagebox.showerror(t("error"), str(e)))
                return

            # Store column names
            self.title_col = title_col
            self.abstract_col = abstract_col

            # Prepare dataframe
            df = prepare_dataframe(df, open_q, yes_no_q)
            self.df = df

            # Log start
            self._schedule(self._log, t("processing_articles", count=len(df)))
            verification_text = t("yes") if config['ENABLE_VERIFICATION'] else t("no")
            self._schedule(self._log, t("concurrent_verification", workers=config['MAX_WORKERS'], verification=verification_text))

            # Create screener
            client = AIClient(config)
            screener = AbstractScreener(config, client)

            # Process concurrently with progress callback
            completed_count = [0]  # Use list to allow modification in closure

            def progress_callback(index, total, result):
                completed_count[0] += 1
                self._schedule(self.status.set, t("completed_status", completed=completed_count[0], total=total))
                self._schedule(self.progress.set, (completed_count[0] / total) * 100)

                # Update log
                if result:
                    self._schedule(self._log_article_result, index, result, open_q, yes_no_q, config)

                # Update preview periodically (every 5 articles)
                if completed_count[0] % 5 == 0:
                    self._schedule(self.update_results_preview)

            # Run concurrent processing
            screener.analyze_batch_concurrent(
                df, title_col, abstract_col, open_q, yes_no_q,
                progress_callback=progress_callback,
                stop_event=self.stop_event
            )

            if self.stop_event.is_set():
                self._schedule(self._log, t("task_stopped"))
            else:
                # Save results
                base, ext = os.path.splitext(path)
                output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
                if output_file_path.endswith('.csv'):
                    df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
                else:
                    df.to_excel(output_file_path, index=False, engine='openpyxl')

                # Generate statistics
                self.statistics = screener.generate_statistics(df, open_q, yes_no_q)

                self._schedule(self._log, t("complete_saved", path=output_file_path))
                self._schedule(self._log, t("total_count", count=self.statistics['total_articles']))
                self._schedule(self.update_results_preview)

        except Exception as e:
            import traceback
            self._schedule(self._log, f"{t('error')}: {e}")
            self._schedule(self._log, traceback.format_exc())
            self._schedule(lambda: messagebox.showerror(t("error"), str(e)))
        finally:
            self._schedule(self.status.set, "")
            self._schedule(self.progress.set, 0)
            self._schedule(lambda: self.stop_btn.config(state=tk.DISABLED))
            self._schedule(lambda: self.enable_exports(self.df is not None))

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _show_column_selector_error(self, error_msg: str, path: str, config: dict) -> None:
        """Show column selection dialog when auto-detection fails."""
        # Show error message first
        msg = f"{error_msg}\n\n{t('manual_select_columns')}"
        if not messagebox.askyesno(t("column_recognition_failed"), msg):
            return

        # Load file to get available columns
        try:
            if path.endswith('.csv'):
                df = pd.read_csv(path, encoding='utf-8-sig')
            else:
                df = pd.read_excel(path)
        except Exception as e:
            messagebox.showerror(t("error"), t("cannot_read_file", error=e))
            return

        columns = list(df.columns)

        # Show selection dialog
        dialog = tk.Toplevel(self.app.root)
        dialog.title(t("select_column"))
        dialog.geometry("400x200")
        dialog.transient(self.app.root)
        dialog.grab_set()

        ttk.Label(dialog, text=t("please_select_columns")).pack(pady=10)

        # Title column
        title_frame = ttk.Frame(dialog)
        title_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(title_frame, text=t("title_column")).pack(side=tk.LEFT)
        title_var = tk.StringVar()
        title_combo = ttk.Combobox(title_frame, textvariable=title_var, values=columns)
        title_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Abstract column
        abstract_frame = ttk.Frame(dialog)
        abstract_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(abstract_frame, text=t("abstract_column")).pack(side=tk.LEFT)
        abstract_var = tk.StringVar()
        abstract_combo = ttk.Combobox(abstract_frame, textvariable=abstract_var, values=columns)
        abstract_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Buttons
        def on_ok():
            self.title_col_var.set(title_var.get())
            self.abstract_col_var.set(abstract_var.get())
            dialog.destroy()
            # Restart screening with selected columns
            self.start_screen()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=t("ok"), command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=t("cancel"), command=on_cancel).pack(side=tk.LEFT, padx=5)

    def _log_article_result(self, index: int, result: dict, open_q: list, yes_no_q: list, config: dict) -> None:
        """Log the result of a single article analysis."""
        initial = result.get("initial", {})
        verification = result.get("verification", {})
        qa = initial.get("quick_analysis", {})
        sr = initial.get("screening_results", {})
        vqa = verification.get("quick_analysis", {})
        vsr = verification.get("screening_results", {})

        summary_parts = []
        for q in open_q:
            key = q["key"]
            ans = qa.get(key, "")
            mark = ""
            if config.get("ENABLE_VERIFICATION", True):
                ver = vqa.get(key, "")
                mark = "✔" if ver == "是" else "✖" if ver == "否" else "?" if ver else ""
            summary_parts.append(f"{key}:{ans[:20]}...{(' ' + mark) if mark else ''}")

        for q in yes_no_q:
            key = q["key"]
            ans = sr.get(key, "")
            mark = ""
            if config.get("ENABLE_VERIFICATION", True):
                ver = vsr.get(key, "")
                mark = "✔" if ver == "是" else "✖" if ver == "否" else "?" if ver else ""
            summary_parts.append(f"{key}:{ans}{(' ' + mark) if mark else ''}")

        self._log(t("entry_log", index=index + 1, summary='; '.join(summary_parts)))

    def update_results_preview(self) -> None:
        """Update the Treeview with current results."""
        if self.df is None or len(self.df) == 0:
            self.preview_status.set(t("no_data"))
            return

        # Clear existing data
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Get columns to display (limit to first 10 columns for readability)
        display_cols = list(self.df.columns[:10])
        self.results_tree["columns"] = display_cols
        self.results_tree["show"] = "headings"

        # Configure column headings
        for col in display_cols:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=120, anchor=tk.W)

        # Insert data (show first 100 rows)
        for index, row in self.df.head(100).iterrows():
            values = [str(row[col])[:50] if pd.notna(row[col]) else "" for col in display_cols]
            self.results_tree.insert("", tk.END, values=values)

        # Update status
        total_rows = len(self.df)
        displayed_rows = min(100, total_rows)
        self.preview_status.set(t("display_rows_cols", displayed=displayed_rows, total=total_rows,
                                   display_cols=len(display_cols), total_cols=len(self.df.columns)))

    def show_statistics(self) -> None:
        """Show statistics dialog using StatisticsViewer."""
        viewer = StatisticsViewer(self.app, self.statistics)
        viewer.show()

    def _log(self, msg: str) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _schedule(self, callback: Callable, *args) -> None:
        """Safely schedule a Tk update from worker threads."""

        root = getattr(self.app, "root", None)
        if root is None:
            return
        try:
            root.after(0, callback, *args)
        except (RuntimeError, tk.TclError):  # pragma: no cover - GUI lifecycle
            pass

    def enable_exports(self, enable: bool) -> None:
        state = tk.NORMAL if enable else tk.DISABLED
        self.export_csv_btn.config(state=state)
        self.export_excel_btn.config(state=state)

    def export_csv(self) -> None:
        if self.df is None:
            messagebox.showerror(t("error"), t("error_no_results"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[(t("csv_files"), "*.csv")])
        if path:
            self.df.to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo(t("success"), t("csv_exported"))

    def export_excel(self) -> None:
        if self.df is None:
            messagebox.showerror(t("error"), t("error_no_results"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
        if path:
            self.df.to_excel(path, index=False, engine="openpyxl")
            messagebox.showinfo(t("success"), t("excel_exported"))

    def add_mode(self) -> None:
        name = simpledialog.askstring(t("new_mode"), t("enter_mode_name"), parent=self.app.root)
        if not name:
            return
        if name in self.modes_data:
            messagebox.showerror(t("error"), t("mode_exists"))
            return
        desc = simpledialog.askstring(t("description"), t("enter_description"), parent=self.app.root) or ""
        self.modes_data[name] = {"description": desc, "open_questions": [], "yes_no_questions": []}
        with self.q_config_path.open("w", encoding="utf-8") as f:
            json.dump(self.modes_data, f, ensure_ascii=False, indent=2)
        self.mode_cb.configure(values=list(self.modes_data.keys()))
        self.mode_var.set(name)

    def edit_questions(self) -> None:
        """Show question editor dialog using QuestionEditor."""
        def on_save(updated_data: dict, mode: str) -> None:
            """Callback to update UI after saving questions."""
            self.modes_data = updated_data
            self.mode_cb.configure(values=list(self.modes_data.keys()))
            self.mode_var.set(mode)

        editor = QuestionEditor(
            self.app,
            self.mode_var.get(),
            self.q_config_path,
            self.modes_data,
            on_save_callback=on_save
        )
        editor.show()

    def update_language(self) -> None:
        """Update all UI text when language changes."""
        # Update tab title
        self.app.notebook.tab(self.tab_index, text=t("abstract_tab"))

        # Update labels
        self.file_label.config(text=t("select_file_label"))
        self.mode_label.config(text=t("screening_mode_label"))
        self.col_selection_label.config(text=t("column_selection_optional"))
        self.title_col_label.config(text=t("title_column"))
        self.abstract_col_label.config(text=t("abstract_column"))
        self.options_frame.config(text=t("processing_options"))
        self.verify_check.config(text=t("enable_verification"))
        self.workers_label.config(text=t("concurrent_workers"))
        self.log_label.config(text=t("log_label"))
        self.right_panel.config(text=t("results_preview"))

        # Update buttons
        self.browse_btn.config(text=t("browse"))
        self.add_mode_btn.config(text=t("add_mode"))
        self.start_btn.config(text=t("start_screening"))
        self.stop_btn.config(text=t("stop_task"))
        self.edit_btn.config(text=t("edit_questions"))
        self.stats_btn.config(text=t("view_statistics"))
        self.export_csv_btn.config(text=t("export_csv"))
        self.export_excel_btn.config(text=t("export_excel"))

        # Update preview status if no data
        if self.df is None or len(self.df) == 0:
            self.preview_status.set(t("no_data"))
