from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from ...ai_client import AIClient
from ...abstract_screener import (
    load_config as load_abs_config,
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
        self.mode_var = tk.StringVar(value=ABSTRACT_CONFIG.get("CONFIG_MODE", "weekly_screening"))
        ttk.Combobox(frame, textvariable=self.mode_var, values=["weekly_screening", "specific_research"]).pack(
            fill=tk.X, padx=5
        )

        ttk.Button(frame, text="开始筛选", command=self.start_screen).pack(pady=5)

        self.progress = tk.DoubleVar()
        ttk.Progressbar(frame, variable=self.progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)
        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status).pack(pady=(0, 5))

        self.result = tk.Text(frame, height=10)
        self.result.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

    # ------------------------------------------------------------------
    # Screening
    # ------------------------------------------------------------------
    def start_screen(self) -> None:
        path = self.file_var.get()
        if not path:
            messagebox.showerror("错误", "请先选择文件")
            return
        mode = self.mode_var.get()
        threading.Thread(target=self.process_abstract, args=(path, mode), daemon=True).start()

    def process_abstract(self, path: str, mode: str) -> None:
        config = ABSTRACT_CONFIG.copy()
        config.update(self.app.build_config())
        config["INPUT_FILE_PATH"] = path
        config["CONFIG_MODE"] = mode
        try:
            client = AIClient(config)
            _, q = load_abs_config()
            open_q = q.get("open_questions", [])
            yes_no_q = q.get("yes_no_questions", [])
            df, title_col, abstract_col = load_and_validate_data(path, config)
            df = prepare_dataframe(df, open_q, yes_no_q)
            total = len(df)
            for index, row in df.iterrows():
                self.status.set(f"处理中: {index + 1}/{total}")
                self.progress.set((index + 1) / total * 100)
                analyze_article(df, index, row, title_col, abstract_col, open_q, yes_no_q, config, client)
            base, ext = os.path.splitext(path)
            output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
            if output_file_path.endswith('.csv'):
                df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(output_file_path, index=False, engine='openpyxl')
            self.result.insert(tk.END, f"完成! 结果已保存到: {output_file_path}\n")
        except Exception as e:  # pragma: no cover
            self.result.insert(tk.END, f"错误: {e}\n")
        finally:
            self.status.set("")
            self.progress.set(0)
