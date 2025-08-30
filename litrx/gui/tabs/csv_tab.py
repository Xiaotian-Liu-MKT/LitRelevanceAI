from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from typing import TYPE_CHECKING, Optional

import pandas as pd

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

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        columns = ("title", "score", "analysis")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("title", text="标题")
        self.tree.heading("score", text="相关度")
        self.tree.heading("analysis", text="分析")
        self.tree.column("title", width=200)
        self.tree.column("score", width=80, anchor=tk.CENTER)
        self.tree.column("analysis", width=300)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", self.show_full_analysis)

        self.export_btn = ttk.Button(frame, text="导出结果", command=self.export_results, state=tk.DISABLED)
        self.export_btn.pack(pady=(0, 5))

        self.df: Optional[pd.DataFrame] = None
        self.analyzer: Optional[LiteratureAnalyzer] = None

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def start_analysis(self) -> None:
        path = self.file_var.get()
        topic = self.topic_var.get()
        if not path or not topic:
            messagebox.showerror("错误", "请填写研究主题并选择文件")
            return
        self.export_btn.config(state=tk.DISABLED)
        self.progress.set(0)
        self.df = None
        self.analyzer = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        threading.Thread(target=self.process_csv, args=(path, topic), daemon=True).start()

    def process_csv(self, path: str, topic: str) -> None:
        config = self.app.build_config()
        analyzer = LiteratureAnalyzer(config, topic)
        try:
            df = analyzer.read_scopus_csv(path)
        except Exception as e:  # pragma: no cover - UI feedback
            self.app.root.after(0, lambda: messagebox.showerror("错误", f"读取文件失败: {e}"))
            return

        self.df = df
        self.analyzer = analyzer
        total = len(df)
        for i, (idx, row) in enumerate(df.iterrows(), start=1):
            try:
                res = analyzer.analyze_paper(row['Title'], row['Abstract'])
                df.at[idx, 'Relevance Score'] = res['relevance_score']
                df.at[idx, 'Analysis Result'] = res['analysis']
                df.at[idx, 'Literature Review Suggestion'] = res.get('literature_review_suggestion', '')
                summary = res['analysis'].replace('\n', ' ')[:80]
                self.app.root.after(0, self.update_row, idx, row['Title'], res['relevance_score'], summary)
            except Exception as e:  # pragma: no cover - UI feedback
                self.app.root.after(0, self.update_row, idx, row['Title'], '', f"错误 {e}")
            self.app.root.after(0, lambda v=i / total * 100: self.progress.set(v))
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
            messagebox.showerror("错误", "没有可导出的结果")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV 文件", "*.csv")])
        if path:
            self.analyzer.save_results(self.df, path)
            messagebox.showinfo("成功", "结果已导出")
