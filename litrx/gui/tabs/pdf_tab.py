from __future__ import annotations

import io
import sys
import threading
import tkinter as tk
from contextlib import redirect_stdout
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from ...pdf_screener import main as pdf_main, DEFAULT_CONFIG as PDF_CONFIG

if TYPE_CHECKING:  # pragma: no cover
    from ..base_window import BaseWindow


class PdfTab:
    """Tab for PDF screening."""

    def __init__(self, app: BaseWindow) -> None:
        self.app = app
        frame = ttk.Frame(app.notebook)
        app.notebook.add(frame, text="PDF 筛选")

        ttk.Label(frame, text="选择PDF文件夹:").pack(anchor=tk.W, padx=5, pady=2)
        folder_frame = ttk.Frame(frame)
        folder_frame.pack(fill=tk.X, padx=5)
        self.folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.folder_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="浏览", command=lambda: self.app.browse_folder(self.folder_var)).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(frame, text="可选元数据文件:").pack(anchor=tk.W, padx=5, pady=(8, 2))
        meta_frame = ttk.Frame(frame)
        meta_frame.pack(fill=tk.X, padx=5)
        self.meta_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.meta_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            meta_frame,
            text="浏览",
            command=lambda: self.app.browse_file(self.meta_var, ("CSV or Excel", "*.csv *.xlsx")),
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="开始筛选", command=self.start_screen).pack(pady=5)

        self.progress = tk.DoubleVar()
        ttk.Progressbar(frame, variable=self.progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)
        self.result = tk.Text(frame, height=10)
        self.result.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

    # ------------------------------------------------------------------
    # Screening
    # ------------------------------------------------------------------
    def start_screen(self) -> None:
        folder = self.folder_var.get()
        if not folder:
            messagebox.showerror("错误", "请先选择PDF文件夹")
            return
        metadata = self.meta_var.get()
        threading.Thread(target=self.process_pdf, args=(folder, metadata), daemon=True).start()

    def process_pdf(self, folder: str, metadata: str) -> None:
        config = PDF_CONFIG.copy()
        config.update(self.app.build_config())
        argv_backup = sys.argv
        sys.argv = ["pdf_screener", "--pdf-folder", folder]
        if metadata:
            sys.argv += ["--metadata-file", metadata]
        output = io.StringIO()
        try:
            with redirect_stdout(output):
                pdf_main()
            self.result.insert(tk.END, output.getvalue())
        except Exception as e:  # pragma: no cover
            self.result.insert(tk.END, f"错误: {e}\n")
        finally:
            sys.argv = argv_backup
            self.progress.set(100)
