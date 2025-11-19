"""PyQt6-based literature matrix analysis tab with user-friendly scheme management."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

import pandas as pd
import yaml

from ...matrix_analyzer import (
    load_matrix_config,
    process_literature_matrix,
    save_results,
)
from ...i18n import get_i18n, t
from ...logging_config import get_logger
from ...preset_manager import MatrixPresetManager
from ..dialogs_qt.ai_matrix_assistant_qt import AIMatrixAssistantDialog
from ..dialogs_qt.dimensions_editor_qt_v2 import DimensionsEditorDialog

if TYPE_CHECKING:
    from ..base_window_qt import BaseWindow

logger = get_logger(__name__)


class MatrixAnalysisWorker(QThread):
    """Worker thread for literature matrix analysis processing.

    This QThread-based worker handles matrix analysis in the background,
    emitting signals for thread-safe UI updates.
    """

    # Signals for thread-safe communication with main thread
    update_progress = pyqtSignal(float)  # progress percentage
    append_log = pyqtSignal(str)  # log text to append
    show_error = pyqtSignal(str, str)  # title, message
    show_info = pyqtSignal(str, str)  # title, message
    finished_processing = pyqtSignal()  # Emitted when done (success or cancelled)

    def __init__(
        self,
        config: Dict,
        pdf_folder: str,
        metadata_file: Optional[str],
        output_file: str,
        matrix_config: Dict
    ):
        """Initialize the worker.

        Args:
            config: AI configuration dictionary
            pdf_folder: Path to PDF folder
            metadata_file: Optional path to metadata file
            output_file: Path to output file
            matrix_config: Matrix dimension configuration
        """
        super().__init__()
        self.config = config
        self.pdf_folder = pdf_folder
        self.metadata_file = metadata_file
        self.output_file = output_file
        self.matrix_config = matrix_config
        self.stop_event = threading.Event()

    def stop(self) -> None:
        """Request the worker to stop processing."""
        self.stop_event.set()
        self.append_log.emit("Stopping analysis...")

    def run(self) -> None:
        """Run the matrix analysis (executed in background thread)."""
        try:
            self.append_log.emit("开始矩阵分析...")

            # Log optimization settings
            max_workers = self.config.get('MAX_WORKERS', 4)
            enable_cache = self.config.get('ENABLE_CACHE', True)
            enable_checkpoints = self.config.get('ENABLE_PROGRESS_CHECKPOINTS', True)

            self.append_log.emit(f"并发线程数: {max_workers}")
            self.append_log.emit(f"结果缓存: {'启用' if enable_cache else '禁用'}")
            self.append_log.emit(f"断点续传: {'启用' if enable_checkpoints else '禁用'}")

            # Process literature matrix with new optimized function
            results_df, mapping_df = process_literature_matrix(
                pdf_folder=self.pdf_folder,
                metadata_path=self.metadata_file,
                matrix_config=self.matrix_config,
                app_config=self.config,
                progress_callback=self._progress_callback,
                status_callback=self._status_callback,
                stop_event=self.stop_event
            )

            if self.stop_event.is_set():
                self.show_info.emit(t("info"), "分析已被用户停止")
                return

            # Prepare output configuration
            output_config = {
                'file_suffix': self.config.get('OUTPUT_FILE_SUFFIX', '_literature_matrix'),
                'file_type': self.config.get('OUTPUT_FILE_TYPE', 'xlsx')
            }

            # Save results
            output_path = save_results(
                results_df,
                mapping_df,
                self.pdf_folder,
                output_config
            )

            self.append_log.emit(f"结果已保存到: {output_path}")
            self.show_info.emit(t("success"), "矩阵分析成功完成！")

        except KeyboardInterrupt:
            self.show_info.emit(t("info"), "分析已被用户停止")

        except Exception as e:
            logger.error(f"Matrix analysis failed: {e}", exc_info=True)
            self.show_error.emit(t("error"), f"分析失败: {e}")

        finally:
            self.finished_processing.emit()

    def _progress_callback(self, current: int, total: int) -> None:
        """Progress callback for matrix analysis (called from worker thread)."""
        progress = (current / total * 100) if total > 0 else 0
        self.update_progress.emit(progress)

    def _status_callback(self, pdf_name: str, status: str) -> None:
        """Status callback for individual PDF processing."""
        self.append_log.emit(f"[{pdf_name}] {status}")


class MatrixTab(QWidget):
    """Tab for Literature Matrix Analysis with user-friendly scheme management.

    Simplified UI with 4 main controls:
    1. Scheme selector (ComboBox)
    2. Edit button
    3. AI button
    4. More menu (⋮)
    """

    def __init__(self, parent: BaseWindow) -> None:
        super().__init__()
        self.parent_window = parent

        # Worker thread and data
        self.worker: Optional[MatrixAnalysisWorker] = None
        self.matrix_config: Dict[str, Any] = {}
        self.current_scheme_key: str = "default"

        # Initialize preset manager
        self.preset_manager = MatrixPresetManager()

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Scheme Management Section (Simplified)
        scheme_group = QGroupBox(t("analysis_scheme"))
        scheme_layout = QVBoxLayout()

        # First row: scheme selector + buttons
        control_layout = QHBoxLayout()

        # Scheme selector (ComboBox)
        self.scheme_combo = QComboBox()
        self.scheme_combo.setMinimumWidth(200)
        self.scheme_combo.currentIndexChanged.connect(self._on_scheme_changed)
        control_layout.addWidget(self.scheme_combo)

        # Edit button
        self.edit_btn = QPushButton(t("edit_dimensions"))
        self.edit_btn.setToolTip("编辑当前方案的分析维度")
        self.edit_btn.clicked.connect(self._open_dimensions_editor)
        control_layout.addWidget(self.edit_btn)

        # AI button
        self.ai_btn = QPushButton(t("ai_generate_dims"))
        self.ai_btn.setToolTip("使用AI生成分析维度")
        self.ai_btn.clicked.connect(self._open_ai_dims)
        control_layout.addWidget(self.ai_btn)

        # More menu button (⋮)
        self.more_btn = QPushButton(t("more_options"))
        self.more_btn.setToolTip("更多选项")
        self.more_btn.clicked.connect(self._show_more_menu)
        control_layout.addWidget(self.more_btn)

        control_layout.addStretch()
        scheme_layout.addLayout(control_layout)

        # Second row: dimension count status
        self.dim_count_label = QLabel("")
        self.dim_count_label.setStyleSheet("color: #666;")
        scheme_layout.addWidget(self.dim_count_label)

        scheme_group.setLayout(scheme_layout)
        layout.addWidget(scheme_group)

        # Data Input Section
        input_group = QGroupBox(t("data_input"))
        input_layout = QVBoxLayout()

        # PDF folder
        self.folder_label = QLabel(t("pdf_folder_required"))
        input_layout.addWidget(self.folder_label)

        folder_layout = QHBoxLayout()
        self.folder_entry = QLineEdit()
        folder_layout.addWidget(self.folder_entry)

        self.browse_folder_btn = QPushButton(t("browse"))
        self.browse_folder_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.browse_folder_btn)

        input_layout.addLayout(folder_layout)

        # Metadata file
        self.meta_label = QLabel(t("metadata_file_optional"))
        input_layout.addWidget(self.meta_label)

        meta_layout = QHBoxLayout()
        self.meta_entry = QLineEdit()
        meta_layout.addWidget(self.meta_entry)

        self.browse_meta_btn = QPushButton(t("browse"))
        self.browse_meta_btn.clicked.connect(self._browse_meta)
        meta_layout.addWidget(self.browse_meta_btn)

        input_layout.addLayout(meta_layout)

        # Output file
        self.output_label = QLabel(t("output_file_required"))
        input_layout.addWidget(self.output_label)

        output_layout = QHBoxLayout()
        self.output_entry = QLineEdit()
        output_layout.addWidget(self.output_entry)

        self.browse_output_btn = QPushButton(t("browse"))
        self.browse_output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.browse_output_btn)

        input_layout.addLayout(output_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Action buttons
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton(f"🚀 {t('start_analysis')}")
        self.start_btn.clicked.connect(self.start_analysis)
        action_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(f"⏹️ {t('stop')}")
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.setEnabled(False)
        action_layout.addWidget(self.stop_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Log
        self.log_label = QLabel(t("processing_log"))
        layout.addWidget(self.log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)

        # Initialize: load schemes and default config
        self._load_schemes()
        self._load_scheme(self.current_scheme_key)

        # Register for language change notifications
        get_i18n().add_observer(self.update_language)

    def update_language(self) -> None:
        """Update UI text when language changes."""
        # Update dimension count label
        self._update_dimension_count_label()

        # Update buttons
        self.edit_btn.setText(t("edit_dimensions"))
        self.ai_btn.setText(t("ai_generate_dims"))
        self.more_btn.setText(t("more_options"))

        # Update labels
        self.folder_label.setText(t("pdf_folder_required"))
        self.meta_label.setText(t("metadata_file_optional"))
        self.output_label.setText(t("output_file_required"))

        # Update action buttons
        self.start_btn.setText(f"🚀 {t('start_analysis')}")
        self.stop_btn.setText(f"⏹️ {t('stop')}")
        self.browse_folder_btn.setText(t("browse"))
        self.browse_meta_btn.setText(t("browse"))
        self.browse_output_btn.setText(t("browse"))

        # Update log label
        self.log_label.setText(t("processing_log"))

    def _load_schemes(self) -> None:
        """Load all available schemes into the combo box."""
        self.scheme_combo.clear()

        # Get list of schemes
        schemes = self.preset_manager.list_presets()

        # Add schemes to combo box
        for scheme_key, display_name in schemes:
            self.scheme_combo.addItem(display_name, scheme_key)

        # Add separator and "New scheme" option
        self.scheme_combo.insertSeparator(self.scheme_combo.count())
        self.scheme_combo.addItem(t("new_scheme"), "__new__")

        # Select current scheme
        index = self.scheme_combo.findData(self.current_scheme_key)
        if index >= 0:
            self.scheme_combo.setCurrentIndex(index)

        logger.info(f"Loaded {len(schemes)} schemes")

    def _load_scheme(self, scheme_key: str) -> None:
        """Load a scheme configuration.

        Args:
            scheme_key: Scheme file name (without extension)
        """
        try:
            self.matrix_config = self.preset_manager.load_preset(scheme_key)
            self.current_scheme_key = scheme_key
            self._update_dimension_count_label()
            logger.info(f"Loaded scheme: {scheme_key}")
        except Exception as e:
            logger.error(f"Failed to load scheme: {e}")
            QMessageBox.critical(self, t("error"), str(e))

    def _save_current_scheme(self, show_message: bool = False) -> None:
        """Save current configuration to current scheme (auto-save).

        Args:
            show_message: Whether to show success message
        """
        if not self.current_scheme_key:
            return

        try:
            # Get display name for this scheme
            index = self.scheme_combo.findData(self.current_scheme_key)
            display_name = self.scheme_combo.itemText(index) if index >= 0 else self.current_scheme_key

            # Save scheme
            self.preset_manager.save_preset(
                self.current_scheme_key,
                self.matrix_config,
                display_name
            )

            if show_message:
                # Show brief toast-style message in status bar
                self._append_log(t("scheme_auto_saved"))

            logger.info(f"Auto-saved scheme: {self.current_scheme_key}")

        except Exception as e:
            logger.error(f"Failed to save scheme: {e}")
            if show_message:
                QMessageBox.critical(self, t("error"), str(e))

    def _update_dimension_count_label(self) -> None:
        """Update the dimension count status label."""
        dim_count = len(self.matrix_config.get("dimensions", []))
        self.dim_count_label.setText(t("current_dimensions", count=dim_count))

    def _on_scheme_changed(self, index: int) -> None:
        """Handle scheme selection change.

        Args:
            index: Selected combo box index
        """
        scheme_key = self.scheme_combo.itemData(index)

        # Handle "New scheme" option
        if scheme_key == "__new__":
            self._create_new_scheme()
            # Reset combo box to previous selection
            prev_index = self.scheme_combo.findData(self.current_scheme_key)
            if prev_index >= 0:
                self.scheme_combo.setCurrentIndex(prev_index)
            return

        # Load selected scheme
        if scheme_key and scheme_key != self.current_scheme_key:
            self._load_scheme(scheme_key)

    def _create_new_scheme(self) -> None:
        """Create a new scheme (dialog workflow)."""
        # Ask for scheme name
        name, ok = QInputDialog.getText(
            self,
            t("create_new_scheme"),
            t("enter_scheme_name")
        )

        if not ok or not name.strip():
            return

        name = name.strip()

        # Generate unique key from name
        try:
            scheme_key = self.preset_manager.generate_unique_key(name)

            # Create empty scheme (copy from default)
            default_config = self.preset_manager.load_preset("default")

            # Save new scheme
            self.preset_manager.save_preset(scheme_key, default_config, name)

            # Reload schemes list
            self._load_schemes()

            # Select new scheme
            index = self.scheme_combo.findData(scheme_key)
            if index >= 0:
                self.scheme_combo.setCurrentIndex(index)

            QMessageBox.information(self, t("success"), t("scheme_saved"))

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _duplicate_current_scheme(self) -> None:
        """Duplicate the current scheme."""
        # Ask for new name
        current_name = self.scheme_combo.currentText()
        new_name, ok = QInputDialog.getText(
            self,
            t("duplicate_scheme"),
            t("enter_scheme_name"),
            text=f"{current_name} (副本)"
        )

        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        try:
            # Generate unique key
            new_key = self.preset_manager.generate_unique_key(new_name)

            # Duplicate scheme
            self.preset_manager.duplicate_preset(
                self.current_scheme_key,
                new_key,
                new_name
            )

            # Reload schemes
            self._load_schemes()

            # Select new scheme
            index = self.scheme_combo.findData(new_key)
            if index >= 0:
                self.scheme_combo.setCurrentIndex(index)

            QMessageBox.information(self, t("success"), t("scheme_saved"))

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _rename_current_scheme(self) -> None:
        """Rename the current scheme."""
        if self.current_scheme_key == "default":
            QMessageBox.warning(self, t("warning"), t("cannot_delete_default"))
            return

        # Ask for new name
        current_name = self.scheme_combo.currentText()
        new_name, ok = QInputDialog.getText(
            self,
            t("rename_scheme"),
            t("enter_new_name"),
            text=current_name
        )

        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        try:
            # Generate new key
            new_key = self.preset_manager.generate_unique_key(new_name)

            # Rename scheme
            self.preset_manager.rename_preset(
                self.current_scheme_key,
                new_key,
                new_name
            )

            # Update current key
            self.current_scheme_key = new_key

            # Reload schemes
            self._load_schemes()

            QMessageBox.information(self, t("success"), t("scheme_saved"))

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _delete_current_scheme(self) -> None:
        """Delete the current scheme."""
        if self.current_scheme_key == "default":
            QMessageBox.warning(self, t("warning"), t("cannot_delete_default"))
            return

        # Confirm deletion
        current_name = self.scheme_combo.currentText()
        reply = QMessageBox.question(
            self,
            t("confirm"),
            t("confirm_delete_scheme", name=current_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Delete scheme
            self.preset_manager.delete_preset(self.current_scheme_key)

            # Switch to default scheme
            self.current_scheme_key = "default"
            self._load_schemes()
            self._load_scheme("default")

            QMessageBox.information(self, t("success"), t("scheme_deleted"))

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _load_from_file(self) -> None:
        """Import scheme from YAML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("load_from_file"),
            "",
            "YAML (*.yaml *.yml)"
        )

        if not file_path:
            return

        try:
            # Load config from file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Update current config
            self.matrix_config = config

            # Auto-save to current scheme
            self._save_current_scheme(show_message=True)

            # Update UI
            self._update_dimension_count_label()

            QMessageBox.information(self, t("success"), t("scheme_loaded"))

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _save_to_file(self) -> None:
        """Export current scheme to YAML file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("save_to_file"),
            "",
            "YAML (*.yaml)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.matrix_config, f, allow_unicode=True, sort_keys=False)

            QMessageBox.information(self, t("success"), t("scheme_saved"))

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _restore_default_template(self) -> None:
        """Restore default template configuration."""
        reply = QMessageBox.question(
            self,
            t("confirm"),
            t("reset_prompt_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Load default config
            default_config = self.preset_manager.load_preset("default")

            # Update current config
            self.matrix_config = default_config

            # Auto-save to current scheme
            self._save_current_scheme(show_message=True)

            # Update UI
            self._update_dimension_count_label()

            QMessageBox.information(self, t("success"), t("scheme_loaded"))

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _show_more_menu(self) -> None:
        """Show the 'More' options menu."""
        menu = QMenu(self)

        # Add actions
        menu.addAction(t("create_new_scheme"), self._create_new_scheme)
        menu.addAction(t("duplicate_scheme"), self._duplicate_current_scheme)
        menu.addAction(t("rename_scheme"), self._rename_current_scheme)
        menu.addAction(t("delete_scheme"), self._delete_current_scheme)

        menu.addSeparator()

        menu.addAction(t("load_from_file"), self._load_from_file)
        menu.addAction(t("save_to_file"), self._save_to_file)

        menu.addSeparator()

        menu.addAction(t("restore_default_template"), self._restore_default_template)

        # Show menu at button position
        menu.exec(self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft()))

    def _open_dimensions_editor(self) -> None:
        """Open graphical editor for current dimensions."""
        dlg = DimensionsEditorDialog(self, self.matrix_config or {"dimensions": []})
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result:
            self.matrix_config = dlg.result

            # Auto-save
            self._save_current_scheme(show_message=True)

            # Update UI
            self._update_dimension_count_label()

    def _open_ai_dims(self) -> None:
        """Open AI assistant to generate dimensions and merge into current config."""
        dlg = AIMatrixAssistantDialog(self, self.parent_window.build_config())
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result:
            # Merge new dimensions
            dims = self.matrix_config.get('dimensions', []) or []
            dims.extend(dlg.result)
            self.matrix_config['dimensions'] = dims

            # Auto-save
            self._save_current_scheme(show_message=True)

            # Update UI
            self._update_dimension_count_label()

    def _browse_folder(self) -> None:
        """Browse for PDF folder."""
        folder_path = QFileDialog.getExistingDirectory(self, t("browse"))
        if folder_path:
            self.folder_entry.setText(folder_path)

    def _browse_meta(self) -> None:
        """Browse for metadata file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("browse"),
            "",
            "CSV or Excel (*.csv *.xlsx)"
        )
        if file_path:
            self.meta_entry.setText(file_path)

    def _browse_output(self) -> None:
        """Browse for output file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("browse"),
            "",
            "Excel (*.xlsx)"
        )
        if file_path:
            self.output_entry.setText(file_path)

    def start_analysis(self) -> None:
        """Start matrix analysis using QThread worker."""
        pdf_folder = self.folder_entry.text().strip()
        output_file = self.output_entry.text().strip()

        if not pdf_folder or not output_file:
            QMessageBox.critical(self, t("error"), "请填写所有必填字段")
            return

        # Initialize UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        # Create and configure worker thread
        config = self.parent_window.build_config()
        metadata_file = self.meta_entry.text().strip() or None
        self.worker = MatrixAnalysisWorker(
            config, pdf_folder, metadata_file, output_file, self.matrix_config
        )

        # Connect worker signals to UI update slots
        self.worker.update_progress.connect(self._update_progress)
        self.worker.append_log.connect(self._append_log)
        self.worker.show_error.connect(self._show_error)
        self.worker.show_info.connect(self._show_info)
        self.worker.finished_processing.connect(self._on_worker_finished)

        # Start the worker thread
        self.worker.start()

    def stop_analysis(self) -> None:
        """Stop the analysis process."""
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self._append_log("Stopping...")

    def _on_worker_finished(self) -> None:
        """Called when worker thread finishes (success or cancelled)."""
        # Restore button states
        self._restore_buttons()

        # Clean up worker reference
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _update_progress(self, value: float) -> None:
        """Update progress bar."""
        self.progress_bar.setValue(int(value))

    def _append_log(self, text: str) -> None:
        """Append text to log."""
        self.log_text.append(text)

    def _show_error(self, title: str, message: str) -> None:
        """Show error message."""
        QMessageBox.critical(self, title, message)

    def _show_info(self, title: str, message: str) -> None:
        """Show info message."""
        QMessageBox.information(self, title, message)

    def _restore_buttons(self) -> None:
        """Restore button states."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
