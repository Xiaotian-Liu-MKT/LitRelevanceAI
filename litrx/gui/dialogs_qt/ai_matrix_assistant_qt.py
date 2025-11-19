from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QMessageBox
)

from ...ai_config_generator import MatrixDimensionGenerator
from ...i18n import t


class AIMatrixAssistantDialog(QDialog):
    """PyQt6 dialog for AI-assisted matrix dimension creation."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle(t("ai_matrix_assistant_title") or "AI Matrix Assistant")
        self.setModal(True)
        self.resize(820, 600)
        self._config = config
        self._generator: Optional[MatrixDimensionGenerator] = None
        self.result: Optional[List[Dict[str, Any]]] = None
        self._closed = False
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("ai_dimension_guide") or "Describe what dimensions to extract."))

        lay.addWidget(QLabel(t("describe_your_needs") or "Your description:"))
        self.input_text = QTextEdit(); lay.addWidget(self.input_text)

        btns = QHBoxLayout(); lay.addLayout(btns)
        gen_btn = QPushButton(t("generate_dimensions") or "Generate")
        gen_btn.clicked.connect(self._on_generate)
        btns.addWidget(gen_btn)

        self.apply_btn = QPushButton(t("apply_selected") or "Apply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply)
        btns.addWidget(self.apply_btn)

        cancel_btn = QPushButton(t("cancel") or "Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        self.status = QLabel("")
        lay.addWidget(self.status)

        lay.addWidget(QLabel(t("preview_label") or "Preview:"))
        self.preview = QTextEdit(); self.preview.setReadOnly(True)
        lay.addWidget(self.preview)

    def _on_generate(self) -> None:
        desc = self.input_text.toPlainText().strip()
        if not desc:
            QMessageBox.warning(self, t("warning") or "Warning", t("please_enter_description") or "Please enter a description")
            return
        self.apply_btn.setEnabled(False)
        self.status.setText(t("generating") or "Generating...")

        def worker():
            try:
                # Lazy initialization of generator to avoid crashing if API key not configured
                if self._generator is None:
                    self._generator = MatrixDimensionGenerator(self._config)

                lang = self._config.get("LANGUAGE", "zh")
                dims = self._generator.generate_dimensions(desc, lang)
                def ok():
                    if self._closed or not self.isVisible():
                        return
                    self.result = dims
                    self.preview.setPlainText(yaml_pretty({"dimensions": dims}))
                    self.status.setText(t("generation_success") or "Generation succeeded")
                    self.apply_btn.setEnabled(True)
                self._invoke(ok)
            except Exception as e:
                def err():
                    if self._closed:
                        return
                    self.status.setText(t("generation_failed") or "Generation failed")
                    error_msg = str(e)
                    if "API key" in error_msg or "not configured" in error_msg:
                        error_msg = f"{error_msg}\n\n请在主窗口配置 API 密钥。\nPlease configure API key in the main window."
                    QMessageBox.critical(self, t("error") or "Error", error_msg)
                self._invoke(err)

        threading.Thread(target=worker, daemon=True).start()

    def _on_apply(self) -> None:
        if not self.result:
            return
        self.accept()

    def _invoke(self, fn):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, fn)

    def reject(self) -> None:
        self._closed = True
        return super().reject()


def yaml_pretty(obj: Dict[str, Any]) -> str:
    try:
        import yaml
        return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)
    except Exception:
        return str(obj)
