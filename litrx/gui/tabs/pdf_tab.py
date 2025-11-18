from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING, Dict, List

from ...tk_compat import ensure_native_macos_version

ensure_native_macos_version()

import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd

from ...ai_client import AIClient
from ...pdf_screener import (
    DEFAULT_CONFIG as PDF_CONFIG,
    build_pdf_metadata_mapping,
    construct_ai_prompt_instructions,
    get_ai_response,
    load_metadata_file,
    parse_ai_response_json,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..base_window import BaseWindow


class PdfTab:
    """Tab for PDF screening."""

    def __init__(self, app: BaseWindow) -> None:
        self.app = app
        frame = ttk.Frame(app.notebook)
        app.notebook.add(frame, text="PDF 筛选")

        ttk.Label(frame, text="研究问题:").pack(anchor=tk.W, padx=5, pady=2)
        self.question_var = tk.StringVar(value=PDF_CONFIG.get("RESEARCH_QUESTION", ""))
        ttk.Entry(frame, textvariable=self.question_var, width=40).pack(fill=tk.X, padx=5)

        ttk.Label(frame, text="筛选条件(逗号分隔):").pack(anchor=tk.W, padx=5, pady=(8, 2))
        self.criteria_var = tk.StringVar(
            value=",".join(PDF_CONFIG.get("CRITERIA", []))
        )
        ttk.Entry(frame, textvariable=self.criteria_var, width=40).pack(fill=tk.X, padx=5)

        ttk.Label(frame, text="输出类型:").pack(anchor=tk.W, padx=5, pady=(8, 2))
        self.output_var = tk.StringVar(value=PDF_CONFIG.get("OUTPUT_FILE_TYPE", "xlsx"))
        ttk.Combobox(
            frame, textvariable=self.output_var, values=["xlsx", "csv"], width=10
        ).pack(anchor=tk.W, padx=5)

        self.match_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="仅匹配元数据", variable=self.match_only_var).pack(anchor=tk.W, padx=5, pady=(8, 2))

        ttk.Label(frame, text="选择PDF文件夹:").pack(anchor=tk.W, padx=5, pady=(8, 2))
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

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        columns = ("file", "meta", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("file", text="文件名")
        self.tree.heading("meta", text="匹配元数据")
        self.tree.heading("status", text="状态")
        self.tree.column("file", width=200)
        self.tree.column("meta", width=200)
        self.tree.column("status", width=80, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.pdf_files: List[str] = []
        self.mapping_df: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Screening
    # ------------------------------------------------------------------
    def start_screen(self) -> None:
        folder = self.folder_var.get()
        if not folder:
            messagebox.showerror("错误", "请先选择PDF文件夹")
            return
        metadata = self.meta_var.get()
        self.load_pdfs(folder, metadata)
        threading.Thread(
            target=self.process_pdf,
            args=(folder, metadata, self.match_only_var.get()),
            daemon=True,
        ).start()

    def load_pdfs(self, folder: str, metadata: str) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress.set(0)
        try:
            self.pdf_files = sorted(
                [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
            )
        except Exception as e:  # pragma: no cover - UI feedback
            messagebox.showerror("错误", f"读取文件夹失败: {e}")
            return

        mapping: Dict[str, str] = {}
        self.mapping_df = None
        if metadata:
            try:
                meta_df = load_metadata_file(metadata)
                self.mapping_df = build_pdf_metadata_mapping(
                    self.pdf_files, meta_df, PDF_CONFIG.get("METADATA_ID_COLUMNS", [])
                )
                mapping = {
                    row["PDF File"]: ", ".join(
                        str(row.get(col, ""))
                        for col in PDF_CONFIG.get("METADATA_ID_COLUMNS", [])
                        if pd.notna(row.get(col)) and row.get(col) != ""
                    )
                    for _, row in self.mapping_df.iterrows()
                }
            except Exception as e:  # pragma: no cover - UI feedback
                messagebox.showerror("错误", f"元数据匹配失败: {e}")

        for pdf in self.pdf_files:
            meta = mapping.get(pdf, "")
            self.tree.insert("", "end", iid=pdf, values=(pdf, meta, "等待"))

    def update_status(self, pdf: str, status: str) -> None:
        if self.tree.exists(pdf):
            vals = list(self.tree.item(pdf, "values"))
            vals[2] = status
            self.tree.item(pdf, values=vals)

    def open_output_dir_prompt(self, folder: str) -> None:
        if messagebox.askyesno("完成", "打开结果文件夹？"):
            self.open_folder(folder)

    def open_folder(self, path: str) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[arg-type]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def process_pdf(self, folder: str, metadata: str, only_match: bool) -> None:
        config = PDF_CONFIG.copy()
        config.update(self.app.build_config())
        config["RESEARCH_QUESTION"] = self.question_var.get().strip()
        config["CRITERIA"] = [
            c.strip() for c in self.criteria_var.get().split(",") if c.strip()
        ]
        config["OUTPUT_FILE_TYPE"] = self.output_var.get()

        if only_match:
            for pdf in self.pdf_files:
                self.app.root.after(0, self.update_status, pdf, "已匹配")
            if self.mapping_df is not None:
                map_path = os.path.join(folder, "pdf_metadata_mapping.csv")
                self.mapping_df.to_csv(map_path, index=False, encoding="utf-8-sig")
            self.progress.set(100)
            self.open_output_dir_prompt(folder)
            return

        client = AIClient(config)
        criteria_list: List[str] = config.get("CRITERIA", [])
        base_prompt = construct_ai_prompt_instructions(
            config.get("RESEARCH_QUESTION", ""), criteria_list, []
        )

        results = []
        total = len(self.pdf_files)
        for i, pdf in enumerate(self.pdf_files, start=1):
            self.app.root.after(0, self.update_status, pdf, "处理中")
            full_path = os.path.join(folder, pdf)
            try:
                raw_text = get_ai_response(full_path, base_prompt, client)
                parsed = parse_ai_response_json(raw_text, criteria_list, [])
                row = {"PDF文件名": pdf}
                for c in criteria_list:
                    row[f"筛选_{c}"] = parsed["screening_results"][c]
                results.append(row)
                self.app.root.after(0, self.update_status, pdf, "完成")
            except Exception as e:  # pragma: no cover - UI feedback
                self.app.root.after(0, self.update_status, pdf, f"错误 {e}")
            finally:
                self.app.root.after(0, lambda v=i / total * 100: self.progress.set(v))
                time.sleep(config.get("API_REQUEST_DELAY", 1))

        df = pd.DataFrame(results)
        folder_name = os.path.basename(os.path.normpath(folder))
        output_base = f"{folder_name}{config['OUTPUT_FILE_SUFFIX']}"
        output_ext = f".{config.get('OUTPUT_FILE_TYPE', 'xlsx')}"
        output_path = os.path.join(folder, f"{output_base}{output_ext}")
        if output_ext == ".csv":
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        else:
            df.to_excel(output_path, index=False, engine="openpyxl")
        if self.mapping_df is not None:
            map_path = os.path.join(folder, "pdf_metadata_mapping.csv")
            self.mapping_df.to_csv(map_path, index=False, encoding="utf-8-sig")
        self.open_output_dir_prompt(folder)
