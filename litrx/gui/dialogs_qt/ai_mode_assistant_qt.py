from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QMessageBox
)

from ...ai_config_generator import AbstractModeGenerator
from ...i18n import t


class AIModeAssistantDialog(QDialog):
    """PyQt6 dialog for AI-assisted abstract mode creation."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle(t("ai_mode_assistant_title") or "AI Mode Assistant")
        self.setModal(True)
        self.resize(760, 560)
        self._config = config
        self._generator = AbstractModeGenerator(config)
        self.result: Optional[Dict[str, Any]] = None
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("ai_mode_guide") or "Describe your screening needs in natural language."))

        lay.addWidget(QLabel(t("describe_your_needs") or "Your description:"))
        self.input_text = QTextEdit()
        lay.addWidget(self.input_text)

        btns = QHBoxLayout()
        self.gen_btn = QPushButton(t("generate_config") or "Generate")
        self.gen_btn.clicked.connect(self._on_generate)
        btns.addWidget(self.gen_btn)

        self.apply_btn = QPushButton(t("apply_changes") or "Apply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply)
        btns.addWidget(self.apply_btn)

        cancel_btn = QPushButton(t("cancel") or "Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        btns.addStretch()
        lay.addLayout(btns)

        self.status = QLabel("")
        lay.addWidget(self.status)

        lay.addWidget(QLabel(t("preview_label") or "Preview:"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        lay.addWidget(self.preview)

    def _on_generate(self) -> None:
        desc = self.input_text.toPlainText().strip()
        if not desc:
            QMessageBox.warning(self, t("warning") or "Warning", t("please_enter_description") or "Please enter a description")
            return
        self.gen_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.status.setText(t("generating") or "Generating...")

        def worker():
            try:
                lang = self._config.get("LANGUAGE", "zh")
                data = self._generator.generate_mode(desc, lang)
                def ok():
                    self.result = data
                    self.preview.setPlainText(json_pretty(data))
                    self.status.setText(t("generation_success") or "Generation succeeded")
                    self.apply_btn.setEnabled(True)
                    self.gen_btn.setEnabled(True)
                self._invoke(ok)
            except Exception as e:
                def err():
                    self.status.setText(t("generation_failed") or "Generation failed")
                    QMessageBox.critical(self, t("error") or "Error", str(e))
                    self.gen_btn.setEnabled(True)
                self._invoke(err)

        threading.Thread(target=worker, daemon=True).start()

    def _on_apply(self) -> None:
        if not self.result:
            return
        self.accept()

    def _invoke(self, fn):
        # simple helper to marshal to UI thread
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, fn)


def json_pretty(obj: Dict[str, Any]) -> str:
    import json
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)

