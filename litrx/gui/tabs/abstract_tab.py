from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import TYPE_CHECKING, Callable, Optional

import pandas as pd

from ...ai_client import AIClient
from ...abstract_screener import (
    load_mode_questions,
    load_and_validate_data,
    prepare_dataframe,
    AbstractScreener,
    ColumnNotFoundError,
    InvalidFileFormatError,
    DEFAULT_CONFIG as ABSTRACT_CONFIG,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..base_window import BaseWindow


class AbstractTab:
    """Tab for abstract screening with enhanced UI."""

    def __init__(self, app: BaseWindow) -> None:
        self.app = app
        frame = ttk.Frame(app.notebook)
        app.notebook.add(frame, text="摘要筛选")

        # Left panel - Controls
        left_panel = ttk.Frame(frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        # File selection
        ttk.Label(left_panel, text="选择CSV/XLSX文件:").pack(anchor=tk.W, pady=2)
        file_frame = ttk.Frame(left_panel)
        file_frame.pack(fill=tk.X, pady=2)
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            file_frame,
            text="浏览",
            command=lambda: self.app.browse_file(self.file_var, ("CSV or Excel", "*.csv *.xlsx")),
        ).pack(side=tk.LEFT, padx=5)

        # Mode selection
        ttk.Label(left_panel, text="筛选模式:").pack(anchor=tk.W, pady=(8, 2))
        mode_frame = ttk.Frame(left_panel)
        mode_frame.pack(fill=tk.X, pady=2)
        self._load_modes()
        self.mode_var = tk.StringVar(value=self.mode_options[0] if self.mode_options else "")
        self.mode_cb = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=self.mode_options)
        self.mode_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(mode_frame, text="添加模式", command=self.add_mode).pack(side=tk.LEFT, padx=5)

        # Column selection (optional)
        ttk.Label(left_panel, text="列名选择(可选):").pack(anchor=tk.W, pady=(8, 2))
        col_frame = ttk.Frame(left_panel)
        col_frame.pack(fill=tk.X, pady=2)
        ttk.Label(col_frame, text="标题列:").pack(side=tk.LEFT)
        self.title_col_var = tk.StringVar()
        ttk.Entry(col_frame, textvariable=self.title_col_var, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Label(col_frame, text="摘要列:").pack(side=tk.LEFT, padx=(10, 0))
        self.abstract_col_var = tk.StringVar()
        ttk.Entry(col_frame, textvariable=self.abstract_col_var, width=15).pack(side=tk.LEFT, padx=2)

        # Options
        options_frame = ttk.LabelFrame(left_panel, text="处理选项")
        options_frame.pack(fill=tk.X, pady=(8, 2))
        self.verify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="启用验证", variable=self.verify_var).pack(anchor=tk.W, padx=5, pady=2)

        workers_frame = ttk.Frame(options_frame)
        workers_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(workers_frame, text="并发数:").pack(side=tk.LEFT)
        self.workers_var = tk.IntVar(value=3)
        ttk.Spinbox(workers_frame, from_=1, to=10, textvariable=self.workers_var, width=10).pack(side=tk.LEFT, padx=5)

        # Action buttons
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="开始筛选", command=self.start_screen).grid(row=0, column=0, padx=2, pady=2)
        self.stop_event = threading.Event()
        self.stop_btn = ttk.Button(btn_frame, text="中止任务", command=self.stop_event.set, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(btn_frame, text="编辑问题", command=self.edit_questions).grid(row=1, column=0, padx=2, pady=2)
        ttk.Button(btn_frame, text="查看统计", command=self.show_statistics).grid(row=1, column=1, padx=2, pady=2)

        # Progress
        self.progress = tk.DoubleVar()
        ttk.Progressbar(left_panel, variable=self.progress, maximum=100).pack(fill=tk.X, pady=5)
        self.status = tk.StringVar()
        ttk.Label(left_panel, textvariable=self.status, wraplength=300).pack(pady=2)

        # Log
        ttk.Label(left_panel, text="日志:").pack(anchor=tk.W, pady=(5, 2))
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
        self.export_csv_btn = ttk.Button(export_frame, text="导出 CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_csv_btn.pack(side=tk.LEFT, padx=2)
        self.export_excel_btn = ttk.Button(export_frame, text="导出 Excel", command=self.export_excel, state=tk.DISABLED)
        self.export_excel_btn.pack(side=tk.LEFT, padx=2)

        # Right panel - Results preview
        right_panel = ttk.LabelFrame(frame, text="结果预览")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview with scrollbars
        tree_frame = ttk.Frame(right_panel)
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
        self.preview_status = tk.StringVar(value="暂无数据")
        ttk.Label(right_panel, textvariable=self.preview_status).pack(pady=2)

        # Data storage
        self.df: Optional[pd.DataFrame] = None
        self.statistics: Optional[dict] = None
        self.title_col: Optional[str] = None
        self.abstract_col: Optional[str] = None

    def _load_modes(self) -> None:
        """Load available screening modes from both unified and legacy configs."""
        modes = set()

        # Load from unified configs
        unified_dir = Path(__file__).resolve().parent.parent.parent.parent / "configs" / "abstract"
        if unified_dir.exists():
            for yaml_file in unified_dir.glob("*.yaml"):
                modes.add(yaml_file.stem)

        # Load from legacy config
        q_path = Path(__file__).resolve().parent.parent.parent.parent / "questions_config.json"
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
            messagebox.showerror("错误", "请先选择文件")
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
                config.update(mode_settings)

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
                self._schedule(self._log, f"错误: {e}")
                self._schedule(lambda: messagebox.showerror("错误", str(e)))
                return

            # Store column names
            self.title_col = title_col
            self.abstract_col = abstract_col

            # Prepare dataframe
            df = prepare_dataframe(df, open_q, yes_no_q)
            self.df = df

            # Log start
            self._schedule(self._log, f"开始处理 {len(df)} 篇文献...")
            self._schedule(self._log, f"并发数: {config['MAX_WORKERS']}, 验证: {'是' if config['ENABLE_VERIFICATION'] else '否'}")

            # Create screener
            client = AIClient(config)
            screener = AbstractScreener(config, client)

            # Process concurrently with progress callback
            completed_count = [0]  # Use list to allow modification in closure

            def progress_callback(index, total, result):
                completed_count[0] += 1
                self._schedule(self.status.set, f"已完成: {completed_count[0]}/{total}")
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
                self._schedule(self._log, "任务已中止")
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

                self._schedule(self._log, f"完成! 结果已保存到: {output_file_path}")
                self._schedule(self._log, f"总计: {self.statistics['total_articles']} 篇")
                self._schedule(self.update_results_preview)

        except Exception as e:
            import traceback
            self._schedule(self._log, f"错误: {e}")
            self._schedule(self._log, traceback.format_exc())
            self._schedule(lambda: messagebox.showerror("错误", str(e)))
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
        msg = f"{error_msg}\n\n是否手动选择列?"
        if not messagebox.askyesno("列识别失败", msg):
            return

        # Load file to get available columns
        try:
            if path.endswith('.csv'):
                df = pd.read_csv(path, encoding='utf-8-sig')
            else:
                df = pd.read_excel(path)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取文件: {e}")
            return

        columns = list(df.columns)

        # Show selection dialog
        dialog = tk.Toplevel(self.app.root)
        dialog.title("选择列")
        dialog.geometry("400x200")
        dialog.transient(self.app.root)
        dialog.grab_set()

        ttk.Label(dialog, text="请选择标题列和摘要列:").pack(pady=10)

        # Title column
        title_frame = ttk.Frame(dialog)
        title_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(title_frame, text="标题列:").pack(side=tk.LEFT)
        title_var = tk.StringVar()
        title_combo = ttk.Combobox(title_frame, textvariable=title_var, values=columns)
        title_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Abstract column
        abstract_frame = ttk.Frame(dialog)
        abstract_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(abstract_frame, text="摘要列:").pack(side=tk.LEFT)
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
        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)

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

        self._log(f"条目 {index + 1}: {'; '.join(summary_parts)}")

    def update_results_preview(self) -> None:
        """Update the Treeview with current results."""
        if self.df is None or len(self.df) == 0:
            self.preview_status.set("暂无数据")
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
        self.preview_status.set(f"显示 {displayed_rows}/{total_rows} 行, {len(display_cols)}/{len(self.df.columns)} 列")

    def show_statistics(self) -> None:
        """Show statistics dialog."""
        if self.statistics is None:
            messagebox.showinfo("提示", "请先完成筛选任务")
            return

        # Create statistics window
        win = tk.Toplevel(self.app.root)
        win.title("筛选统计")
        win.geometry("600x500")
        win.transient(self.app.root)

        # Header
        header = ttk.Frame(win)
        header.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(
            header,
            text=f"筛选统计摘要 - 共 {self.statistics['total_articles']} 篇文献",
            font=("", 12, "bold")
        ).pack()

        # Notebook for different categories
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Yes/No Questions Tab
        yn_frame = ttk.Frame(notebook)
        notebook.add(yn_frame, text="是/否问题统计")

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

        # Open Questions Tab
        oq_frame = ttk.Frame(notebook)
        notebook.add(oq_frame, text="开放问题统计")

        oq_text = tk.Text(oq_frame, wrap=tk.WORD, state=tk.DISABLED)
        oq_scroll = ttk.Scrollbar(oq_frame, orient=tk.VERTICAL, command=oq_text.yview)
        oq_text.configure(yscrollcommand=oq_scroll.set)
        oq_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        oq_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        oq_text.config(state=tk.NORMAL)
        for question, stats in self.statistics.get('open_question_stats', {}).items():
            oq_text.insert(tk.END, f"\n{'='*60}\n")
            oq_text.insert(tk.END, f"问题: {question}\n")
            oq_text.insert(tk.END, f"{'-'*60}\n")
            oq_text.insert(tk.END, f"  已回答: {stats.get('answered', 0)} 篇\n")
            oq_text.insert(tk.END, f"  未回答: {stats.get('missing', 0)} 篇\n")
        oq_text.config(state=tk.DISABLED)

        # Close button
        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=10)

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
            messagebox.showerror("错误", "没有可导出的结果")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV 文件", "*.csv")])
        if path:
            self.df.to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo("成功", "CSV 已导出")

    def export_excel(self) -> None:
        if self.df is None:
            messagebox.showerror("错误", "没有可导出的结果")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel 文件", "*.xlsx")])
        if path:
            self.df.to_excel(path, index=False, engine="openpyxl")
            messagebox.showinfo("成功", "Excel 已导出")

    def add_mode(self) -> None:
        name = simpledialog.askstring("新模式", "请输入模式名称:", parent=self.app.root)
        if not name:
            return
        if name in self.modes_data:
            messagebox.showerror("错误", "模式已存在")
            return
        desc = simpledialog.askstring("描述", "请输入模式描述:", parent=self.app.root) or ""
        self.modes_data[name] = {"description": desc, "open_questions": [], "yes_no_questions": []}
        with self.q_config_path.open("w", encoding="utf-8") as f:
            json.dump(self.modes_data, f, ensure_ascii=False, indent=2)
        self.mode_cb.configure(values=list(self.modes_data.keys()))
        self.mode_var.set(name)

    def edit_questions(self) -> None:
        mode = self.mode_var.get()
        try:
            with self.q_config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        mode_data = data.get(mode, {"description": "", "open_questions": [], "yes_no_questions": []})
        open_q = mode_data.get("open_questions", [])
        yes_no_q = mode_data.get("yes_no_questions", [])

        win = tk.Toplevel(self.app.root)
        win.title("编辑问题")
        win.geometry("640x420")
        win.transient(self.app.root)
        win.grab_set()

        content = ttk.Frame(win)
        content.pack(fill=tk.BOTH, expand=True)

        def prompt_question(initial: Optional[dict[str, str]] = None) -> Optional[dict[str, str]]:
            dialog = tk.Toplevel(win)
            dialog.title("设置问题")
            dialog.transient(win)
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
                    messagebox.showerror("错误", "Key 不能为空", parent=dialog)
                    return
                if not question:
                    messagebox.showerror("错误", "Question 不能为空", parent=dialog)
                    return
                if not column_name:
                    messagebox.showerror("错误", "Column Name 不能为空", parent=dialog)
                    return
                result = {"key": key, "question": question, "column_name": column_name}
                dialog.destroy()

            def on_cancel() -> None:
                dialog.destroy()

            ttk.Button(button_frame, text="保存", command=on_save).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)

            dialog.columnconfigure(1, weight=1)
            dialog.rowconfigure(2, weight=1)
            dialog.protocol("WM_DELETE_WINDOW", on_cancel)
            key_entry.focus_set()
            win.wait_window(dialog)
            return result

        def make_section(parent, title, items):
            frame = ttk.LabelFrame(parent, text=title)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            lb = tk.Listbox(frame)
            lb.pack(fill=tk.BOTH, expand=True)
            for q in items:
                lb.insert(tk.END, q["question"])

            def add_item():
                new_item = prompt_question()
                if not new_item:
                    return
                items.append(new_item)
                lb.insert(tk.END, new_item["question"])

            def edit_item():
                sel = lb.curselection()
                if not sel:
                    messagebox.showwarning("提示", "请先选择一个问题")
                    return
                idx = sel[0]
                item = items[idx]
                updated_item = prompt_question(item)
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
            ttk.Button(btn_f, text="添加", command=add_item).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_f, text="编辑", command=edit_item).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_f, text="删除", command=del_item).pack(side=tk.LEFT, padx=5)
            lb.bind("<Double-Button-1>", lambda _event: edit_item())
            return frame

        make_section(content, "开放问题", open_q)
        make_section(content, "是/否问题", yes_no_q)

        def close_window() -> None:
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        def save():
            if not mode:
                messagebox.showerror("错误", "请先选择一个模式后再保存。", parent=win)
                return

            updated_mode = dict(mode_data)
            updated_mode["open_questions"] = deepcopy(open_q)
            updated_mode["yes_no_questions"] = deepcopy(yes_no_q)

            data[mode] = updated_mode
            try:
                with self.q_config_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except OSError as exc:
                messagebox.showerror("错误", f"保存问题配置失败: {exc}", parent=win)
                return

            self.modes_data = data
            self.mode_cb.configure(values=list(self.modes_data.keys()))
            self.mode_var.set(mode)
            messagebox.showinfo("成功", "问题配置已保存。", parent=win)
            close_window()

        action_frame = ttk.Frame(win)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(action_frame, text="取消", command=close_window).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="保存", command=save).pack(side=tk.RIGHT, padx=5)
        win.protocol("WM_DELETE_WINDOW", close_window)
