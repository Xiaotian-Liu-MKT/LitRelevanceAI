"""PyQt6-based abstract screening tab."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from copy import deepcopy

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
    QDialog,
    QDialogButtonBox,
    QTabWidget,
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
        self.statistics: Optional[dict] = None
        self.mode_options = []
        self.modes_data = {}
        self.stop_flag = False

        # Load modes and configuration paths
        self._init_config_paths()
        self._load_modes()

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
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.mode_options)
        mode_layout.addWidget(self.mode_combo)

        self.add_mode_btn = QPushButton(t("add_mode"))
        self.add_mode_btn.clicked.connect(self.add_mode)
        mode_layout.addWidget(self.add_mode_btn)

        left_layout.addLayout(mode_layout)

        # Column selection (optional)
        col_label = QLabel(t("column_selection_optional"))
        left_layout.addWidget(col_label)

        col_layout = QHBoxLayout()
        self.title_col_label = QLabel(t("title_column"))
        col_layout.addWidget(self.title_col_label)

        self.title_col_entry = QLineEdit()
        self.title_col_entry.setMaximumWidth(120)
        col_layout.addWidget(self.title_col_entry)

        self.abstract_col_label = QLabel(t("abstract_column"))
        col_layout.addWidget(self.abstract_col_label)

        self.abstract_col_entry = QLineEdit()
        self.abstract_col_entry.setMaximumWidth(120)
        col_layout.addWidget(self.abstract_col_entry)

        col_layout.addStretch()
        left_layout.addLayout(col_layout)

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

        # Action buttons (2x2 grid)
        btn_widget = QWidget()
        btn_grid = QGridLayout(btn_widget)
        btn_grid.setSpacing(5)

        self.start_btn = QPushButton(t("start_screening"))
        self.start_btn.clicked.connect(self.start_screening)
        btn_grid.addWidget(self.start_btn, 0, 0)

        self.stop_btn = QPushButton(t("stop_task"))
        self.stop_btn.clicked.connect(self.stop_screening)
        self.stop_btn.setEnabled(False)
        btn_grid.addWidget(self.stop_btn, 0, 1)

        self.edit_btn = QPushButton(t("edit_questions"))
        self.edit_btn.clicked.connect(self.edit_questions)
        btn_grid.addWidget(self.edit_btn, 1, 0)

        self.stats_btn = QPushButton(t("view_statistics"))
        self.stats_btn.clicked.connect(self.show_statistics)
        btn_grid.addWidget(self.stats_btn, 1, 1)

        left_layout.addWidget(btn_widget)

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

        self.preview_status_label = QLabel(t("no_data"))
        right_layout.addWidget(self.preview_status_label)

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

    def _init_config_paths(self) -> None:
        """Initialize configuration paths."""
        self.q_config_path = Path(__file__).resolve().parents[3] / "questions_config.json"

    def _load_modes(self) -> None:
        """Load available screening modes from both unified and legacy configs."""
        modes = set()

        # Load from unified configs
        unified_dir = Path(__file__).resolve().parents[3] / "configs" / "abstract"
        if unified_dir.exists():
            for yaml_file in unified_dir.glob("*.yaml"):
                modes.add(yaml_file.stem)

        # Load from legacy config
        try:
            with self.q_config_path.open("r", encoding="utf-8") as f:
                self.modes_data = json.load(f)
                modes.update(self.modes_data.keys())
        except Exception:
            self.modes_data = {}

        self.mode_options = sorted(list(modes)) if modes else ["weekly_screening"]

    def update_language(self) -> None:
        """Update UI text when language changes."""
        self.file_label.setText(t("select_file_label"))
        self.browse_btn.setText(t("browse"))
        self.mode_label.setText(t("screening_mode_label"))
        self.add_mode_btn.setText(t("add_mode"))
        self.title_col_label.setText(t("title_column"))
        self.abstract_col_label.setText(t("abstract_column"))
        self.verify_checkbox.setText(t("enable_verification"))
        self.workers_label.setText(t("concurrent_workers"))
        self.start_btn.setText(t("start_screening"))
        self.stop_btn.setText(t("stop_task"))
        self.edit_btn.setText(t("edit_questions"))
        self.stats_btn.setText(t("view_statistics"))
        self.log_label.setText(t("log_label"))
        self.export_csv_btn.setText(t("export_csv"))
        self.export_excel_btn.setText(t("export_excel"))

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

    def add_mode(self) -> None:
        """Add a new screening mode."""
        name, ok = QInputDialog.getText(
            self,
            t("new_mode"),
            t("enter_mode_name")
        )
        if not ok or not name:
            return

        if name in self.modes_data:
            QMessageBox.critical(self, t("error"), t("mode_exists"))
            return

        desc, ok = QInputDialog.getText(
            self,
            t("description"),
            t("enter_description")
        )
        if not ok:
            desc = ""

        self.modes_data[name] = {
            "description": desc,
            "open_questions": [],
            "yes_no_questions": []
        }

        try:
            with self.q_config_path.open("w", encoding="utf-8") as f:
                json.dump(self.modes_data, f, ensure_ascii=False, indent=2)

            # Update combo box
            self.mode_combo.clear()
            self.mode_combo.addItems(sorted(self.modes_data.keys()))
            self.mode_combo.setCurrentText(name)

            QMessageBox.information(self, t("success"), f"Mode '{name}' created successfully!")
        except Exception as e:
            QMessageBox.critical(self, t("error"), f"Failed to save mode: {e}")

    def edit_questions(self) -> None:
        """Show question editor dialog."""
        mode = self.mode_combo.currentText()
        if not mode:
            QMessageBox.warning(self, t("hint"), t("please_select_mode"))
            return

        dialog = QuestionEditorDialog(self, mode, self.q_config_path, self.modes_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload modes data
            try:
                with self.q_config_path.open("r", encoding="utf-8") as f:
                    self.modes_data = json.load(f)
                # Update combo box
                current_mode = self.mode_combo.currentText()
                self.mode_combo.clear()
                self.mode_combo.addItems(sorted(self.modes_data.keys()))
                if current_mode in self.modes_data:
                    self.mode_combo.setCurrentText(current_mode)
            except Exception:
                pass

    def show_statistics(self) -> None:
        """Show statistics dialog."""
        if self.statistics is None:
            QMessageBox.information(self, t("hint"), t("please_complete_screening"))
            return

        dialog = StatisticsViewerDialog(self, self.statistics)
        dialog.exec()

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
                    # Note: This is simplified - full implementation would update df

                except Exception as e:
                    self.append_log_signal.emit(f"Error: {str(e)}")

                # Update progress
                self.update_progress_signal.emit(i / total * 100)

            if not self.stop_flag:
                self.enable_export_signal.emit()
                self.show_info_signal.emit(t("success"), "Screening completed!")

        except Exception as e:
            self.show_error_signal.emit(t("error"), str(e))

        finally:
            self.restore_buttons_signal.emit()

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


class QuestionEditorDialog(QDialog):
    """Dialog for editing screening mode questions."""

    def __init__(self, parent: QWidget, mode: str, q_config_path: Path, modes_data: dict):
        super().__init__(parent)
        self.mode = mode
        self.q_config_path = q_config_path
        self.modes_data = modes_data

        self.setWindowTitle(t("edit_questions"))
        self.resize(640, 480)

        layout = QVBoxLayout(self)

        # Load mode data
        mode_data = modes_data.get(
            mode,
            {"description": "", "open_questions": [], "yes_no_questions": []}
        )
        self.open_questions = deepcopy(mode_data.get("open_questions", []))
        self.yes_no_questions = deepcopy(mode_data.get("yes_no_questions", []))

        # Info label
        info_label = QLabel(f"Editing mode: {mode}")
        info_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(info_label)

        # Tab widget for questions
        tabs = QTabWidget()

        # Open questions tab
        open_tab = QWidget()
        open_layout = QVBoxLayout(open_tab)
        self.open_text = QTextEdit()
        self.open_text.setPlainText(json.dumps(self.open_questions, ensure_ascii=False, indent=2))
        open_layout.addWidget(QLabel(t("open_questions")))
        open_layout.addWidget(self.open_text)
        tabs.addTab(open_tab, t("open_questions"))

        # Yes/No questions tab
        yn_tab = QWidget()
        yn_layout = QVBoxLayout(yn_tab)
        self.yn_text = QTextEdit()
        self.yn_text.setPlainText(json.dumps(self.yes_no_questions, ensure_ascii=False, indent=2))
        yn_layout.addWidget(QLabel(t("yes_no_questions")))
        yn_layout.addWidget(self.yn_text)
        tabs.addTab(yn_tab, t("yes_no_questions"))

        layout.addWidget(tabs)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_questions)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def save_questions(self) -> None:
        """Save questions to configuration file."""
        try:
            # Parse JSON from text edits
            open_q = json.loads(self.open_text.toPlainText())
            yn_q = json.loads(self.yn_text.toPlainText())

            # Update mode data
            mode_data = self.modes_data.get(self.mode, {})
            mode_data["open_questions"] = open_q
            mode_data["yes_no_questions"] = yn_q

            # Save to file
            self.modes_data[self.mode] = mode_data
            with self.q_config_path.open("w", encoding="utf-8") as f:
                json.dump(self.modes_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, t("success"), "Questions saved successfully!")
            self.accept()

        except json.JSONDecodeError as e:
            QMessageBox.critical(self, t("error"), f"Invalid JSON format: {e}")
        except Exception as e:
            QMessageBox.critical(self, t("error"), f"Failed to save: {e}")


class StatisticsViewerDialog(QDialog):
    """Dialog for viewing abstract screening statistics."""

    def __init__(self, parent: QWidget, statistics: dict):
        super().__init__(parent)
        self.statistics = statistics

        self.setWindowTitle(t("screening_statistics"))
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(t("statistics_summary", count=statistics['total_articles']))
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()

        # Yes/No Questions Tab
        yn_tab = QWidget()
        yn_layout = QVBoxLayout(yn_tab)
        yn_text = QTextEdit()
        yn_text.setReadOnly(True)

        # Format yes/no statistics
        yn_stats = []
        for question, stats in statistics.get('yes_no_results', {}).items():
            yn_stats.append(f"\n{'='*60}")
            yn_stats.append(f"问题: {question}")
            yn_stats.append(f"{'-'*60}")
            yn_stats.append(f"  是: {stats.get('是', 0)} 篇")
            yn_stats.append(f"  否: {stats.get('否', 0)} 篇")
            yn_stats.append(f"  不确定: {stats.get('不确定', 0)} 篇")
            yn_stats.append(f"  其他: {stats.get('其他', 0)} 篇")

            if 'verification' in stats:
                yn_stats.append("\n验证结果:")
                ver = stats['verification']
                yn_stats.append(f"  已验证: {ver.get('已验证', 0)} 篇")
                yn_stats.append(f"  未验证: {ver.get('未验证', 0)} 篇")
                yn_stats.append(f"  不确定: {ver.get('不确定', 0)} 篇")

        yn_text.setPlainText('\n'.join(yn_stats))
        yn_layout.addWidget(yn_text)
        tabs.addTab(yn_tab, t("yes_no_questions_stats"))

        # Open Questions Tab
        oq_tab = QWidget()
        oq_layout = QVBoxLayout(oq_tab)
        oq_text = QTextEdit()
        oq_text.setReadOnly(True)

        # Format open questions statistics
        oq_stats = []
        for question, stats in statistics.get('open_question_results', {}).items():
            oq_stats.append(f"\n{'='*60}")
            oq_stats.append(f"问题: {question}")
            oq_stats.append(f"{'-'*60}")
            oq_stats.append(f"  已回答: {stats.get('已回答', 0)} 篇")
            oq_stats.append(f"  未回答: {stats.get('未回答', 0)} 篇")

        oq_text.setPlainText('\n'.join(oq_stats))
        oq_layout.addWidget(oq_text)
        tabs.addTab(oq_tab, t("open_questions_stats"))

        layout.addWidget(tabs)

        # Close button
        close_btn = QPushButton(t("close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
