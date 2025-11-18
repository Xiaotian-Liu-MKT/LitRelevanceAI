"""Literature Matrix Analysis Tab for GUI."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd
import yaml

from ...tk_compat import ensure_native_macos_version

ensure_native_macos_version()

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ...matrix_analyzer import (
    load_matrix_config,
    process_literature_matrix,
    save_results,
)
from ..dialogs import DimensionEditorDialog

if TYPE_CHECKING:  # pragma: no cover
    from ..base_window import BaseWindow


class MatrixTab:
    """Tab for Literature Matrix Analysis."""

    def __init__(self, app: BaseWindow) -> None:
        """Initialize Matrix Tab.

        Args:
            app: Parent BaseWindow application
        """
        self.app = app
        self.matrix_config: Dict[str, Any] = {}
        self.default_config_path = Path(__file__).resolve().parent.parent.parent.parent / "configs" / "matrix" / "default.yaml"

        # Create main frame
        frame = ttk.Frame(app.notebook, padding="10")
        app.notebook.add(frame, text="文献矩阵")

        self._create_widgets(frame)
        self._load_default_config()

    def _create_widgets(self, parent: ttk.Frame) -> None:
        """Create all widgets for the tab."""

        # ============================================================
        # Configuration Section
        # ============================================================
        config_frame = ttk.LabelFrame(parent, text="矩阵配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # Dimensions info and buttons
        dim_info_frame = ttk.Frame(config_frame)
        dim_info_frame.pack(fill=tk.X, pady=(0, 5))

        self.dim_count_var = tk.StringVar(value="当前维度数：0")
        ttk.Label(dim_info_frame, textvariable=self.dim_count_var).pack(side=tk.LEFT)

        # Buttons frame
        btn_group = ttk.Frame(config_frame)
        btn_group.pack(fill=tk.X)

        ttk.Button(btn_group, text="✏️ 编辑维度", command=self._edit_dimensions, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_group, text="📥 导入配置", command=self._import_config, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_group, text="📤 导出配置", command=self._export_config, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_group, text="🔄 重置默认", command=self._reset_config, width=15).pack(side=tk.LEFT, padx=2)

        # ============================================================
        # Data Input Section
        # ============================================================
        input_frame = ttk.LabelFrame(parent, text="数据输入", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # PDF folder
        ttk.Label(input_frame, text="PDF文件夹*:").pack(anchor=tk.W, pady=(0, 2))
        folder_frame = ttk.Frame(input_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        self.folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            folder_frame,
            text="浏览",
            command=lambda: self.app.browse_folder(self.folder_var),
            width=10
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Metadata file
        ttk.Label(input_frame, text="元数据文件（可选 - 支持Zotero导出的CSV/Excel）:").pack(anchor=tk.W, pady=(0, 2))
        meta_frame = ttk.Frame(input_frame)
        meta_frame.pack(fill=tk.X, pady=(0, 10))

        self.meta_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.meta_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            meta_frame,
            text="浏览",
            command=lambda: self.app.browse_file(self.meta_var, ("CSV or Excel", "*.csv *.xlsx")),
            width=10
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Output format
        output_format_frame = ttk.Frame(input_frame)
        output_format_frame.pack(fill=tk.X)

        ttk.Label(output_format_frame, text="输出格式:").pack(side=tk.LEFT)
        self.output_var = tk.StringVar(value="xlsx")
        ttk.Radiobutton(output_format_frame, text="Excel (.xlsx)", variable=self.output_var, value="xlsx").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(output_format_frame, text="CSV (.csv)", variable=self.output_var, value="csv").pack(side=tk.LEFT)

        # Match only option
        self.match_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            input_frame,
            text="仅生成元数据匹配表（不进行AI分析）",
            variable=self.match_only_var
        ).pack(anchor=tk.W, pady=(5, 0))

        # ============================================================
        # Action Section
        # ============================================================
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_button = ttk.Button(
            action_frame,
            text="🚀 开始分析",
            command=self._start_analysis,
            style="Accent.TButton"
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame, text="📂 打开输出文件夹", command=self._open_output_folder).pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.status_label_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(parent, textvariable=self.status_label_var, foreground="gray")
        status_label.pack(anchor=tk.W)

        # ============================================================
        # Results Table Section
        # ============================================================
        table_frame = ttk.LabelFrame(parent, text="处理状态", padding="5")
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview
        columns = ("file", "match_status", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)

        self.tree.heading("file", text="PDF文件名")
        self.tree.heading("match_status", text="元数据匹配")
        self.tree.heading("status", text="分析状态")

        self.tree.column("file", width=300)
        self.tree.column("match_status", width=150)
        self.tree.column("status", width=120)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        vsb.grid(row=0, column=1, sticky=tk.NS)
        hsb.grid(row=1, column=0, sticky=tk.EW)

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Storage for results
        self.pdf_files: List[str] = []
        self.output_path: Optional[str] = None

    # ================================================================
    # Configuration Management
    # ================================================================

    def _load_default_config(self) -> None:
        """Load default matrix configuration."""
        try:
            self.matrix_config = load_matrix_config(str(self.default_config_path))
            self._update_dimension_count()
        except Exception as e:
            messagebox.showerror("配置加载失败", f"无法加载默认配置：\n{str(e)}")
            self.matrix_config = {'dimensions': []}

    def _update_dimension_count(self) -> None:
        """Update dimension count display."""
        count = len(self.matrix_config.get('dimensions', []))
        self.dim_count_var.set(f"当前维度数：{count}")

    def _edit_dimensions(self) -> None:
        """Open dimension editor dialog."""
        dimensions = self.matrix_config.get('dimensions', [])
        editor = DimensionEditorDialog(self.app.root, dimensions)
        self.app.root.wait_window(editor.dialog)

        if editor.result is not None:
            self.matrix_config['dimensions'] = editor.result
            self._update_dimension_count()

    def _import_config(self) -> None:
        """Import matrix configuration from YAML file."""
        filepath = filedialog.askopenfilename(
            title="选择矩阵配置文件",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                if 'dimensions' not in config:
                    messagebox.showwarning("导入失败", "配置文件中未找到维度定义")
                    return

                self.matrix_config = config
                self._update_dimension_count()
                messagebox.showinfo("导入成功", f"成功导入配置（{len(config.get('dimensions', []))} 个维度）")

            except Exception as e:
                messagebox.showerror("导入失败", f"导入配置文件时出错：\n{str(e)}")

    def _export_config(self) -> None:
        """Export current matrix configuration to YAML file."""
        if not self.matrix_config.get('dimensions'):
            messagebox.showwarning("无法导出", "当前没有配置任何维度")
            return

        filepath = filedialog.asksaveasfilename(
            title="保存矩阵配置",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(self.matrix_config, f, allow_unicode=True, sort_keys=False)

                messagebox.showinfo("导出成功", f"配置已保存到：\n{filepath}")

            except Exception as e:
                messagebox.showerror("导出失败", f"导出配置文件时出错：\n{str(e)}")

    def _reset_config(self) -> None:
        """Reset to default configuration."""
        if messagebox.askyesno("确认重置", "确定要重置为默认配置吗？当前的配置修改将丢失。"):
            self._load_default_config()
            messagebox.showinfo("重置完成", "已恢复默认配置")

    # ================================================================
    # Analysis Processing
    # ================================================================

    def _start_analysis(self) -> None:
        """Start literature matrix analysis."""
        # Validate inputs
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showerror("输入错误", "请选择PDF文件夹")
            return

        if not os.path.isdir(folder):
            messagebox.showerror("输入错误", "PDF文件夹路径无效")
            return

        if not self.match_only_var.get():
            if not self.matrix_config.get('dimensions'):
                messagebox.showerror("配置错误", "请先配置至少一个分析维度")
                return

        # Update config with current GUI values
        self.matrix_config['output'] = {
            'file_type': self.output_var.get(),
            'file_suffix': '_literature_matrix',
            'include_match_status': True,
            'include_match_confidence': True,
            'column_order': 'metadata_first'
        }

        # Clear results table
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Disable start button
        self.start_button.state(['disabled'])
        self.progress_var.set(0)
        self.status_label_var.set("准备中...")

        # Start processing in background thread
        threading.Thread(
            target=self._process_analysis,
            args=(folder, self.meta_var.get().strip(), self.match_only_var.get()),
            daemon=True
        ).start()

    def _process_analysis(self, pdf_folder: str, metadata_path: str, match_only: bool) -> None:
        """Background processing function.

        Args:
            pdf_folder: Path to PDF folder
            metadata_path: Path to metadata file (or empty string)
            match_only: If True, only generate metadata mapping
        """
        try:
            # Load PDFs
            self.pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
            if not self.pdf_files:
                self.app.root.after(0, lambda: messagebox.showerror("错误", "PDF文件夹中未找到PDF文件"))
                return

            total = len(self.pdf_files)
            self.app.root.after(0, lambda: self.status_label_var.set(f"找到 {total} 个PDF文件"))

            # Populate tree
            for pdf in self.pdf_files:
                self.app.root.after(0, lambda p=pdf: self.tree.insert('', tk.END, values=(p, '-', '等待')))

            # Match-only mode
            if match_only:
                if not metadata_path:
                    self.app.root.after(0, lambda: messagebox.showwarning("警告", "未提供元数据文件，无法执行匹配"))
                    return

                self.app.root.after(0, lambda: self.status_label_var.set("正在匹配元数据..."))

                # Build mapping
                from ...matrix_analyzer import build_pdf_metadata_mapping
                if metadata_path.lower().endswith('.csv'):
                    metadata_df = pd.read_csv(metadata_path, encoding='utf-8-sig')
                else:
                    metadata_df = pd.read_excel(metadata_path)

                matching_config = self.matrix_config.get('metadata_matching', {
                    'id_columns': ['DOI', 'Title', 'Key'],
                    'title_similarity_threshold': 80,
                    'enable_filename_parsing': True
                })

                mapping_df = build_pdf_metadata_mapping(self.pdf_files, metadata_df, matching_config)

                # Update tree with match status
                for idx, row in mapping_df.iterrows():
                    pdf = row['PDF_File']
                    match_status = row.get('Match_Status', 'not_matched')
                    confidence = row.get('Match_Confidence', 0)

                    status_text = f"{match_status} ({confidence:.0f}%)" if confidence > 0 else match_status

                    self.app.root.after(
                        0,
                        lambda p=pdf, s=status_text: self._update_tree_row(p, s, '已匹配')
                    )

                # Save mapping
                mapping_path = os.path.join(pdf_folder, "pdf_metadata_mapping.csv")
                mapping_df.to_csv(mapping_path, index=False, encoding='utf-8-sig')
                self.output_path = mapping_path

                self.app.root.after(0, lambda: self.progress_var.set(100))
                self.app.root.after(0, lambda: self.status_label_var.set(f"✓ 完成！匹配结果已保存"))
                self.app.root.after(0, lambda: messagebox.showinfo("完成", f"元数据匹配完成\n\n结果已保存到：\n{mapping_path}"))

            else:
                # Full analysis mode
                self.app.root.after(0, lambda: self.status_label_var.set("正在进行AI分析..."))

                # Build app config
                app_config = self.app.build_config()

                # Process with callbacks
                results_df, mapping_df = process_literature_matrix(
                    pdf_folder,
                    metadata_path if metadata_path else None,
                    self.matrix_config,
                    app_config,
                    progress_callback=self._update_progress,
                    status_callback=self._update_status
                )

                # Save results
                output_path = save_results(
                    results_df,
                    mapping_df,
                    pdf_folder,
                    self.matrix_config.get('output', {})
                )
                self.output_path = output_path

                self.app.root.after(0, lambda: self.progress_var.set(100))
                self.app.root.after(0, lambda: self.status_label_var.set(f"✓ 分析完成！"))
                self.app.root.after(
                    0,
                    lambda: messagebox.showinfo("完成", f"文献矩阵分析完成\n\n结果已保存到：\n{output_path}")
                )

        except Exception as e:
            self.app.root.after(0, lambda: messagebox.showerror("处理失败", f"处理过程中出错：\n{str(e)}"))
            import traceback
            traceback.print_exc()

        finally:
            self.app.root.after(0, lambda: self.start_button.state(['!disabled']))

    def _update_progress(self, current: int, total: int) -> None:
        """Update progress bar.

        Args:
            current: Current count
            total: Total count
        """
        progress = (current / total) * 100
        self.app.root.after(0, lambda: self.progress_var.set(progress))
        self.app.root.after(0, lambda: self.status_label_var.set(f"处理中... ({current}/{total})"))

    def _update_status(self, pdf: str, status: str) -> None:
        """Update status for a specific PDF in the tree.

        Args:
            pdf: PDF filename
            status: Status text
        """
        self.app.root.after(0, lambda: self._update_tree_row(pdf, None, status))

    def _update_tree_row(self, pdf: str, match_status: Optional[str], analysis_status: str) -> None:
        """Update tree row values.

        Args:
            pdf: PDF filename
            match_status: Match status text (or None to keep current)
            analysis_status: Analysis status text
        """
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values[0] == pdf:
                new_values = list(values)
                if match_status is not None:
                    new_values[1] = match_status
                new_values[2] = analysis_status
                self.tree.item(item, values=new_values)
                break

    def _open_output_folder(self) -> None:
        """Open the output folder in file explorer."""
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("提示", "请先选择有效的PDF文件夹")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹：\n{str(e)}")
