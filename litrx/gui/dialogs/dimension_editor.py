"""Dimension Editor Dialog for Literature Matrix configuration."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from ...tk_compat import ensure_native_macos_version

ensure_native_macos_version()

import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class DimensionEditorDialog:
    """Dialog for editing matrix dimensions configuration."""

    # Dimension type options
    DIMENSION_TYPES = [
        ('text', '开放文本'),
        ('yes_no', '是/否/不确定'),
        ('single_choice', '单选题'),
        ('multiple_choice', '多选题'),
        ('number', '数值提取'),
        ('rating', '评分'),
        ('list', '列表提取'),
    ]

    def __init__(self, parent: tk.Tk, dimensions: List[Dict[str, Any]]):
        """Initialize dimension editor dialog.

        Args:
            parent: Parent window
            dimensions: List of dimension dictionaries to edit
        """
        self.parent = parent
        self.dimensions = copy.deepcopy(dimensions)  # Work on a copy
        self.result = None  # Will store edited dimensions if user clicks OK

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑文献矩阵维度")
        self.dialog.geometry("900x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._populate_list()

        # Center dialog on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Instructions
        inst_label = ttk.Label(
            main_frame,
            text="配置文献矩阵的分析维度。每个维度对应AI分析的一个问题。",
            wraplength=850
        )
        inst_label.pack(anchor=tk.W, pady=(0, 10))

        # List frame with scrollbar
        list_frame = ttk.LabelFrame(main_frame, text="维度列表", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview for dimensions
        columns = ('type', 'question', 'column')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        self.tree.heading('type', text='类型')
        self.tree.heading('question', text='问题')
        self.tree.heading('column', text='列名')

        self.tree.column('type', width=120)
        self.tree.column('question', width=500)
        self.tree.column('column', width=180)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click to edit
        self.tree.bind('<Double-Button-1>', lambda e: self._edit_dimension())

        # Button frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        # Left side buttons (CRUD operations)
        left_btns = ttk.Frame(btn_frame)
        left_btns.pack(side=tk.LEFT)

        ttk.Button(left_btns, text="➕ 添加", command=self._add_dimension, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_btns, text="🤖 AI 辅助创建", command=self._ai_assist_create, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_btns, text="✏️ 编辑", command=self._edit_dimension, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_btns, text="🗑️ 删除", command=self._delete_dimension, width=10).pack(side=tk.LEFT, padx=2)

        # Middle buttons (ordering)
        middle_btns = ttk.Frame(btn_frame)
        middle_btns.pack(side=tk.LEFT, padx=20)

        ttk.Button(middle_btns, text="↑ 上移", command=self._move_up, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(middle_btns, text="↓ 下移", command=self._move_down, width=10).pack(side=tk.LEFT, padx=2)

        # Right side buttons (import/export)
        right_btns = ttk.Frame(btn_frame)
        right_btns.pack(side=tk.RIGHT)

        ttk.Button(right_btns, text="📥 导入", command=self._import_config, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_btns, text="📤 导出", command=self._export_config, width=10).pack(side=tk.LEFT, padx=2)

        # Bottom buttons (OK/Cancel)
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        ttk.Button(bottom_frame, text="确定", command=self._on_ok, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="取消", command=self._on_cancel, width=15).pack(side=tk.RIGHT)

    def _populate_list(self) -> None:
        """Populate the treeview with current dimensions."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add dimensions
        for dim in self.dimensions:
            dim_type = dim.get('type', 'text')
            type_display = dict(self.DIMENSION_TYPES).get(dim_type, dim_type)
            question = dim.get('question', '')
            column = dim.get('column_name', dim.get('key', ''))

            # Truncate long questions for display
            if len(question) > 60:
                question = question[:57] + '...'

            self.tree.insert('', tk.END, values=(type_display, question, column))

    def _add_dimension(self) -> None:
        """Add a new dimension."""
        editor = DimensionDetailEditor(self.dialog, None)
        self.dialog.wait_window(editor.dialog)

        if editor.result:
            self.dimensions.append(editor.result)
            self._populate_list()

    def _ai_assist_create(self) -> None:
        """Open AI assistant for dimension creation."""
        from .ai_dimension_assistant import AIDimensionAssistantDialog

        # Get configuration from parent window if it has build_config method
        # Otherwise use empty config (will need API keys from env)
        config = getattr(self.parent, 'build_config', lambda: {})()

        # Open AI assistant dialog
        dialog = AIDimensionAssistantDialog(self.dialog, config)
        self.dialog.wait_window(dialog.dialog)

        # Handle result
        if dialog.result:
            # Add selected dimensions to the list
            self.dimensions.extend(dialog.result)
            self._populate_list()
            messagebox.showinfo(
                "成功",
                f"成功添加 {len(dialog.result)} 个维度！"
            )

    def _edit_dimension(self) -> None:
        """Edit selected dimension."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("未选择", "请先选择要编辑的维度")
            return

        # Get selected index
        idx = self.tree.index(selection[0])
        dim = self.dimensions[idx]

        editor = DimensionDetailEditor(self.dialog, dim)
        self.dialog.wait_window(editor.dialog)

        if editor.result:
            self.dimensions[idx] = editor.result
            self._populate_list()

    def _delete_dimension(self) -> None:
        """Delete selected dimension."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("未选择", "请先选择要删除的维度")
            return

        if messagebox.askyesno("确认删除", "确定要删除选中的维度吗？"):
            idx = self.tree.index(selection[0])
            del self.dimensions[idx]
            self._populate_list()

    def _move_up(self) -> None:
        """Move selected dimension up."""
        selection = self.tree.selection()
        if not selection:
            return

        idx = self.tree.index(selection[0])
        if idx > 0:
            self.dimensions[idx], self.dimensions[idx-1] = self.dimensions[idx-1], self.dimensions[idx]
            self._populate_list()
            # Re-select the moved item
            self.tree.selection_set(self.tree.get_children()[idx-1])

    def _move_down(self) -> None:
        """Move selected dimension down."""
        selection = self.tree.selection()
        if not selection:
            return

        idx = self.tree.index(selection[0])
        if idx < len(self.dimensions) - 1:
            self.dimensions[idx], self.dimensions[idx+1] = self.dimensions[idx+1], self.dimensions[idx]
            self._populate_list()
            # Re-select the moved item
            self.tree.selection_set(self.tree.get_children()[idx+1])

    def _import_config(self) -> None:
        """Import dimensions from YAML file."""
        filepath = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )

        if filepath:
            try:
                import yaml
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    dimensions = config.get('dimensions', [])

                if not dimensions:
                    messagebox.showwarning("导入失败", "配置文件中未找到维度定义")
                    return

                if messagebox.askyesno("确认导入", f"找到 {len(dimensions)} 个维度。是否替换当前配置？"):
                    self.dimensions = dimensions
                    self._populate_list()
                    messagebox.showinfo("导入成功", f"成功导入 {len(dimensions)} 个维度")

            except Exception as e:
                messagebox.showerror("导入失败", f"导入配置文件时出错：\n{str(e)}")

    def _export_config(self) -> None:
        """Export current dimensions to YAML file."""
        filepath = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )

        if filepath:
            try:
                import yaml
                config = {
                    'dimensions': self.dimensions,
                    'metadata_matching': {
                        'id_columns': ['DOI', 'Title', 'Key'],
                        'title_similarity_threshold': 80,
                        'enable_filename_parsing': True
                    },
                    'output': {
                        'file_type': 'xlsx',
                        'file_suffix': '_literature_matrix',
                        'include_match_status': True,
                        'include_match_confidence': True,
                        'column_order': 'metadata_first'
                    }
                }

                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, sort_keys=False)

                messagebox.showinfo("导出成功", f"配置已保存到：\n{filepath}")

            except Exception as e:
                messagebox.showerror("导出失败", f"导出配置文件时出错：\n{str(e)}")

    def _on_ok(self) -> None:
        """Handle OK button."""
        if not self.dimensions:
            if not messagebox.askyesno("确认", "维度列表为空，确定要继续吗？"):
                return

        self.result = self.dimensions
        self.dialog.destroy()

    def _on_cancel(self) -> None:
        """Handle Cancel button."""
        self.result = None
        self.dialog.destroy()


class DimensionDetailEditor:
    """Dialog for editing a single dimension's details."""

    def __init__(self, parent: tk.Toplevel, dimension: Optional[Dict[str, Any]]):
        """Initialize dimension detail editor.

        Args:
            parent: Parent window
            dimension: Dimension dict to edit, or None for new dimension
        """
        self.parent = parent
        self.dimension = copy.deepcopy(dimension) if dimension else {}
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑维度" if dimension else "添加维度")
        self.dialog.geometry("600x550")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Variables
        self.type_var = tk.StringVar(value=self.dimension.get('type', 'text'))
        self.key_var = tk.StringVar(value=self.dimension.get('key', ''))
        self.question_var = tk.StringVar(value=self.dimension.get('question', ''))
        self.column_var = tk.StringVar(value=self.dimension.get('column_name', ''))

        # Type-specific variables
        self.unit_var = tk.StringVar(value=self.dimension.get('unit', ''))
        self.scale_var = tk.IntVar(value=self.dimension.get('scale', 5))
        self.scale_desc_var = tk.StringVar(value=self.dimension.get('scale_description', ''))
        self.separator_var = tk.StringVar(value=self.dimension.get('separator', '; '))
        self.options_text = tk.Text(height=5)

        self._create_widgets()
        self._update_type_specific_widgets()

        # Center dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Basic fields
        row = 0

        # Type
        ttk.Label(main_frame, text="维度类型*:").grid(row=row, column=0, sticky=tk.W, pady=5)
        type_combo = ttk.Combobox(
            main_frame,
            textvariable=self.type_var,
            values=[f"{code} - {name}" for code, name in DimensionEditorDialog.DIMENSION_TYPES],
            state='readonly',
            width=40
        )
        type_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        type_combo.bind('<<ComboboxSelected>>', lambda e: self._update_type_specific_widgets())
        row += 1

        # Key
        ttk.Label(main_frame, text="字段标识*:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.key_var, width=40).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        ttk.Label(main_frame, text="(英文，用于数据存储)", font=('', 8), foreground='gray').grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # Question
        ttk.Label(main_frame, text="问题*:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        question_text = tk.Text(main_frame, height=3, width=40, wrap=tk.WORD)
        question_text.insert('1.0', self.question_var.get())
        question_text.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        self.question_text = question_text
        row += 1

        # Column name
        ttk.Label(main_frame, text="Excel列名*:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.column_var, width=40).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        row += 1

        # Separator
        ttk.Label(main_frame, text="─" * 60).grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Type-specific frame
        self.specific_frame = ttk.LabelFrame(main_frame, text="类型特定配置", padding="10")
        self.specific_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=5)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)

        ttk.Button(btn_frame, text="确定", command=self._on_ok, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=15).pack(side=tk.RIGHT)

        # Configure column weights
        main_frame.columnconfigure(1, weight=1)

    def _update_type_specific_widgets(self) -> None:
        """Update type-specific configuration widgets based on selected type."""
        # Clear specific frame
        for widget in self.specific_frame.winfo_children():
            widget.destroy()

        # Get selected type (extract code from "code - name" format)
        type_display = self.type_var.get()
        dim_type = type_display.split(' - ')[0] if ' - ' in type_display else type_display

        row = 0

        if dim_type == 'single_choice' or dim_type == 'multiple_choice':
            # Options (one per line)
            ttk.Label(self.specific_frame, text="选项（每行一个）*:").grid(row=row, column=0, sticky=tk.NW, pady=5)

            options_frame = ttk.Frame(self.specific_frame)
            options_frame.grid(row=row, column=1, sticky=tk.EW, pady=5)

            self.options_text = tk.Text(options_frame, height=6, width=40)
            scrollbar = ttk.Scrollbar(options_frame, orient=tk.VERTICAL, command=self.options_text.yview)
            self.options_text.configure(yscrollcommand=scrollbar.set)

            # Pre-fill options if editing
            if 'options' in self.dimension:
                self.options_text.insert('1.0', '\n'.join(self.dimension['options']))

            self.options_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        elif dim_type == 'number':
            # Unit
            ttk.Label(self.specific_frame, text="单位:").grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Entry(self.specific_frame, textvariable=self.unit_var, width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
            ttk.Label(self.specific_frame, text="(如：个、%、年)", font=('', 8), foreground='gray').grid(row=row, column=2, sticky=tk.W, padx=5)

        elif dim_type == 'rating':
            # Scale
            ttk.Label(self.specific_frame, text="评分范围*:").grid(row=row, column=0, sticky=tk.W, pady=5)
            scale_frame = ttk.Frame(self.specific_frame)
            scale_frame.grid(row=row, column=1, sticky=tk.W, pady=5)

            ttk.Label(scale_frame, text="1 到").pack(side=tk.LEFT)
            ttk.Spinbox(scale_frame, from_=3, to=10, textvariable=self.scale_var, width=5).pack(side=tk.LEFT, padx=5)
            ttk.Label(scale_frame, text="分").pack(side=tk.LEFT)
            row += 1

            # Scale description
            ttk.Label(self.specific_frame, text="评分说明:").grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Entry(self.specific_frame, textvariable=self.scale_desc_var, width=40).grid(row=row, column=1, sticky=tk.EW, pady=5)
            ttk.Label(self.specific_frame, text="(如：1=很差, 5=优秀)", font=('', 8), foreground='gray').grid(row=row, column=2, sticky=tk.W, padx=5)

        elif dim_type == 'list':
            # Separator
            ttk.Label(self.specific_frame, text="分隔符*:").grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Entry(self.specific_frame, textvariable=self.separator_var, width=10).grid(row=row, column=1, sticky=tk.W, pady=5)
            ttk.Label(self.specific_frame, text="(如：; 或 , )", font=('', 8), foreground='gray').grid(row=row, column=2, sticky=tk.W, padx=5)

        else:
            # No specific configuration for text and yes_no types
            ttk.Label(self.specific_frame, text="此类型无需额外配置", foreground='gray').grid(row=row, column=0, columnspan=3, pady=10)

        self.specific_frame.columnconfigure(1, weight=1)

    def _validate_inputs(self) -> bool:
        """Validate user inputs."""
        # Extract type code
        type_display = self.type_var.get()
        dim_type = type_display.split(' - ')[0] if ' - ' in type_display else type_display

        if not dim_type:
            messagebox.showerror("验证错误", "请选择维度类型")
            return False

        if not self.key_var.get().strip():
            messagebox.showerror("验证错误", "请输入字段标识")
            return False

        # Validate key format (should be valid Python identifier)
        key = self.key_var.get().strip()
        if not key.replace('_', '').isalnum() or key[0].isdigit():
            messagebox.showerror("验证错误", "字段标识必须是有效的标识符（字母、数字、下划线，不能以数字开头）")
            return False

        if not self.question_text.get('1.0', tk.END).strip():
            messagebox.showerror("验证错误", "请输入问题")
            return False

        if not self.column_var.get().strip():
            messagebox.showerror("验证错误", "请输入Excel列名")
            return False

        # Type-specific validation
        if dim_type in ('single_choice', 'multiple_choice'):
            options = self.options_text.get('1.0', tk.END).strip().split('\n')
            options = [opt.strip() for opt in options if opt.strip()]
            if not options:
                messagebox.showerror("验证错误", "请至少输入一个选项")
                return False

        return True

    def _on_ok(self) -> None:
        """Handle OK button."""
        if not self._validate_inputs():
            return

        # Extract type code
        type_display = self.type_var.get()
        dim_type = type_display.split(' - ')[0] if ' - ' in type_display else type_display

        # Build result
        result = {
            'type': dim_type,
            'key': self.key_var.get().strip(),
            'question': self.question_text.get('1.0', tk.END).strip(),
            'column_name': self.column_var.get().strip(),
        }

        # Add type-specific fields
        if dim_type in ('single_choice', 'multiple_choice'):
            options = self.options_text.get('1.0', tk.END).strip().split('\n')
            result['options'] = [opt.strip() for opt in options if opt.strip()]

        elif dim_type == 'number':
            if self.unit_var.get().strip():
                result['unit'] = self.unit_var.get().strip()

        elif dim_type == 'rating':
            result['scale'] = self.scale_var.get()
            if self.scale_desc_var.get().strip():
                result['scale_description'] = self.scale_desc_var.get().strip()

        elif dim_type == 'list':
            result['separator'] = self.separator_var.get()

        self.result = result
        self.dialog.destroy()

    def _on_cancel(self) -> None:
        """Handle Cancel button."""
        self.result = None
        self.dialog.destroy()
