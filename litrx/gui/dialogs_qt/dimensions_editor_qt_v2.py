"""Graphical dimension editor for literature matrix analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QSpinBox,
    QTextEdit, QGroupBox, QSplitter, QWidget, QFormLayout, QScrollArea
)

from ...i18n import t


class DimensionEditorDialog(QDialog):
    """Graphical editor for a single dimension with type-specific fields."""

    DIMENSION_TYPES = [
        ("text", "文本 / Text"),
        ("yes_no", "是/否 / Yes/No"),
        ("single_choice", "单选 / Single Choice"),
        ("multiple_choice", "多选 / Multiple Choice"),
        ("number", "数字 / Number"),
        ("rating", "评分 / Rating"),
        ("list", "列表 / List"),
    ]

    def __init__(self, parent, dimension: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("编辑维度 / Edit Dimension")
        self.setModal(True)
        self.resize(650, 550)

        self.dimension = dimension or {
            "type": "text",
            "key": "",
            "question": "",
            "column_name": ""
        }
        self.result: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._load_dimension()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # Type selector
        self.type_combo = QComboBox()
        for type_key, type_label in self.DIMENSION_TYPES:
            self.type_combo.addItem(type_label, type_key)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_layout.addRow("维度类型 / Type *:", self.type_combo)

        # Common fields
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("e.g., research_method")
        form_layout.addRow("键名 / Key *:", self.key_edit)

        self.column_edit = QLineEdit()
        self.column_edit.setPlaceholderText("e.g., 研究方法 / Research Method")
        form_layout.addRow("列名 / Column Name *:", self.column_edit)

        self.question_edit = QTextEdit()
        self.question_edit.setMaximumHeight(100)
        self.question_edit.setPlaceholderText("输入问题描述 / Enter question description")
        form_layout.addRow("问题 / Question *:", self.question_edit)

        # Type-specific fields container
        self.specific_container = QGroupBox("类型特定设置 / Type-Specific Settings")
        self.specific_layout = QVBoxLayout(self.specific_container)
        form_layout.addRow(self.specific_container)

        scroll.setWidget(form_widget)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存 / Save")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消 / Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _load_dimension(self) -> None:
        """Load dimension data into form."""
        dim_type = self.dimension.get("type", "text")

        # Set type
        idx = self.type_combo.findData(dim_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # Set common fields
        self.key_edit.setText(self.dimension.get("key", ""))
        self.column_edit.setText(self.dimension.get("column_name", ""))
        self.question_edit.setPlainText(self.dimension.get("question", ""))

        # Trigger type-specific UI
        self._on_type_changed()

    def _on_type_changed(self) -> None:
        """Update type-specific fields based on selected type."""
        # Clear existing widgets
        while self.specific_layout.count():
            item = self.specific_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        dim_type = self.type_combo.currentData()

        if dim_type in ("single_choice", "multiple_choice"):
            self._build_choice_fields()
        elif dim_type == "rating":
            self._build_rating_fields()
        elif dim_type == "list":
            self._build_list_fields()
        else:
            # No special fields for text, yes_no, number
            label = QLabel("此类型无额外设置 / No additional settings for this type")
            label.setStyleSheet("color: gray; font-style: italic;")
            self.specific_layout.addWidget(label)

    def _build_choice_fields(self) -> None:
        """Build UI for choice type options."""
        label = QLabel("选项列表 / Options (one per line):")
        self.specific_layout.addWidget(label)

        self.options_edit = QTextEdit()
        self.options_edit.setMaximumHeight(120)
        self.options_edit.setPlaceholderText("选项1\n选项2\n选项3")

        # Load existing options
        options = self.dimension.get("options", [])
        if options:
            self.options_edit.setPlainText("\n".join(options))

        self.specific_layout.addWidget(self.options_edit)

        note = QLabel("注：至少需要2个选项 / Note: At least 2 options required")
        note.setStyleSheet("color: #666; font-size: 10px;")
        self.specific_layout.addWidget(note)

    def _build_rating_fields(self) -> None:
        """Build UI for rating scale."""
        form = QFormLayout()

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(2, 10)
        self.scale_spin.setValue(self.dimension.get("scale", 5))
        form.addRow("评分刻度 / Scale (2-10):", self.scale_spin)

        note = QLabel("例如：5表示1-5分评分 / Example: 5 means 1-5 rating")
        note.setStyleSheet("color: #666; font-size: 10px;")
        form.addRow("", note)

        self.specific_layout.addLayout(form)

    def _build_list_fields(self) -> None:
        """Build UI for list separator."""
        form = QFormLayout()

        self.separator_edit = QLineEdit()
        self.separator_edit.setPlaceholderText("; 或 , 或其他")
        self.separator_edit.setText(self.dimension.get("separator", ";"))
        form.addRow("分隔符 / Separator:", self.separator_edit)

        note = QLabel("用于分隔多个项目的字符 / Character to separate multiple items")
        note.setStyleSheet("color: #666; font-size: 10px;")
        form.addRow("", note)

        self.specific_layout.addLayout(form)

    def _on_save(self) -> None:
        """Validate and save dimension."""
        dim_type = self.type_combo.currentData()
        key = self.key_edit.text().strip()
        column_name = self.column_edit.text().strip()
        question = self.question_edit.toPlainText().strip()

        # Validate required fields
        if not key:
            QMessageBox.warning(self, "警告 / Warning", "键名不能为空 / Key cannot be empty")
            return
        if not column_name:
            QMessageBox.warning(self, "警告 / Warning", "列名不能为空 / Column name cannot be empty")
            return
        if not question:
            QMessageBox.warning(self, "警告 / Warning", "问题不能为空 / Question cannot be empty")
            return

        # Build dimension dict
        result = {
            "type": dim_type,
            "key": key,
            "column_name": column_name,
            "question": question
        }

        # Add type-specific fields
        if dim_type in ("single_choice", "multiple_choice"):
            options_text = self.options_edit.toPlainText().strip()
            options = [line.strip() for line in options_text.split("\n") if line.strip()]
            if len(options) < 2:
                QMessageBox.warning(
                    self,
                    "警告 / Warning",
                    "选择题至少需要2个选项 / Choice questions require at least 2 options"
                )
                return
            result["options"] = options
        elif dim_type == "rating":
            result["scale"] = self.scale_spin.value()
        elif dim_type == "list":
            separator = self.separator_edit.text().strip()
            if not separator:
                QMessageBox.warning(
                    self,
                    "警告 / Warning",
                    "列表类型需要分隔符 / List type requires a separator"
                )
                return
            result["separator"] = separator

        self.result = result
        self.accept()


class DimensionsEditorDialog(QDialog):
    """Main graphical editor for managing multiple dimensions."""

    def __init__(self, parent, preset: Dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle("编辑维度配置 / Edit Dimensions")
        self.setModal(True)
        self.resize(1000, 650)

        self._original = preset or {"dimensions": []}
        self.dimensions: List[Dict[str, Any]] = list(self._original.get("dimensions", []))
        self.result: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "💡 提示：选择维度后点击编辑，或双击列表项快速编辑\n"
            "💡 Tip: Select a dimension and click Edit, or double-click to edit quickly"
        )
        instructions.setStyleSheet("background: #f0f8ff; padding: 8px; border-radius: 4px;")
        layout.addWidget(instructions)

        # Splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: dimension list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel(f"维度列表 ({len(self.dimensions)}) / Dimensions")
        list_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(list_label)

        self.dim_list = QListWidget()
        self.dim_list.itemDoubleClicked.connect(self._on_edit)
        self.dim_list.currentRowChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.dim_list)

        # Buttons
        btn_layout = QVBoxLayout()

        self.add_btn = QPushButton("➕ 添加 / Add")
        self.add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ 编辑 / Edit")
        self.edit_btn.clicked.connect(self._on_edit)
        self.edit_btn.setEnabled(False)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ 删除 / Delete")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addSpacing(10)

        self.up_btn = QPushButton("⬆️ 上移 / Up")
        self.up_btn.clicked.connect(self._on_move_up)
        self.up_btn.setEnabled(False)
        btn_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("⬇️ 下移 / Down")
        self.down_btn.clicked.connect(self._on_move_down)
        self.down_btn.setEnabled(False)
        btn_layout.addWidget(self.down_btn)

        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)

        # Right panel: preview
        right_panel = QGroupBox("维度预览 / Preview")
        right_layout = QVBoxLayout(right_panel)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        right_layout.addWidget(self.preview_text)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

        # Bottom buttons
        bottom_layout = QHBoxLayout()

        save_btn = QPushButton("💾 保存全部 / Save All")
        save_btn.clicked.connect(self._on_save_all)
        save_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        bottom_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消 / Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        bottom_layout.addStretch()

        self.count_label = QLabel("")
        bottom_layout.addWidget(self.count_label)

        layout.addLayout(bottom_layout)

        self._update_count()

    def _refresh_list(self) -> None:
        """Refresh the dimension list display."""
        self.dim_list.clear()

        for idx, dim in enumerate(self.dimensions):
            type_label = self._get_type_label(dim.get("type", "text"))
            key = dim.get("key", "unnamed")
            question = dim.get("question", "")[:50]

            display_text = f"[{type_label}] {key}\n  {question}..."
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.dim_list.addItem(item)

        self._update_count()
        self._update_preview()

    def _get_type_label(self, dim_type: str) -> str:
        """Get display label for dimension type."""
        type_map = {d[0]: d[1] for d in DimensionEditorDialog.DIMENSION_TYPES}
        return type_map.get(dim_type, dim_type)

    def _on_selection_changed(self, current_row: int) -> None:
        """Handle selection change."""
        has_selection = current_row >= 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.up_btn.setEnabled(has_selection and current_row > 0)
        self.down_btn.setEnabled(has_selection and current_row < len(self.dimensions) - 1)

        self._update_preview()

    def _update_preview(self) -> None:
        """Update preview text for selected dimension."""
        current_row = self.dim_list.currentRow()
        if current_row < 0 or current_row >= len(self.dimensions):
            self.preview_text.clear()
            return

        dim = self.dimensions[current_row]

        # Format as YAML
        import yaml
        preview = yaml.safe_dump(dim, allow_unicode=True, sort_keys=False)
        self.preview_text.setPlainText(preview)

    def _update_count(self) -> None:
        """Update dimension count label."""
        self.count_label.setText(f"总计 / Total: {len(self.dimensions)} 个维度")

    def _on_add(self) -> None:
        """Add a new dimension."""
        dialog = DimensionEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result:
            self.dimensions.append(dialog.result)
            self._refresh_list()
            # Select the new item
            self.dim_list.setCurrentRow(len(self.dimensions) - 1)

    def _on_edit(self) -> None:
        """Edit selected dimension."""
        current_row = self.dim_list.currentRow()
        if current_row < 0:
            return

        dim = self.dimensions[current_row]
        dialog = DimensionEditorDialog(self, dim)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result:
            self.dimensions[current_row] = dialog.result
            self._refresh_list()
            # Restore selection
            self.dim_list.setCurrentRow(current_row)

    def _on_delete(self) -> None:
        """Delete selected dimension."""
        current_row = self.dim_list.currentRow()
        if current_row < 0:
            return

        dim = self.dimensions[current_row]
        reply = QMessageBox.question(
            self,
            "确认删除 / Confirm Delete",
            f"确定要删除维度 '{dim.get('key', 'unnamed')}' 吗？\n"
            f"Delete dimension '{dim.get('key', 'unnamed')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.dimensions[current_row]
            self._refresh_list()
            # Try to select next item or previous
            if current_row < len(self.dimensions):
                self.dim_list.setCurrentRow(current_row)
            elif len(self.dimensions) > 0:
                self.dim_list.setCurrentRow(len(self.dimensions) - 1)

    def _on_move_up(self) -> None:
        """Move selected dimension up."""
        current_row = self.dim_list.currentRow()
        if current_row <= 0:
            return

        # Swap
        self.dimensions[current_row], self.dimensions[current_row - 1] = \
            self.dimensions[current_row - 1], self.dimensions[current_row]

        self._refresh_list()
        self.dim_list.setCurrentRow(current_row - 1)

    def _on_move_down(self) -> None:
        """Move selected dimension down."""
        current_row = self.dim_list.currentRow()
        if current_row < 0 or current_row >= len(self.dimensions) - 1:
            return

        # Swap
        self.dimensions[current_row], self.dimensions[current_row + 1] = \
            self.dimensions[current_row + 1], self.dimensions[current_row]

        self._refresh_list()
        self.dim_list.setCurrentRow(current_row + 1)

    def _on_save_all(self) -> None:
        """Save all dimensions."""
        if len(self.dimensions) == 0:
            reply = QMessageBox.question(
                self,
                "空配置 / Empty Config",
                "当前没有任何维度，确定保存空配置吗？\nNo dimensions defined. Save empty config?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.result = {"dimensions": self.dimensions}
        self.accept()
