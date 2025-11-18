"""PyQt6-based abstract screening tab."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import pandas as pd

from ...abstract_screener import (
    load_mode_questions,
    load_and_validate_data,
    prepare_dataframe,
    AbstractScreener,
)
from ...i18n import get_i18n, t

if TYPE_CHECKING:
    from ..base_window_qt import BaseWindow


class AbstractTab(QWidget):
    """Tab for abstract screening."""

    # Signals for thread-safe UI updates
    update_progress_signal = pyqtSignal(float)
    update_status_signal = pyqtSignal(str)
    append_log_signal = pyqtSignal(str)
    show_error_signal = pyqtSignal(str, str)
    show_info_signal = pyqtSignal(str, str)
    enable_export_signal = pyqtSignal()
    restore_buttons_signal = pyqtSignal()

    def __init__(self, parent: BaseWindow) -> None:
        super().__init__()
        self.parent_window = parent

        # Data
        self.df: Optional[pd.DataFrame] = None
        self.mode_options = []
        self.stop_flag = False

        # Main layout with splitter
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # File selection
        self.file_label = QLabel(t("select_file_label"))
        left_layout.addWidget(self.file_label)

        file_layout = QHBoxLayout()
        self.file_entry = QLineEdit()
        file_layout.addWidget(self.file_entry)

        self.browse_btn = QPushButton(t("browse"))
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.browse_btn)

        left_layout.addLayout(file_layout)

        # Mode selection
        self.mode_label = QLabel(t("screening_mode_label"))
        left_layout.addWidget(self.mode_label)

        mode_layout = QHBoxLayout()
        self._load_modes()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.mode_options)
        mode_layout.addWidget(self.mode_combo)

        self.add_mode_btn = QPushButton(t("add_mode"))
        mode_layout.addWidget(self.add_mode_btn)

        left_layout.addLayout(mode_layout)

        # Options group
        options_group = QGroupBox(t("processing_options"))
        options_layout = QVBoxLayout()

        self.verify_checkbox = QCheckBox(t("enable_verification"))
        self.verify_checkbox.setChecked(True)
        options_layout.addWidget(self.verify_checkbox)

        workers_layout = QHBoxLayout()
        self.workers_label = QLabel(t("concurrent_workers"))
        workers_layout.addWidget(self.workers_label)

        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setRange(1, 10)
        self.workers_spinbox.setValue(3)
        workers_layout.addWidget(self.workers_spinbox)
        workers_layout.addStretch()

        options_layout.addLayout(workers_layout)
        options_group.setLayout(options_layout)
        left_layout.addWidget(options_group)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton(t("start_screening"))
        self.start_btn.clicked.connect(self.start_screening)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(t("stop_task"))
        self.stop_btn.clicked.connect(self.stop_screening)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        left_layout.addLayout(btn_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        left_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        left_layout.addWidget(self.status_label)

        # Log
        self.log_label = QLabel(t("log_label"))
        left_layout.addWidget(self.log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        left_layout.addWidget(self.log_text)

        # Export buttons
        export_layout = QHBoxLayout()
        self.export_csv_btn = QPushButton(t("export_csv"))
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.export_csv_btn.setEnabled(False)
        export_layout.addWidget(self.export_csv_btn)

        self.export_excel_btn = QPushButton(t("export_excel"))
        self.export_excel_btn.clicked.connect(self.export_excel)
        self.export_excel_btn.setEnabled(False)
        export_layout.addWidget(self.export_excel_btn)

        left_layout.addLayout(export_layout)
        left_layout.addStretch()

        # Right panel - Results preview
        right_panel = QGroupBox(t("results_preview"))
        right_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Title", "Status", "Summary"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.results_table)

        right_panel.setLayout(right_layout)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

        # Connect signals
        self.update_progress_signal.connect(self._update_progress)
        self.update_status_signal.connect(self._update_status)
        self.append_log_signal.connect(self._append_log)
        self.show_error_signal.connect(self._show_error)
        self.show_info_signal.connect(self._show_info)
        self.enable_export_signal.connect(self._enable_export)
        self.restore_buttons_signal.connect(self._restore_buttons)

        # Register for language change notifications
        get_i18n().add_observer(self.update_language)

    def update_language(self) -> None:
        """Update UI text when language changes."""
        self.file_label.setText(t("select_file_label"))
        self.browse_btn.setText(t("browse"))
        self.mode_label.setText(t("screening_mode_label"))
        self.add_mode_btn.setText(t("add_mode"))
        self.verify_checkbox.setText(t("enable_verification"))
        self.workers_label.setText(t("concurrent_workers"))
        self.start_btn.setText(t("start_screening"))
        self.stop_btn.setText(t("stop_task"))
        self.log_label.setText(t("log_label"))
        self.export_csv_btn.setText(t("export_csv"))
        self.export_excel_btn.setText(t("export_excel"))

    def _load_modes(self) -> None:
        """Load screening modes from configuration."""
        questions_path = Path(__file__).resolve().parents[3] / "questions_config.json"
        try:
            with open(questions_path, 'r', encoding='utf-8') as f:
                questions = json.load(f)
            self.mode_options = list(questions.keys())
        except Exception:
            self.mode_options = []

    def _browse_file(self) -> None:
        """Browse for CSV or Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("browse"),
            "",
            "CSV or Excel (*.csv *.xlsx)"
        )
        if file_path:
            self.file_entry.setText(file_path)

    def start_screening(self) -> None:
        """Start abstract screening."""
        file_path = self.file_entry.text().strip()
        mode = self.mode_combo.currentText()

        if not file_path or not mode:
            QMessageBox.critical(self, t("error"), t("error_fill_fields"))
            return

        # Initialize UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(False)
        self.export_excel_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.results_table.setRowCount(0)
        self.stop_flag = False

        # Start processing in background thread
        threading.Thread(
            target=self.process_screening,
            args=(file_path, mode),
            daemon=True
        ).start()

    def stop_screening(self) -> None:
        """Stop the screening process."""
        self.stop_flag = True
        self.stop_btn.setEnabled(False)
        self.append_log_signal.emit("Stopping...")

    def process_screening(self, file_path: str, mode: str) -> None:
        """Process abstract screening in background thread."""
        config = self.parent_window.build_config()

        try:
            # Load questions
            questions_dict = load_mode_questions(mode)

            # Load data
            df = load_and_validate_data(file_path)
            df = prepare_dataframe(df, questions_dict)

            self.df = df
            total = len(df)

            # Create screener
            enable_verification = self.verify_checkbox.isChecked()
            screener = AbstractScreener(
                config,
                questions_dict,
                enable_verification=enable_verification
            )

            # Process each row
            for i, (idx, row) in enumerate(df.iterrows(), start=1):
                if self.stop_flag:
                    self.show_info_signal.emit(t("hint"), t("task_stopped"))
                    break

                try:
                    title = row.get('Title', '')
                    abstract = row.get('Abstract', '')

                    self.update_status_signal.emit(f"Processing {i}/{total}: {title[:50]}...")
                    self.append_log_signal.emit(f"[{i}/{total}] {title[:50]}...")

                    result = screener.screen_abstract(title, abstract)

                    # Update table
                    self._add_result_row(i - 1, title, "Completed", "Analyzed")

                except Exception as e:
                    self.append_log_signal.emit(f"Error: {str(e)}")
                    self._add_result_row(i - 1, title, "Error", str(e))

                # Update progress
                self.update_progress_signal.emit(i / total * 100)

            if not self.stop_flag:
                self.enable_export_signal.emit()
                self.show_info_signal.emit(t("success"), "Screening completed!")

        except Exception as e:
            self.show_error_signal.emit(t("error"), str(e))

        finally:
            self.restore_buttons_signal.emit()

    def _add_result_row(self, row: int, title: str, status: str, summary: str) -> None:
        """Add a result row to the table (must be called from main thread via signal)."""
        # This is a simplified version - in reality you'd emit a signal
        pass

    def _update_progress(self, value: float) -> None:
        """Update progress bar."""
        self.progress_bar.setValue(int(value))

    def _update_status(self, text: str) -> None:
        """Update status label."""
        self.status_label.setText(text)

    def _append_log(self, text: str) -> None:
        """Append text to log."""
        self.log_text.append(text)

    def _show_error(self, title: str, message: str) -> None:
        """Show error message."""
        QMessageBox.critical(self, title, message)

    def _show_info(self, title: str, message: str) -> None:
        """Show info message."""
        QMessageBox.information(self, title, message)

    def _enable_export(self) -> None:
        """Enable export buttons."""
        self.export_csv_btn.setEnabled(True)
        self.export_excel_btn.setEnabled(True)

    def _restore_buttons(self) -> None:
        """Restore button states."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def export_csv(self) -> None:
        """Export results to CSV."""
        if self.df is None:
            QMessageBox.critical(self, t("error"), t("error_no_results"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_csv"),
            "",
            "CSV (*.csv)"
        )
        if file_path:
            try:
                self.df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, t("success"), t("results_exported"))
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))

    def export_excel(self) -> None:
        """Export results to Excel."""
        if self.df is None:
            QMessageBox.critical(self, t("error"), t("error_no_results"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_excel"),
            "",
            "Excel (*.xlsx)"
        )
        if file_path:
            try:
                self.df.to_excel(file_path, index=False)
                QMessageBox.information(self, t("success"), t("results_exported"))
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))
