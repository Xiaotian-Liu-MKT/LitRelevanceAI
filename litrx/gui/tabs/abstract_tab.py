from __future__ import annotations

import json
import os
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import TYPE_CHECKING, Optional

import pandas as pd

from ...ai_client import AIClient
from ...abstract_screener import (
    load_mode_questions,
    load_and_validate_data,
    prepare_dataframe,
    analyze_article,
    DEFAULT_CONFIG as ABSTRACT_CONFIG,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..base_window import BaseWindow


class AbstractTab:
    """Tab for abstract screening."""

    def __init__(self, app: BaseWindow) -> None:
        self.app = app
        frame = ttk.Frame(app.notebook)
        app.notebook.add(frame, text="摘要筛选")

        ttk.Label(frame, text="选择CSV/XLSX文件:").pack(anchor=tk.W, padx=5, pady=2)
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=tk.X, padx=5)
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            file_frame,
            text="浏览",
            command=lambda: self.app.browse_file(self.file_var, ("CSV or Excel", "*.csv *.xlsx")),
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="筛选模式:").pack(anchor=tk.W, padx=5, pady=(8, 2))
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill=tk.X, padx=5)
        q_path = Path(__file__).resolve().parent.parent.parent.parent / "questions_config.json"
        try:
            with q_path.open("r", encoding="utf-8") as f:
                self.modes_data = json.load(f)
                mode_options = list(self.modes_data.keys())
        except Exception:
            self.modes_data = {}
            mode_options = ["weekly_screening"]
        self.mode_var = tk.StringVar(value=mode_options[0] if mode_options else "")
        self.mode_cb = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=mode_options)
        self.mode_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(mode_frame, text="添加模式", command=self.add_mode).pack(side=tk.LEFT, padx=5)
        self.q_config_path = q_path

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="开始筛选", command=self.start_screen).pack(side=tk.LEFT, padx=5)
        self.stop_event = threading.Event()
        self.stop_btn = ttk.Button(btn_frame, text="中止任务", command=self.stop_event.set, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="编辑问题", command=self.edit_questions).pack(side=tk.LEFT, padx=5)

        self.progress = tk.DoubleVar()
        ttk.Progressbar(frame, variable=self.progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)
        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status).pack(pady=(0, 5))

        ttk.Label(frame, text="日志:").pack(anchor=tk.W, padx=5)
        self.log_text = tk.Text(frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        export_frame = ttk.Frame(frame)
        export_frame.pack(pady=(0, 5))
        self.export_csv_btn = ttk.Button(export_frame, text="导出 CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_csv_btn.pack(side=tk.LEFT, padx=5)
        self.export_excel_btn = ttk.Button(export_frame, text="导出 Excel", command=self.export_excel, state=tk.DISABLED)
        self.export_excel_btn.pack(side=tk.LEFT, padx=5)

        self.df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Screening
    # ------------------------------------------------------------------
    def start_screen(self) -> None:
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
        config = ABSTRACT_CONFIG.copy()
        config.update(self.app.build_config())
        config["INPUT_FILE_PATH"] = path
        config["CONFIG_MODE"] = mode
        try:
            client = AIClient(config)
            q = load_mode_questions(mode)
            open_q = q.get("open_questions", [])
            yes_no_q = q.get("yes_no_questions", [])
            df, title_col, abstract_col = load_and_validate_data(path, config)
            df = prepare_dataframe(df, open_q, yes_no_q)
            self.df = df
            total = len(df)
            for index, row in df.iterrows():
                if self.stop_event.is_set():
                    self.app.root.after(0, self._log, "任务已中止")
                    break
                self.app.root.after(0, self.status.set, f"处理中: {index + 1}/{total}")
                self.app.root.after(0, self.progress.set, (index + 1) / total * 100)
                parsed = analyze_article(df, index, row, title_col, abstract_col, open_q, yes_no_q, config, client)
                qa = parsed.get("quick_analysis", {}) if parsed else {}
                sr = parsed.get("screening_results", {}) if parsed else {}
                summary_parts = [f"{k}:{v}" for k, v in {**qa, **sr}.items()]
                self.app.root.after(0, self._log, f"条目 {index + 1}: {'; '.join(summary_parts)}")
            else:
                base, ext = os.path.splitext(path)
                output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
                if output_file_path.endswith('.csv'):
                    df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
                else:
                    df.to_excel(output_file_path, index=False, engine='openpyxl')
                self.app.root.after(0, self._log, f"完成! 结果已保存到: {output_file_path}")
        except Exception as e:  # pragma: no cover
            self.app.root.after(0, self._log, f"错误: {e}")
        finally:
            self.app.root.after(0, self.status.set, "")
            self.app.root.after(0, self.progress.set, 0)
            self.app.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self.app.root.after(0, lambda: self.enable_exports(self.df is not None))

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

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
        win.geometry("600x400")

        def make_section(parent, title, items):
            frame = ttk.LabelFrame(parent, text=title)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            lb = tk.Listbox(frame)
            lb.pack(fill=tk.BOTH, expand=True)
            for q in items:
                lb.insert(tk.END, q["question"])

            def add_item():
                key = simpledialog.askstring("键", "Key:", parent=win)
                if not key:
                    return
                question = simpledialog.askstring("问题", "Question:", parent=win)
                if not question:
                    return
                column = simpledialog.askstring("列名", "Column Name:", parent=win)
                if not column:
                    return
                items.append({"key": key, "question": question, "column_name": column})
                lb.insert(tk.END, question)

            def del_item():
                sel = lb.curselection()
                if sel:
                    idx = sel[0]
                    lb.delete(idx)
                    items.pop(idx)

            btn_f = ttk.Frame(frame)
            btn_f.pack(pady=5)
            ttk.Button(btn_f, text="添加", command=add_item).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_f, text="删除", command=del_item).pack(side=tk.LEFT, padx=5)
            return frame

        make_section(win, "开放问题", open_q)
        make_section(win, "是/否问题", yes_no_q)

        def save():
            data[mode] = {
                "description": mode_data.get("description", ""),
                "open_questions": open_q,
                "yes_no_questions": yes_no_q,
            }
            with self.q_config_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.modes_data = data
            self.mode_cb.configure(values=list(self.modes_data.keys()))
            win.destroy()

        ttk.Button(win, text="保存", command=save).pack(pady=5)
