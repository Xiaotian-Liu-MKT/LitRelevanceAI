"""PyQt6-based CSV relevance analysis tab."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject
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


class CsvTab(QWidget):
    """Tab for CSV relevance analysis."""

    # Signals for thread-safe UI updates
    update_row_signal = pyqtSignal(int, str, object, str)
    update_progress_signal = pyqtSignal(float)
    show_error_signal = pyqtSignal(str, str)
    show_info_signal = pyqtSignal(str, str)
    enable_export_signal = pyqtSignal()
    restore_buttons_signal = pyqtSignal()

    def __init__(self, parent: BaseWindow) -> None:
        super().__init__()
        self.parent_window = parent

        # Data
        self.df: Optional[pd.DataFrame] = None
        self.analyzer: Optional[LiteratureAnalyzer] = None
        self.current_task: Optional[CancellableTask] = None

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

        # Connect signals
        self.update_row_signal.connect(self._update_row)
        self.update_progress_signal.connect(self._update_progress)
        self.show_error_signal.connect(self._show_error)
        self.show_info_signal.connect(self._show_info)
        self.enable_export_signal.connect(self._enable_export)
        self.restore_buttons_signal.connect(self._restore_buttons)

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
        """Start CSV analysis with cancellation support."""
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

        # Start processing in background thread
        threading.Thread(target=self.process_csv, args=(path, topic), daemon=True).start()

    def stop_analysis(self) -> None:
        """Stop the current analysis task."""
        if self.current_task:
            self.current_task.cancel()
            self.stop_btn.setEnabled(False)

    def process_csv(self, path: str, topic: str) -> None:
        """Process CSV file with thread-safe updates and cancellation support."""
        config = self.parent_window.build_config()
        analyzer = LiteratureAnalyzer(config, topic)

        try:
            df = analyzer.read_scopus_csv(path)
        except Exception as e:
            self.show_error_signal.emit(t("error"), t("error_read_file", error=str(e)))
            self.restore_buttons_signal.emit()
            return

        self.df = df
        self.analyzer = analyzer
        total = len(df)

        try:
            # Process all papers with cancellation checks
            for i, (idx, row) in enumerate(df.iterrows(), start=1):
                # Check for cancellation
                if self.current_task and self.current_task.is_cancelled():
                    self.show_info_signal.emit(t("hint"), t("task_stopped"))
                    break

                try:
                    res = analyzer.analyze_paper(row['Title'], row['Abstract'])
                    analyzer.apply_result_to_dataframe(df, idx, res)

                    summary = res['analysis'].replace('\n', ' ')[:80]
                    self.update_row_signal.emit(i - 1, row['Title'], res['relevance_score'], summary)

                except Exception as e:
                    error_msg = t("error_analysis", error=str(e))
                    self.update_row_signal.emit(i - 1, row['Title'], '', error_msg)

                # Update progress bar
                self.update_progress_signal.emit(i / total * 100)

            # Enable export button when done (only if not cancelled)
            if not (self.current_task and self.current_task.is_cancelled()):
                self.enable_export_signal.emit()

        except TaskCancelledException:
            self.show_info_signal.emit(t("hint"), t("task_stopped"))

        except Exception as e:
            self.show_error_signal.emit(t("error"), t("error_analysis", error=str(e)))

        finally:
            self.restore_buttons_signal.emit()

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
