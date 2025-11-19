"""PyQt6-based CSV relevance analysis tab."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDialog,
)
from PyQt6.QtGui import QFont

import pandas as pd

from ...csv_analyzer import LiteratureAnalyzer
from ...i18n import t, get_i18n
from ...task_manager import CancellableTask, TaskCancelledException

if TYPE_CHECKING:
    from ..base_window_qt import BaseWindow


class CsvAnalysisWorker(QThread):
    """Worker thread for CSV analysis processing.

    This QThread-based worker handles CSV analysis in the background,
    emitting signals for thread-safe UI updates.
    """

    # Signals for thread-safe communication with main thread
    update_row = pyqtSignal(int, str, object, str)  # row, title, score, analysis
    update_progress = pyqtSignal(float)  # progress percentage
    show_error = pyqtSignal(str, str)  # title, message
    show_info = pyqtSignal(str, str)  # title, message
    enable_export = pyqtSignal()
    finished_processing = pyqtSignal()  # Emitted when done (success or cancelled)

    def __init__(self, config: dict, path: str, topic: str, task: CancellableTask):
        """Initialize the worker.

        Args:
            config: Configuration dictionary
            path: Path to CSV file
            topic: Research topic
            task: CancellableTask for cancellation support
        """
        super().__init__()
        self.config = config
        self.path = path
        self.topic = topic
        self.task = task
        self.df: Optional[pd.DataFrame] = None
        self.analyzer: Optional[LiteratureAnalyzer] = None

    def run(self) -> None:
        """Run the analysis (executed in background thread)."""
        analyzer = LiteratureAnalyzer(self.config, self.topic)

        try:
            df = analyzer.read_scopus_csv(self.path)
        except Exception as e:
            self.show_error.emit(t("error"), t("error_read_file", error=str(e)))
            self.finished_processing.emit()
            return

        self.df = df
        self.analyzer = analyzer
        total = len(df)

        try:
            # Process all papers with cancellation checks
            for i, (idx, row) in enumerate(df.iterrows(), start=1):
                # Check for cancellation
                if self.task and self.task.is_cancelled():
                    self.show_info.emit(t("hint"), t("task_stopped"))
                    break

                try:
                    res = analyzer.analyze_paper(row['Title'], row['Abstract'])
                    analyzer.apply_result_to_dataframe(df, idx, res)

                    summary = res['analysis'].replace('\n', ' ')[:80]
                    self.update_row.emit(i - 1, row['Title'], res['relevance_score'], summary)

                except Exception as e:
                    error_msg = t("error_analysis", error=str(e))
                    self.update_row.emit(i - 1, row['Title'], '', error_msg)

                # Update progress bar
                self.update_progress.emit(i / total * 100)

            # Enable export button when done (only if not cancelled)
            if not (self.task and self.task.is_cancelled()):
                # Auto-save results beside the input CSV with timestamped name
                try:
                    file_dir = os.path.dirname(self.path)
                    file_name = os.path.splitext(os.path.basename(self.path))[0]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_path = os.path.join(file_dir, f"{file_name}_analyzed_{timestamp}.csv")
                    df.to_csv(out_path, index=False, encoding='utf-8-sig')
                    self.show_info.emit(t("success"), t("complete_saved", path=out_path))
                except Exception as e:
                    self.show_error.emit(t("error"), str(e))
                self.enable_export.emit()

        except TaskCancelledException:
            self.show_info.emit(t("hint"), t("task_stopped"))

        except Exception as e:
            self.show_error.emit(t("error"), t("error_analysis", error=str(e)))

        finally:
            self.finished_processing.emit()


class CsvTab(QWidget):
    """Tab for CSV relevance analysis."""

    def __init__(self, parent: BaseWindow) -> None:
        super().__init__()
        self.parent_window = parent

        # Worker thread and task management
        self.worker: Optional[CsvAnalysisWorker] = None
        self.current_task: Optional[CancellableTask] = None
        self.df: Optional[pd.DataFrame] = None
        self.analyzer: Optional[LiteratureAnalyzer] = None

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Research topic
        self.topic_label = QLabel(t("research_topic_label"))
        layout.addWidget(self.topic_label)

        self.topic_entry = QLineEdit()
        layout.addWidget(self.topic_entry)

        # File selection
        self.file_label = QLabel(t("select_csv_file"))
        layout.addWidget(self.file_label)

        file_layout = QHBoxLayout()
        self.file_entry = QLineEdit()
        file_layout.addWidget(self.file_entry)

        self.browse_btn = QPushButton(t("browse"))
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.browse_btn)

        layout.addLayout(file_layout)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton(t("start_analysis"))
        self.start_btn.clicked.connect(self.start_analysis)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(t("stop_task"))
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([t("table_title"), t("table_score"), t("table_analysis")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self.show_full_analysis)
        layout.addWidget(self.table)

        # Export button
        self.export_btn = QPushButton(t("export_results"))
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)

        # Register for language change notifications
        get_i18n().add_observer(self.update_language)

    def update_language(self) -> None:
        """Update UI text when language changes."""
        self.topic_label.setText(t("research_topic_label"))
        self.file_label.setText(t("select_csv_file"))
        self.browse_btn.setText(t("browse"))
        self.start_btn.setText(t("start_analysis"))
        self.stop_btn.setText(t("stop_task"))
        self.export_btn.setText(t("export_results"))
        self.table.setHorizontalHeaderLabels([t("table_title"), t("table_score"), t("table_analysis")])

    def _browse_file(self) -> None:
        """Browse for CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("browse"),
            "",
            f"{t('csv_files')} (*.csv)"
        )
        if file_path:
            self.file_entry.setText(file_path)

    def start_analysis(self) -> None:
        """Start CSV analysis using QThread worker."""
        path = self.file_entry.text().strip()
        topic = self.topic_entry.text().strip()
        if not path or not topic:
            QMessageBox.critical(self, t("error"), t("error_fill_fields"))
            return

        # Initialize UI state
        self.export_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.table.setRowCount(0)
        self.df = None
        self.analyzer = None

        # Create cancellable task
        self.current_task = CancellableTask()

        # Create and configure worker thread
        config = self.parent_window.build_config()
        self.worker = CsvAnalysisWorker(config, path, topic, self.current_task)

        # Connect worker signals to UI update slots
        self.worker.update_row.connect(self._update_row)
        self.worker.update_progress.connect(self._update_progress)
        self.worker.show_error.connect(self._show_error)
        self.worker.show_info.connect(self._show_info)
        self.worker.enable_export.connect(self._enable_export)
        self.worker.finished_processing.connect(self._on_worker_finished)

        # Start the worker thread
        self.worker.start()

    def stop_analysis(self) -> None:
        """Stop the current analysis task."""
        if self.current_task:
            self.current_task.cancel()
            self.stop_btn.setEnabled(False)

        # Note: Worker will detect cancellation and finish gracefully

    def _on_worker_finished(self) -> None:
        """Called when worker thread finishes (success or cancelled)."""
        # Copy results from worker to main thread
        if self.worker:
            self.df = self.worker.df
            self.analyzer = self.worker.analyzer

        # Restore button states
        self._restore_buttons()

        # Clean up worker reference
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _update_row(self, row: int, title: str, score, analysis: str) -> None:
        """Update a row in the table (called from main thread)."""
        if row >= self.table.rowCount():
            self.table.setRowCount(row + 1)

        self.table.setItem(row, 0, QTableWidgetItem(title))
        self.table.setItem(row, 1, QTableWidgetItem(str(score)))
        self.table.setItem(row, 2, QTableWidgetItem(analysis))

    def _update_progress(self, value: float) -> None:
        """Update progress bar (called from main thread)."""
        self.progress_bar.setValue(int(value))

    def _show_error(self, title: str, message: str) -> None:
        """Show error message (called from main thread)."""
        QMessageBox.critical(self, title, message)

    def _show_info(self, title: str, message: str) -> None:
        """Show info message (called from main thread)."""
        QMessageBox.information(self, title, message)

    def _enable_export(self) -> None:
        """Enable export button (called from main thread)."""
        self.export_btn.setEnabled(True)

    def _restore_buttons(self) -> None:
        """Restore button states (called from main thread)."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def show_full_analysis(self) -> None:
        """Show full analysis in a dialog when row is double-clicked."""
        current_row = self.table.currentRow()
        if current_row < 0 or self.df is None:
            return

        try:
            idx = self.df.index[current_row]
            analysis = self.df.at[idx, 'Analysis Result']
            if pd.isna(analysis):
                return

            title = self.df.at[idx, 'Title']

            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(title)
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)
            text_edit = QTextEdit()
            text_edit.setPlainText(str(analysis))
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Consolas", 9))
            layout.addWidget(text_edit)

            close_btn = QPushButton(t("close"))
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.exec()

        except Exception:
            pass

    def export_results(self) -> None:
        """Export results to CSV."""
        if self.df is None or self.analyzer is None:
            QMessageBox.critical(self, t("error"), t("error_no_results"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_results"),
            "",
            f"{t('csv_files')} (*.csv)"
        )
        if file_path:
            try:
                self.analyzer.save_results(self.df, file_path)
                QMessageBox.information(self, t("success"), t("results_exported"))
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))
