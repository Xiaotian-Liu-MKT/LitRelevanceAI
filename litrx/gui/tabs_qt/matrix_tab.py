"""PyQt6-based literature matrix analysis tab."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
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
        self.stop_flag = False

    def stop(self) -> None:
        """Request the worker to stop processing."""
        self.stop_flag = True

    def run(self) -> None:
        """Run the matrix analysis (executed in background thread)."""
        try:
            self.append_log.emit("Starting matrix analysis...")

            # Process literature matrix
            results_df = process_literature_matrix(
                pdf_folder=self.pdf_folder,
                matrix_config=self.matrix_config,
                ai_config=self.config,
                metadata_file=self.metadata_file,
                progress_callback=self._progress_callback
            )

            if self.stop_flag:
                self.show_info.emit("Info", "Analysis stopped by user")
                return

            # Save results
            save_results(results_df, self.output_file)

            self.append_log.emit(f"Results saved to: {self.output_file}")
            self.show_info.emit("Success", "Matrix analysis completed successfully!")

        except Exception as e:
            self.show_error.emit("Error", f"Analysis failed: {e}")

        finally:
            self.finished_processing.emit()

    def _progress_callback(self, current: int, total: int, message: str = "") -> None:
        """Progress callback for matrix analysis (called from worker thread)."""
        if self.stop_flag:
            raise Exception("Analysis stopped by user")

        progress = (current / total * 100) if total > 0 else 0
        self.update_progress.emit(progress)

        if message:
            self.append_log.emit(f"[{current}/{total}] {message}")


class MatrixTab(QWidget):
    """Tab for Literature Matrix Analysis."""

    def __init__(self, parent: BaseWindow) -> None:
        super().__init__()
        self.parent_window = parent

        # Worker thread and data
        self.worker: Optional[MatrixAnalysisWorker] = None
        self.matrix_config: Dict[str, Any] = {}
        self.default_config_path = Path(__file__).resolve().parents[3] / "configs" / "matrix" / "default.yaml"

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Configuration Section
        config_group = QGroupBox(t("matrix_config"))
        config_layout = QVBoxLayout()

        self.dim_count_label = QLabel(t("current_dimensions", count=0))
        config_layout.addWidget(self.dim_count_label)

        btn_layout = QHBoxLayout()
        self.edit_dim_btn = QPushButton(f"✏️ {t('edit_dimensions')}")
        self.edit_dim_btn.clicked.connect(self._open_dimensions_editor)
        btn_layout.addWidget(self.edit_dim_btn)

        self.ai_dims_btn = QPushButton(f"🤖 {t('ai_generate_dims')}")
        self.ai_dims_btn.clicked.connect(self._open_ai_dims)
        btn_layout.addWidget(self.ai_dims_btn)

        self.import_config_btn = QPushButton(f"📥 {t('import_config')}")
        self.import_config_btn.clicked.connect(self._import_config)
        btn_layout.addWidget(self.import_config_btn)

        self.export_config_btn = QPushButton(f"📤 {t('export_config')}")
        self.export_config_btn.clicked.connect(self._export_config)
        btn_layout.addWidget(self.export_config_btn)

        self.save_preset_btn = QPushButton(f"💾 {t('save_preset')}")
        self.save_preset_btn.clicked.connect(self._save_as_preset)
        btn_layout.addWidget(self.save_preset_btn)

        self.reset_btn = QPushButton(f"🔄 {t('reset_default')}")
        self.reset_btn.clicked.connect(self._reset_config)
        btn_layout.addWidget(self.reset_btn)

        config_layout.addLayout(btn_layout)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

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

        # Load default config
        self._load_default_config()

        # Register for language change notifications
        get_i18n().add_observer(self.update_language)

    def update_language(self) -> None:
        """Update UI text when language changes."""
        # Update dimension count label
        dim_count = len(self.matrix_config.get("dimensions", []))
        self.dim_count_label.setText(t("current_dimensions", count=dim_count))

        # Update buttons
        self.edit_dim_btn.setText(f"✏️ {t('edit_dimensions')}")
        self.ai_dims_btn.setText(f"🤖 {t('ai_generate_dims')}")
        self.import_config_btn.setText(f"📥 {t('import_config')}")
        self.export_config_btn.setText(f"📤 {t('export_config')}")
        self.save_preset_btn.setText(f"💾 {t('save_preset')}")
        self.reset_btn.setText(f"🔄 {t('reset_default')}")

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

    def _load_default_config(self) -> None:
        """Load default matrix configuration."""
        try:
            self.matrix_config = load_matrix_config(str(self.default_config_path))
            dim_count = len(self.matrix_config.get("dimensions", []))
            self.dim_count_label.setText(t("current_dimensions", count=dim_count))
        except Exception as e:
            logger.warning(f"Failed to load default config: {e}")

    def _import_config(self) -> None:
        """Import matrix configuration from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("import_config"),
            "",
            "YAML (*.yaml *.yml)"
        )
        if file_path:
            try:
                self.matrix_config = load_matrix_config(file_path)
                dim_count = len(self.matrix_config.get("dimensions", []))
                self.dim_count_label.setText(t("current_dimensions", count=dim_count))
                QMessageBox.information(self, t("success"), t("saved"))
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))

    def _export_config(self) -> None:
        """Export current matrix configuration."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_config"),
            "",
            "YAML (*.yaml)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(self.matrix_config, f, allow_unicode=True)
                QMessageBox.information(self, t("success"), t("saved"))
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))

    def _reset_config(self) -> None:
        """Reset to default configuration."""
        reply = QMessageBox.question(
            self,
            t("confirm"),
            t("reset_prompt_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._load_default_config()

    def _open_dimensions_editor(self) -> None:
        """Open graphical editor for current dimensions."""
        dlg = DimensionsEditorDialog(self, self.matrix_config or {"dimensions": []})
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result:
            self.matrix_config = dlg.result
            dim_count = len(self.matrix_config.get("dimensions", []))
            self.dim_count_label.setText(t("current_dimensions", count=dim_count))

    def _save_as_preset(self) -> None:
        """Save current config as a preset YAML file."""
        # Suggest default directory and filename under configs/matrix
        from ...resources import resource_path
        from datetime import datetime
        default_dir = resource_path('configs', 'matrix')
        suggested = str(default_dir / f"preset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save as Preset",
            suggested,
            "YAML (*.yaml)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(self.matrix_config or {"dimensions": []}, f, allow_unicode=True, sort_keys=False)
                QMessageBox.information(self, t("success") or "Success", t("saved") or "Saved")
            except Exception as e:
                QMessageBox.critical(self, t("error") or "Error", str(e))

    def _open_ai_dims(self) -> None:
        """Open AI assistant to generate dimensions and merge into current config."""
        from PyQt6.QtWidgets import QDialog
        dlg = AIMatrixAssistantDialog(self, self.parent_window.build_config())
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result:
            dims = self.matrix_config.get('dimensions', []) or []
            dims.extend(dlg.result)
            self.matrix_config['dimensions'] = dims
            dim_count = len(self.matrix_config.get("dimensions", []))
            self.dim_count_label.setText(t("current_dimensions", count=dim_count))

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
            QMessageBox.critical(self, t("error"), t("error_fill_fields"))
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
