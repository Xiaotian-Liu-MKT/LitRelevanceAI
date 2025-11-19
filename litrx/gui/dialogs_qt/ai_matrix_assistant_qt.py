from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPlainTextEdit, QPushButton,
    QHBoxLayout, QMessageBox
)

from ...ai_config_generator import MatrixDimensionGenerator
from ...i18n import t
from ..widgets.ime_text_edit import IMEPlainTextEdit


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
        # Prefer IME-friendly plain text editor (especially on macOS)
        use_plain = (os.getenv("LITRX_USE_PLAIN_TEXT_INPUT") == "1") or (sys.platform == "darwin")
        from PyQt6.QtCore import Qt
        self.input_text = IMEPlainTextEdit() if use_plain else QTextEdit()
        # Enable input method support and avoid rich text parsing
        self.input_text.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        if isinstance(self.input_text, QTextEdit):
            try:
                self.input_text.setAcceptRichText(False)
                self.input_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            except Exception:
                pass
        self.input_text.setPlaceholderText(t("describe_your_needs_placeholder") or "请在此输入中文描述…")
        lay.addWidget(self.input_text)

        btns = QHBoxLayout(); lay.addLayout(btns)
        self.gen_btn = QPushButton(t("generate_dimensions") or "Generate")
        self.gen_btn.clicked.connect(self._on_generate)
        btns.addWidget(self.gen_btn)

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

    def showEvent(self, event):  # noqa: N802
        try:
            self.input_text.setFocus()
        except Exception:
            pass
        return super().showEvent(event)

    def _on_generate(self) -> None:
        desc = self.input_text.toPlainText().strip()
        if not desc:
            QMessageBox.warning(self, t("warning") or "Warning", t("please_enter_description") or "Please enter a description")
            return
        # Disable both buttons while generating
        self.gen_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.status.setText(t("generating") or "Generating...")

        def worker():
            try:
                # Lazy initialization of generator to avoid crashing if API key not configured
                if self._generator is None:
                    self._generator = MatrixDimensionGenerator(self._config)

                lang = self._config.get("LANGUAGE", "zh")
                from ...logging_config import get_logger as _get_logger
                _log = _get_logger(__name__)
                _log.info("AIMatrixAssistant: generation started (lang=%s)", lang)
                dims = self._generator.generate_dimensions(desc, lang)
                def ok():
                    if self._closed or not self.isVisible():
                        # Re-enable button even if dialog was closed
                        if not self._closed:
                            self.gen_btn.setEnabled(True)
                        return
                    _log.info("AIMatrixAssistant: generation succeeded; updating UI")
                    self.result = dims
                    self.preview.setPlainText(yaml_pretty({"dimensions": dims}))
                    self.status.setText(t("generation_success") or "Generation succeeded")
                    self.apply_btn.setEnabled(True)
                    self.gen_btn.setEnabled(True)
                self._invoke(ok)
            except Exception as e:
                def err():
                    if self._closed:
                        return
                    self.status.setText(t("generation_failed") or "Generation failed")
                    error_msg = str(e)
                    if "API key" in error_msg or "not configured" in error_msg:
                        error_msg = f"{error_msg}\n\n请在主窗口配置 API 密钥。\nPlease configure API key in the main window."
                    if self.isVisible():
                        QMessageBox.critical(self, t("error") or "Error", error_msg)
                    # Re-enable generate button, keep apply disabled
                    self.gen_btn.setEnabled(True)
                    self.apply_btn.setEnabled(False)
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
