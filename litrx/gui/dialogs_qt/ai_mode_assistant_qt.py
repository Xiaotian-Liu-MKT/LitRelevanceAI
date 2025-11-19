from __future__ import annotations

import threading
from typing import Any, Dict, Optional

import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPlainTextEdit, QPushButton,
    QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import QObject, pyqtSignal

from ...ai_config_generator import AbstractModeGenerator
from ...i18n import t
from ..widgets.ime_text_edit import IMEPlainTextEdit
from ...logging_config import get_logger

logger = get_logger(__name__)


class WorkerSignals(QObject):
    """Signals for worker thread to communicate with UI thread."""
    success = pyqtSignal(dict)  # Emits generated config data
    error = pyqtSignal(str)     # Emits error message


class AIModeAssistantDialog(QDialog):
    """PyQt6 dialog for AI-assisted abstract mode creation."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle(t("ai_mode_assistant_title") or "AI Mode Assistant")
        self.setModal(True)
        self.resize(760, 560)
        self._config = config
        self._generator: Optional[AbstractModeGenerator] = None
        self._closed = False
        self.result: Optional[Dict[str, Any]] = None

        # Initialize worker signals
        self._signals = WorkerSignals()
        self._signals.success.connect(self._on_generation_success)
        self._signals.error.connect(self._on_generation_error)

        self._build_ui()
        logger.debug("AIModeAssistantDialog initialized")

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("ai_mode_guide") or "Describe your screening needs in natural language."))

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

        logger.info("User clicked Generate button, description length=%d", len(desc))
        self.gen_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.status.setText(t("generating") or "Generating...")

        def worker():
            try:
                logger.info("Worker thread started for AI mode generation")

                # Lazy initialization of generator to avoid crashing if API key not configured
                if self._generator is None:
                    logger.debug("Lazy initializing AbstractModeGenerator")
                    self._generator = AbstractModeGenerator(self._config)

                lang = self._config.get("LANGUAGE", "zh")
                logger.info("AIModeAssistant: generation started (lang=%s)", lang)

                # Call the generator
                data = self._generator.generate_mode(desc, lang)

                logger.info("AIModeAssistant: generator returned, data type=%s", type(data).__name__)

                # Validate data before emitting
                if not isinstance(data, dict):
                    raise TypeError(f"Expected dict from generator, got {type(data).__name__}")

                # Emit success signal to UI thread
                logger.info("Emitting success signal to UI thread")
                self._signals.success.emit(data)

            except Exception as e:
                logger.error("Worker thread caught exception: %s", e, exc_info=True)
                error_msg = str(e)

                # Provide helpful message for API key issues
                if "API key" in error_msg or "not configured" in error_msg:
                    error_msg = f"{error_msg}\n\n请在主窗口配置 API 密钥。\nPlease configure API key in the main window."

                # Emit error signal to UI thread
                logger.info("Emitting error signal to UI thread")
                self._signals.error.emit(error_msg)

        threading.Thread(target=worker, daemon=True).start()
        logger.debug("Worker thread launched")

    def _on_generation_success(self, data: Dict[str, Any]) -> None:
        """Handle successful generation in UI thread (slot connected to signal)."""
        try:
            logger.info("_on_generation_success called in UI thread")

            if self._closed or not self.isVisible():
                logger.warning("Dialog closed or not visible, skipping UI update")
                if not self._closed:
                    self.gen_btn.setEnabled(True)
                return

            logger.info("Updating UI with generated data")
            self.result = data

            # Safely format JSON for preview
            try:
                preview_text = json_pretty(data)
                logger.debug("JSON preview generated, length=%d", len(preview_text))
            except Exception as e:
                logger.error("Failed to format JSON for preview: %s", e, exc_info=True)
                preview_text = str(data)

            self.preview.setPlainText(preview_text)
            self.status.setText(t("generation_success") or "Generation succeeded")
            self.apply_btn.setEnabled(True)
            self.gen_btn.setEnabled(True)

            logger.info("UI update completed successfully")

        except Exception as e:
            logger.error("Exception in _on_generation_success: %s", e, exc_info=True)
            self.status.setText(t("generation_failed") or "Generation failed")
            QMessageBox.critical(
                self,
                t("error") or "Error",
                f"UI 更新时发生错误: {e}\nError updating UI: {e}"
            )
            self.gen_btn.setEnabled(True)
            self.apply_btn.setEnabled(False)

    def _on_generation_error(self, error_msg: str) -> None:
        """Handle generation error in UI thread (slot connected to signal)."""
        try:
            logger.info("_on_generation_error called in UI thread")

            if self._closed:
                logger.warning("Dialog closed, skipping error display")
                return

            self.status.setText(t("generation_failed") or "Generation failed")

            if self.isVisible():
                QMessageBox.critical(self, t("error") or "Error", error_msg)

            self.gen_btn.setEnabled(True)
            self.apply_btn.setEnabled(False)

            logger.info("Error handling completed")

        except Exception as e:
            logger.error("Exception in _on_generation_error: %s", e, exc_info=True)

    def _on_apply(self) -> None:
        if not self.result:
            logger.warning("Apply clicked but no result available")
            return
        logger.info("User clicked Apply, accepting dialog")
        self.accept()

    def reject(self) -> None:
        # mark closed to avoid unsafe UI updates from worker
        logger.info("Dialog rejected/closed by user")
        self._closed = True
        return super().reject()


def json_pretty(obj: Dict[str, Any]) -> str:
    import json
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)
