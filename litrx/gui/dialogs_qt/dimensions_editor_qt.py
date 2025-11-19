from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QMessageBox
)


class DimensionsEditorDialog(QDialog):
    """Simple YAML editor for matrix dimensions preset."""

    def __init__(self, parent, preset: Dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle("编辑维度（YAML） / Edit Dimensions (YAML)")
        self.setModal(True)
        self.resize(860, 640)
        self._original = preset or {"dimensions": []}
        self.result: Optional[Dict[str, Any]] = None
        self._build_ui()

    def _build_ui(self) -> None:
        import yaml
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("YAML 结构：dimensions: [ ... ]"))
        self.editor = QTextEdit()
        try:
            text = yaml.safe_dump(self._original, allow_unicode=True, sort_keys=False)
        except Exception:
            text = str(self._original)
        self.editor.setPlainText(text)
        lay.addWidget(self.editor)

        btns = QHBoxLayout(); lay.addLayout(btns)
        save_btn = QPushButton("保存 / Save")
        save_btn.clicked.connect(self._on_save)
        btns.addWidget(save_btn)
        cancel_btn = QPushButton("取消 / Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        btns.addStretch()

    def _on_save(self) -> None:
        import yaml
        text = self.editor.toPlainText()
        try:
            data = yaml.safe_load(text) or {}
            if not isinstance(data, dict):
                raise ValueError("Root must be a mapping with 'dimensions'.")
            if 'dimensions' not in data:
                raise ValueError("Missing 'dimensions' key.")
            if not isinstance(data['dimensions'], list):
                raise ValueError("'dimensions' must be a list.")
            self.result = data
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid YAML: {e}")

