from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from ...csv_analyzer import LiteratureAnalyzer

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from ..base_window import BaseWindow


class CsvTab:
    """Tab for CSV relevance analysis."""

    def __init__(self, app: BaseWindow) -> None:
        self.app = app
        frame = ttk.Frame(app.notebook)
        app.notebook.add(frame, text="CSV 相关性分析")

        ttk.Label(frame, text="研究主题:").pack(anchor=tk.W, padx=5, pady=2)
        self.topic_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.topic_var, width=40).pack(fill=tk.X, padx=5)

        ttk.Label(frame, text="选择CSV文件:").pack(anchor=tk.W, padx=5, pady=(8, 2))
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=tk.X, padx=5)
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            file_frame,
            text="浏览",
            command=lambda: self.app.browse_file(self.file_var, ("CSV 文件", "*.csv")),
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="开始分析", command=self.start_analysis).pack(pady=5)

        self.progress = tk.DoubleVar()
        ttk.Progressbar(frame, variable=self.progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)

        self.result = tk.Text(frame, height=10)
        self.result.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def start_analysis(self) -> None:
        path = self.file_var.get()
        topic = self.topic_var.get()
        if not path or not topic:
            messagebox.showerror("错误", "请填写研究主题并选择文件")
            return
        threading.Thread(target=self.process_csv, args=(path, topic), daemon=True).start()

    def process_csv(self, path: str, topic: str) -> None:
        config = self.app.build_config()
        analyzer = LiteratureAnalyzer(config, topic)
        try:
            df = analyzer.read_scopus_csv(path)
        except Exception as e:  # pragma: no cover - UI feedback
            self.result.insert(tk.END, f"读取文件失败: {e}\n")
            return
        total = len(df)
        for i, (idx, row) in enumerate(df.iterrows(), start=1):
            try:
                res = analyzer.analyze_paper(row['Title'], row['Abstract'])
                df.at[idx, 'Relevance Score'] = res['relevance_score']
                df.at[idx, 'Analysis Result'] = res['analysis']
                df.at[idx, 'Literature Review Suggestion'] = res.get('literature_review_suggestion', '')
                self.result.insert(tk.END, f"{row['Title']}: {res['relevance_score']}\n")
            except Exception as e:  # pragma: no cover - UI feedback
                self.result.insert(tk.END, f"{row['Title']}: 错误 {e}\n")
            self.progress.set(i / total * 100)
        analyzer.save_results(df, path)
        self.result.insert(tk.END, "分析完成\n")
