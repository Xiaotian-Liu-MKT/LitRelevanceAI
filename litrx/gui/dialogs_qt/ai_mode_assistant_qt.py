from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPlainTextEdit, QPushButton,
    QHBoxLayout, QMessageBox, QGroupBox, QCheckBox, QScrollArea, QWidget, QSplitter
)
from PyQt6.QtCore import QObject, pyqtSignal, Qt

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
        self.resize(900, 700)
        self._config = config
        self._generator: Optional[AbstractModeGenerator] = None
        self._closed = False
        self.result: Optional[Dict[str, Any]] = None

        # Track checkboxes for criteria and questions
        self._criteria_checkboxes: List[QCheckBox] = []
        self._question_checkboxes: List[QCheckBox] = []

        # Initialize worker signals
        self._signals = WorkerSignals()
        self._signals.success.connect(self._on_generation_success)
        self._signals.error.connect(self._on_generation_error)

        self._build_ui()
        logger.debug("AIModeAssistantDialog initialized")

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)

        # Input section
        lay.addWidget(QLabel(t("ai_mode_guide") or "Describe your screening needs in natural language."))
        lay.addWidget(QLabel(t("describe_your_needs") or "Your description:"))

        # IME-friendly input
        use_plain = (os.getenv("LITRX_USE_PLAIN_TEXT_INPUT") == "1") or (sys.platform == "darwin")
        self.input_text = IMEPlainTextEdit() if use_plain else QTextEdit()
        self.input_text.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        if isinstance(self.input_text, QTextEdit):
            try:
                self.input_text.setAcceptRichText(False)
                self.input_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            except Exception:
                pass
        self.input_text.setPlaceholderText(t("describe_your_needs_placeholder") or "请在此输入中文描述…")
        self.input_text.setMaximumHeight(100)
        lay.addWidget(self.input_text)

        # Buttons
        btns = QHBoxLayout()
        self.gen_btn = QPushButton(t("generate_config") or "Generate")
        self.gen_btn.clicked.connect(self._on_generate)
        btns.addWidget(self.gen_btn)

        self.apply_btn = QPushButton(t("apply_selected") or "Apply Selected")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply)
        btns.addWidget(self.apply_btn)

        cancel_btn = QPushButton(t("cancel") or "Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        btns.addStretch()
        lay.addLayout(btns)

        # Status
        self.status = QLabel("")
        lay.addWidget(self.status)

        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Preview/Edit area
        preview_group = QGroupBox(t("preview_edit") or "预览/编辑 Preview/Edit")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(QLabel(t("preview_hint") or "您可以在此编辑生成的 JSON / You can edit the generated JSON here:"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(False)  # Allow manual editing
        preview_layout.addWidget(self.preview)
        splitter.addWidget(preview_group)

        # Right: Selection area
        selection_group = QGroupBox(t("select_items") or "选择要采纳的项 / Select Items to Apply")
        selection_layout = QVBoxLayout(selection_group)

        # Add select/deselect all buttons
        select_btns = QHBoxLayout()
        select_all_btn = QPushButton(t("select_all") or "全选 / Select All")
        select_all_btn.clicked.connect(self._select_all)
        select_btns.addWidget(select_all_btn)

        deselect_all_btn = QPushButton(t("deselect_all") or "全不选 / Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        select_btns.addWidget(deselect_all_btn)
        select_btns.addStretch()
        selection_layout.addLayout(select_btns)

        # Scrollable area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.selection_widget = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_widget)
        self.selection_layout.addStretch()
        scroll.setWidget(self.selection_widget)
        selection_layout.addWidget(scroll)

        splitter.addWidget(selection_group)

        # Set initial splitter sizes (40% preview, 60% selection)
        splitter.setSizes([400, 500])
        lay.addWidget(splitter, stretch=1)

    def showEvent(self, event):  # noqa: N802
        try:
            self.input_text.setFocus()
        except Exception:
            pass
        return super().showEvent(event)

    def _select_all(self) -> None:
        """Select all checkboxes."""
        for cb in self._criteria_checkboxes + self._question_checkboxes:
            cb.setChecked(True)

    def _deselect_all(self) -> None:
        """Deselect all checkboxes."""
        for cb in self._criteria_checkboxes + self._question_checkboxes:
            cb.setChecked(False)

    def _populate_selection_area(self, data: Dict[str, Any]) -> None:
        """Populate the selection area with checkboxes for each item."""
        # Clear existing checkboxes
        for i in reversed(range(self.selection_layout.count())):
            item = self.selection_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self._criteria_checkboxes.clear()
        self._question_checkboxes.clear()

        # Add criteria section
        if "criteria" in data and data["criteria"]:
            criteria_label = QLabel(f"<b>{t('criteria') or '筛选标准 / Criteria'}:</b>")
            self.selection_layout.addWidget(criteria_label)

            for idx, criterion in enumerate(data["criteria"]):
                cb = QCheckBox()
                cb.setChecked(True)  # Default: all selected
                question = criterion.get("question", "")
                type_info = criterion.get("type", "yes_no")
                cb.setText(f"{question} ({type_info})")
                cb.setWordWrap(True)
                self.selection_layout.addWidget(cb)
                self._criteria_checkboxes.append(cb)

        # Add questions section
        if "questions" in data and data["questions"]:
            questions_label = QLabel(f"<b>{t('additional_questions') or '附加问题 / Additional Questions'}:</b>")
            self.selection_layout.addWidget(questions_label)

            for idx, question_item in enumerate(data["questions"]):
                cb = QCheckBox()
                cb.setChecked(True)  # Default: all selected
                question = question_item.get("question", "")
                type_info = question_item.get("type", "text")
                cb.setText(f"{question} ({type_info})")
                cb.setWordWrap(True)
                self.selection_layout.addWidget(cb)
                self._question_checkboxes.append(cb)

        self.selection_layout.addStretch()

    def _get_selected_items(self) -> Optional[Dict[str, Any]]:
        """Get only the selected items from the current result."""
        if not self.result:
            return None

        # Try to parse the preview text first (in case user edited it)
        try:
            import json
            edited_data = json.loads(self.preview.toPlainText())
            # Use edited data as base
            base_data = edited_data
        except Exception:
            # Fall back to original result
            base_data = self.result

        # Filter based on checkbox selections
        filtered = {
            "mode_name": base_data.get("mode_name", ""),
            "criteria": [],
            "questions": []
        }

        # Add selected criteria
        if "criteria" in base_data and base_data["criteria"]:
            for idx, cb in enumerate(self._criteria_checkboxes):
                if cb.isChecked() and idx < len(base_data["criteria"]):
                    filtered["criteria"].append(base_data["criteria"][idx])

        # Add selected questions
        if "questions" in base_data and base_data["questions"]:
            for idx, cb in enumerate(self._question_checkboxes):
                if cb.isChecked() and idx < len(base_data["questions"]):
                    filtered["questions"].append(base_data["questions"][idx])

        return filtered

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

            # Populate selection area with checkboxes
            self._populate_selection_area(data)

            self.status.setText(t("generation_success") or "Generation succeeded. Please review and select items to apply.")
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
            QMessageBox.warning(
                self,
                t("warning") or "Warning",
                t("no_result") or "没有可应用的结果 / No result to apply"
            )
            return

        # Get selected items
        selected = self._get_selected_items()
        if not selected:
            logger.warning("Failed to get selected items")
            QMessageBox.warning(
                self,
                t("warning") or "Warning",
                t("selection_error") or "获取选择项时出错 / Error getting selected items"
            )
            return

        # Check if at least one item is selected
        if not selected.get("criteria") and not selected.get("questions"):
            QMessageBox.warning(
                self,
                t("warning") or "Warning",
                t("no_items_selected") or "请至少选择一个项目 / Please select at least one item"
            )
            return

        # Update result with selected items only
        self.result = selected
        logger.info("User clicked Apply with %d criteria and %d questions selected",
                    len(selected.get("criteria", [])), len(selected.get("questions", [])))
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
