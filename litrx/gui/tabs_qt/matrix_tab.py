"""PyQt6-based literature matrix analysis tab."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
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
from ..dialogs_qt.ai_matrix_assistant_qt import AIMatrixAssistantDialog
from ..dialogs_qt.dimensions_editor_qt_v2 import DimensionsEditorDialog

if TYPE_CHECKING:
    from ..base_window_qt import BaseWindow


class MatrixTab(QWidget):
    """Tab for Literature Matrix Analysis."""

    # Signals for thread-safe UI updates
    update_progress_signal = pyqtSignal(float)
    append_log_signal = pyqtSignal(str)
    show_error_signal = pyqtSignal(str, str)
    show_info_signal = pyqtSignal(str, str)
    restore_buttons_signal = pyqtSignal()

    def __init__(self, parent: BaseWindow) -> None:
        super().__init__()
        self.parent_window = parent

        # Data
        self.matrix_config: Dict[str, Any] = {}
        self.default_config_path = Path(__file__).resolve().parents[3] / "configs" / "matrix" / "default.yaml"
        self.stop_flag = False

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Configuration Section
        config_group = QGroupBox("矩阵配置 / Matrix Configuration")
        config_layout = QVBoxLayout()

        self.dim_count_label = QLabel("当前维度数：0 / Current Dimensions: 0")
        config_layout.addWidget(self.dim_count_label)

        btn_layout = QHBoxLayout()
        self.edit_dim_btn = QPushButton("✏️ 编辑维度 / Edit Dimensions")
        self.edit_dim_btn.clicked.connect(self._open_dimensions_editor)
        btn_layout.addWidget(self.edit_dim_btn)

        self.ai_dims_btn = QPushButton("🤖 AI 生成维度 / AI Dims")
        self.ai_dims_btn.clicked.connect(self._open_ai_dims)
        btn_layout.addWidget(self.ai_dims_btn)

        self.import_config_btn = QPushButton("📥 导入配置 / Import Config")
        self.import_config_btn.clicked.connect(self._import_config)
        btn_layout.addWidget(self.import_config_btn)

        self.export_config_btn = QPushButton("📤 导出配置 / Export Config")
        self.export_config_btn.clicked.connect(self._export_config)
        btn_layout.addWidget(self.export_config_btn)

        self.save_preset_btn = QPushButton("💾 另存为 Preset / Save as Preset")
        self.save_preset_btn.clicked.connect(self._save_as_preset)
        btn_layout.addWidget(self.save_preset_btn)

        self.reset_btn = QPushButton("🔄 重置默认 / Reset Default")
        self.reset_btn.clicked.connect(self._reset_config)
        btn_layout.addWidget(self.reset_btn)

        config_layout.addLayout(btn_layout)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Data Input Section
        input_group = QGroupBox("数据输入 / Data Input")
        input_layout = QVBoxLayout()

        # PDF folder
        folder_label = QLabel("PDF文件夹* / PDF Folder*:")
        input_layout.addWidget(folder_label)

        folder_layout = QHBoxLayout()
        self.folder_entry = QLineEdit()
        folder_layout.addWidget(self.folder_entry)

        self.browse_folder_btn = QPushButton("浏览 / Browse")
        self.browse_folder_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.browse_folder_btn)

        input_layout.addLayout(folder_layout)

        # Metadata file
        meta_label = QLabel("元数据文件（可选）/ Metadata File (Optional):")
        input_layout.addWidget(meta_label)

        meta_layout = QHBoxLayout()
        self.meta_entry = QLineEdit()
        meta_layout.addWidget(self.meta_entry)

        self.browse_meta_btn = QPushButton("浏览 / Browse")
        self.browse_meta_btn.clicked.connect(self._browse_meta)
        meta_layout.addWidget(self.browse_meta_btn)

        input_layout.addLayout(meta_layout)

        # Output file
        output_label = QLabel("输出文件* / Output File*:")
        input_layout.addWidget(output_label)

        output_layout = QHBoxLayout()
        self.output_entry = QLineEdit()
        output_layout.addWidget(self.output_entry)

        self.browse_output_btn = QPushButton("保存为 / Save As")
        self.browse_output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.browse_output_btn)

        input_layout.addLayout(output_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Action buttons
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 开始分析 / Start Analysis")
        self.start_btn.clicked.connect(self.start_analysis)
        action_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ 停止 / Stop")
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
        log_label = QLabel("处理日志 / Processing Log:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)

        # Connect signals
        self.update_progress_signal.connect(self._update_progress)
        self.append_log_signal.connect(self._append_log)
        self.show_error_signal.connect(self._show_error)
        self.show_info_signal.connect(self._show_info)
        self.restore_buttons_signal.connect(self._restore_buttons)

        # Load default config
        self._load_default_config()

        # Register for language change notifications
        get_i18n().add_observer(self.update_language)

    def update_language(self) -> None:
        """Update UI text when language changes."""
        # Matrix tab labels are currently bilingual, so minimal updates needed
        pass

    def _load_default_config(self) -> None:
        """Load default matrix configuration."""
        try:
            self.matrix_config = load_matrix_config(str(self.default_config_path))
            dim_count = len(self.matrix_config.get("dimensions", []))
            self.dim_count_label.setText(f"当前维度数：{dim_count} / Current Dimensions: {dim_count}")
        except Exception as e:
            self.append_log_signal.emit(f"Failed to load default config: {e}")

    def _import_config(self) -> None:
        """Import matrix configuration from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Config",
            "",
            "YAML (*.yaml *.yml)"
        )
        if file_path:
            try:
                self.matrix_config = load_matrix_config(file_path)
                dim_count = len(self.matrix_config.get("dimensions", []))
                self.dim_count_label.setText(f"当前维度数：{dim_count} / Current Dimensions: {dim_count}")
                QMessageBox.information(self, "Success", "Configuration imported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import config: {e}")

    def _export_config(self) -> None:
        """Export current matrix configuration."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Config",
            "",
            "YAML (*.yaml)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(self.matrix_config, f, allow_unicode=True)
                QMessageBox.information(self, "Success", "Configuration exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export config: {e}")

    def _reset_config(self) -> None:
        """Reset to default configuration."""
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset to default configuration?",
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
            self.dim_count_label.setText(f"当前维度数：{dim_count} / Current Dimensions: {dim_count}")

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
            self.dim_count_label.setText(f"当前维度数：{dim_count} / Current Dimensions: {dim_count}")

    def _browse_folder(self) -> None:
        """Browse for PDF folder."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select PDF Folder")
        if folder_path:
            self.folder_entry.setText(folder_path)

    def _browse_meta(self) -> None:
        """Browse for metadata file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Metadata File",
            "",
            "CSV or Excel (*.csv *.xlsx)"
        )
        if file_path:
            self.meta_entry.setText(file_path)

    def _browse_output(self) -> None:
        """Browse for output file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output As",
            "",
            "Excel (*.xlsx)"
        )
        if file_path:
            self.output_entry.setText(file_path)

    def start_analysis(self) -> None:
        """Start matrix analysis."""
        pdf_folder = self.folder_entry.text().strip()
        output_file = self.output_entry.text().strip()

        if not pdf_folder or not output_file:
            QMessageBox.critical(self, "Error", "Please specify PDF folder and output file!")
            return

        # Initialize UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.stop_flag = False

        # Start processing in background thread
        metadata_file = self.meta_entry.text().strip() or None
        threading.Thread(
            target=self.process_analysis,
            args=(pdf_folder, metadata_file, output_file),
            daemon=True
        ).start()

    def stop_analysis(self) -> None:
        """Stop the analysis process."""
        self.stop_flag = True
        self.stop_btn.setEnabled(False)
        self.append_log_signal.emit("Stopping...")

    def process_analysis(self, pdf_folder: str, metadata_file: Optional[str], output_file: str) -> None:
        """Process matrix analysis in background thread."""
        config = self.parent_window.build_config()

        try:
            self.append_log_signal.emit("Starting matrix analysis...")

            # Process literature matrix
            results_df = process_literature_matrix(
                pdf_folder=pdf_folder,
                matrix_config=self.matrix_config,
                ai_config=config,
                metadata_file=metadata_file,
                progress_callback=self._progress_callback
            )

            if self.stop_flag:
                self.show_info_signal.emit("Info", "Analysis stopped by user")
                return

            # Save results
            save_results(results_df, output_file)

            self.append_log_signal.emit(f"Results saved to: {output_file}")
            self.show_info_signal.emit("Success", "Matrix analysis completed successfully!")

        except Exception as e:
            self.show_error_signal.emit("Error", f"Analysis failed: {e}")

        finally:
            self.restore_buttons_signal.emit()

    def _progress_callback(self, current: int, total: int, message: str = "") -> None:
        """Progress callback for matrix analysis."""
        if self.stop_flag:
            raise Exception("Analysis stopped by user")

        progress = (current / total * 100) if total > 0 else 0
        self.update_progress_signal.emit(progress)

        if message:
            self.append_log_signal.emit(f"[{current}/{total}] {message}")

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
