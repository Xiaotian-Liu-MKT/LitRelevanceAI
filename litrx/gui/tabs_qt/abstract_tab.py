"""PyQt6-based abstract screening tab."""

from __future__ import annotations

import json
from pathlib import Path
import os
import threading
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
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
from ...resources import resource_path
from ..dialogs_qt.ai_mode_assistant_qt import AIModeAssistantDialog

if TYPE_CHECKING:
    from ..base_window_qt import BaseWindow


class AbstractScreeningWorker(QThread):
    """Worker thread for abstract screening processing.

    This QThread-based worker handles abstract screening in the background,
    emitting signals for thread-safe UI updates.
    """

    # Signals for thread-safe communication with main thread
    update_progress = pyqtSignal(float)  # progress percentage
    update_status = pyqtSignal(str)  # status text
    append_log = pyqtSignal(str)  # log text to append
    add_result_row = pyqtSignal(int, str, str, str)  # row, title, status, summary
    show_error = pyqtSignal(str, str)  # title, message
    show_info = pyqtSignal(str, str)  # title, message
    enable_export = pyqtSignal()
    finished_processing = pyqtSignal()  # Emitted when done (success or cancelled)

    def __init__(self, config: dict, file_path: str, mode: str, verify_enabled: bool):
        """Initialize the worker.

        Args:
            config: Configuration dictionary
            file_path: Path to input file (CSV or Excel)
            mode: Screening mode name
            verify_enabled: Whether verification is enabled
        """
        super().__init__()
        self.config = config
        self.file_path = file_path
        self.mode = mode
        self.verify_enabled = verify_enabled
        self.stop_event = threading.Event()
        self.df: Optional[pd.DataFrame] = None

    def stop(self) -> None:
        """Request the worker to stop processing."""
        self.stop_event.set()

    def run(self) -> None:
        """Run the screening process (executed in background thread)."""
        try:
            # Load questions for selected mode
            q = load_mode_questions(self.mode)
            open_q = q.get("open_questions", [])
            yes_no_q = q.get("yes_no_questions", [])

            # Load and validate data
            df, title_col, abstract_col = load_and_validate_data(self.file_path, self.config)
            df = prepare_dataframe(df, open_q, yes_no_q)

            self.df = df
            total = len(df)

            # Create screener with verification setting
            self.config["ENABLE_VERIFICATION"] = self.verify_enabled
            screener = AbstractScreener(self.config)

            # Log start of concurrent processing
            max_workers = self.config.get('MAX_WORKERS', 3)
            self.append_log.emit(f"Starting concurrent analysis with {max_workers} workers...")
            self.update_status.emit(f"Processing {total} articles with {max_workers} workers...")

            # Progress callback to update UI (called from worker threads)
            def progress_callback(index: int, total_count: int, result: Optional[dict]) -> None:
                """Update UI with progress (thread-safe via signals)."""
                try:
                    # Get title from result if available
                    row_data = df.iloc[index]
                    title = str(row_data.get(title_col, ''))[:50]

                    # Emit progress update
                    progress_pct = ((index + 1) / total_count) * 100
                    self.update_progress.emit(progress_pct)
                    self.update_status.emit(f"Processing {index + 1}/{total_count}: {title}...")

                    # Log status with verification indicator
                    if result and result.get("verification"):
                        verification_status = " ✔" if any(
                            v == "是" for v in result.get("verification", {}).get("screening_results", {}).values()
                        ) else " ✖"
                    else:
                        verification_status = ""

                    self.append_log.emit(f"[{index + 1}/{total_count}] {title}{verification_status}")

                    # Update table
                    status = "Completed" if result else "Error"
                    summary = "Analyzed" if result else "Failed"
                    self.add_result_row.emit(index, title, status, summary)

                except Exception as e:
                    # Silently log errors in callback to avoid disrupting processing
                    self.append_log.emit(f"Progress callback error: {str(e)}")

            # Use concurrent processing (5-10x faster!)
            try:
                df = screener.analyze_batch_concurrent(
                    df=df,
                    title_col=title_col,
                    abstract_col=abstract_col,
                    open_questions=open_q,
                    yes_no_questions=yes_no_q,
                    progress_callback=progress_callback,
                    stop_event=self.stop_event
                )
                self.df = df  # Update with processed results

            except KeyboardInterrupt:
                # User cancelled via stop button
                self.show_info.emit(t("hint"), t("task_stopped"))
                return

            if not self.stop_event.is_set():
                # Auto-save results beside the input file using configured suffix
                try:
                    base, ext = os.path.splitext(self.file_path)
                    suffix = self.config.get("OUTPUT_FILE_SUFFIX", "_analyzed")
                    output_file_path = f"{base}{suffix}{ext}"
                    if ext.lower() == ".csv":
                        df.to_csv(output_file_path, index=False, encoding="utf-8-sig")
                    else:
                        df.to_excel(output_file_path, index=False)
                    self.show_info.emit(t("success"), t("complete_saved", path=output_file_path))
                except Exception as e:
                    self.show_error.emit(t("error"), str(e))

                self.enable_export.emit()

        except Exception as e:
            self.show_error.emit(t("error"), str(e))

        finally:
            self.finished_processing.emit()


class AbstractTab(QWidget):
    """Tab for abstract screening."""

    def __init__(self, parent: BaseWindow) -> None:
        super().__init__()
        self.parent_window = parent

        # Worker thread and data
        self.worker: Optional[AbstractScreeningWorker] = None
        self.df: Optional[pd.DataFrame] = None
        self.mode_options = []

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
        self.add_mode_btn.clicked.connect(self.add_mode)
        mode_layout.addWidget(self.add_mode_btn)

        self.edit_questions_btn = QPushButton(t("edit_questions"))
        self.edit_questions_btn.clicked.connect(self.edit_questions)
        mode_layout.addWidget(self.edit_questions_btn)

        self.ai_assist_btn = QPushButton(t("ai_mode_assistant_title") or "AI Assistant")
        self.ai_assist_btn.clicked.connect(self.open_ai_mode_assistant)
        mode_layout.addWidget(self.ai_assist_btn)

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

        self.stats_btn = QPushButton(t("view_statistics"))
        self.stats_btn.clicked.connect(self.show_statistics)
        self.stats_btn.setEnabled(True)
        btn_layout.addWidget(self.stats_btn)

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

        # Register for language change notifications
        get_i18n().add_observer(self.update_language)

    def update_language(self) -> None:
        """Update UI text when language changes."""
        self.file_label.setText(t("select_file_label"))
        self.browse_btn.setText(t("browse"))
        self.mode_label.setText(t("screening_mode_label"))
        self.add_mode_btn.setText(t("add_mode"))
        self.edit_questions_btn.setText(t("edit_questions"))
        self.ai_assist_btn.setText(t("ai_mode_assistant_title") or "AI Assistant")
        self.verify_checkbox.setText(t("enable_verification"))
        self.workers_label.setText(t("concurrent_workers"))
        self.start_btn.setText(t("start_screening"))
        self.stop_btn.setText(t("stop_task"))
        self.stats_btn.setText(t("view_statistics"))
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
        """Start abstract screening using QThread worker."""
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

        # Create and configure worker thread
        config = self.parent_window.build_config()
        # Apply concurrent workers setting from spinbox
        config['MAX_WORKERS'] = self.workers_spinbox.value()
        verify_enabled = self.verify_checkbox.isChecked()
        self.worker = AbstractScreeningWorker(config, file_path, mode, verify_enabled)

        # Connect worker signals to UI update slots
        self.worker.update_progress.connect(self._update_progress)
        self.worker.update_status.connect(self._update_status)
        self.worker.append_log.connect(self._append_log)
        self.worker.add_result_row.connect(self._add_result_row)
        self.worker.show_error.connect(self._show_error)
        self.worker.show_info.connect(self._show_info)
        self.worker.enable_export.connect(self._enable_export)
        self.worker.finished_processing.connect(self._on_worker_finished)

        # Start the worker thread
        self.worker.start()

    def stop_screening(self) -> None:
        """Stop the screening process."""
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self._append_log("Stopping...")

    def _on_worker_finished(self) -> None:
        """Called when worker thread finishes (success or cancelled)."""
        # Copy results from worker to main thread
        if self.worker:
            self.df = self.worker.df

        # Restore button states
        self._restore_buttons()

        # Clean up worker reference
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _add_result_row(self, row: int, title: str, status: str, summary: str) -> None:
        """Add a result row to the table (must be called from main thread via signal)."""
        if row >= self.results_table.rowCount():
            self.results_table.setRowCount(row + 1)
        self.results_table.setItem(row, 0, QTableWidgetItem(title))
        self.results_table.setItem(row, 1, QTableWidgetItem(status))
        self.results_table.setItem(row, 2, QTableWidgetItem(summary))

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

    # ------------------------------------------------------------------
    # Modes and Questions Management
    # ------------------------------------------------------------------
    def _questions_path(self) -> Path:
        return resource_path("questions_config.json")

    def _resolve_questions_config_write_path(self) -> Path:
        """Resolve a writable path for questions_config.json (handles frozen apps)."""
        import os
        # Prefer resource path if writable
        p = self._questions_path()
        try:
            os.makedirs(os.path.dirname(str(p)), exist_ok=True)
            with open(p, 'a', encoding='utf-8'):
                pass
            return p
        except Exception:
            user_dir = os.path.join(os.path.expanduser('~'), '.litrx')
            os.makedirs(user_dir, exist_ok=True)
            return Path(user_dir) / 'questions_config.json'

    def _write_questions_config(self, data: dict, backup: bool = False) -> None:
        # Try writing to packaged location; if fails, write to ~/.litrx/questions_config.json
        import os, json, time
        target = self._resolve_questions_config_write_path()
        if backup and os.path.exists(target):
            bak = str(target) + f".bak.{int(time.time())}"
            try:
                with open(target, 'r', encoding='utf-8') as src, open(bak, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            except Exception:
                pass
        with open(target, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_mode(self) -> None:
        """Add a new screening mode and persist to questions_config.json."""
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, t("new_mode"), t("enter_mode_name"))
        if not ok or not name.strip():
            return
        name = name.strip()

        q_path = self._questions_path()
        try:
            if q_path.exists():
                with q_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except Exception:
            data = {}

        if name in data:
            QMessageBox.warning(self, t("warning"), t("mode_exists"))
            return

        # Create empty mode template
        data[name] = {
            "description": "",
            "open_questions": [],
            "yes_no_questions": []
        }

        try:
            with q_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))
            return

        # Refresh combo
        self._load_modes()
        self.mode_combo.clear()
        self.mode_combo.addItems(self.mode_options)
        # Select new mode
        idx = self.mode_combo.findText(name)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        QMessageBox.information(self, t("success"), t("saved"))

    def edit_questions(self) -> None:
        """Open a simple Qt dialog to edit questions for the selected mode."""
        mode = self.mode_combo.currentText().strip()
        if not mode:
            QMessageBox.warning(self, t("warning"), t("please_select_mode"))
            return

        q_path = self._questions_path()
        try:
            with q_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        mode_data = data.get(mode, {"open_questions": [], "yes_no_questions": []})

        dialog = QDialog(self)
        dialog.setWindowTitle(t("edit_questions"))
        layout = QVBoxLayout(dialog)

        # Two lists: open and yes/no with labels
        lists_layout = QHBoxLayout()
        left_col = QVBoxLayout(); right_col = QVBoxLayout()
        left_col.addWidget(QLabel(t("open_questions")))
        right_col.addWidget(QLabel(t("yes_no_questions")))
        open_list = QListWidget()
        yn_list = QListWidget()
        for q in mode_data.get("open_questions", []):
            QListWidgetItem(q.get("question", ""), open_list)
        for q in mode_data.get("yes_no_questions", []):
            QListWidgetItem(q.get("question", ""), yn_list)
        left_col.addWidget(open_list)
        right_col.addWidget(yn_list)
        lists_layout.addLayout(left_col)
        lists_layout.addLayout(right_col)
        layout.addLayout(lists_layout)

        # Editors
        form_layout = QVBoxLayout()
        key_edit = QLineEdit(); key_edit.setPlaceholderText("key")
        col_edit = QLineEdit(); col_edit.setPlaceholderText("column_name")
        q_text = QTextEdit(); q_text.setPlaceholderText("question")
        form_layout.addWidget(key_edit)
        form_layout.addWidget(col_edit)
        form_layout.addWidget(q_text)
        layout.addLayout(form_layout)

        # Buttons
        btns = QHBoxLayout()
        add_open = QPushButton(t("add"))
        add_yn = QPushButton(t("add"))
        edit_btn = QPushButton(t("edit"))
        del_btn = QPushButton(t("delete"))
        save_btn = QPushButton(t("save"))
        cancel_btn = QPushButton(t("cancel"))
        btns.addWidget(add_open)
        btns.addWidget(add_yn)
        btns.addWidget(edit_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        def read_fields():
            return {
                "key": key_edit.text().strip(),
                "column_name": col_edit.text().strip(),
                "question": q_text.toPlainText().strip(),
            }

        def validate(item: dict) -> bool:
            if not item.get("key"):
                QMessageBox.critical(dialog, t("error"), t("key_cannot_empty"))
                return False
            if not item.get("column_name"):
                QMessageBox.critical(dialog, t("error"), t("column_name_cannot_empty"))
                return False
            if not item.get("question"):
                QMessageBox.critical(dialog, t("error"), t("question_cannot_empty"))
                return False
            return True

        def add_to_list(target_list: QListWidget, key_prefix: str):
            item = read_fields()
            if not validate(item):
                return
            QListWidgetItem(item["question"], target_list)
            mode_data.setdefault(f"{key_prefix}", []).append(item)

        def on_add_open():
            add_to_list(open_list, "open_questions")

        def on_add_yn():
            add_to_list(yn_list, "yes_no_questions")

        def on_edit():
            # Determine which list has selection
            target = open_list if open_list.currentRow() >= 0 else yn_list
            key_prefix = "open_questions" if target is open_list else "yes_no_questions"
            idx = target.currentRow()
            if idx < 0:
                QMessageBox.warning(dialog, t("warning"), t("please_select_question"))
                return
            # Preload fields from current selection if empty
            current_items = mode_data.get(key_prefix, [])
            current = current_items[idx] if idx < len(current_items) else {}
            if not key_edit.text().strip():
                key_edit.setText(current.get("key", ""))
            if not col_edit.text().strip():
                col_edit.setText(current.get("column_name", ""))
            if not q_text.toPlainText().strip():
                q_text.setPlainText(current.get("question", ""))

            item = read_fields()
            if not validate(item):
                return
            # Update data
            mode_data.setdefault(key_prefix, [])
            mode_data[key_prefix][idx] = item
            target.item(idx).setText(item["question"])

        def load_selection_to_fields():
            # Keep selection exclusive and populate fields with selected item
            if open_list.currentRow() >= 0:
                yn_list.clearSelection()
                idx = open_list.currentRow()
                data_list = mode_data.get("open_questions", [])
            elif yn_list.currentRow() >= 0:
                open_list.clearSelection()
                idx = yn_list.currentRow()
                data_list = mode_data.get("yes_no_questions", [])
            else:
                return
            if 0 <= idx < len(data_list):
                d = data_list[idx]
                key_edit.setText(d.get("key", ""))
                col_edit.setText(d.get("column_name", ""))
                q_text.setPlainText(d.get("question", ""))

        open_list.currentRowChanged.connect(lambda _: load_selection_to_fields())
        yn_list.currentRowChanged.connect(lambda _: load_selection_to_fields())
        open_list.itemDoubleClicked.connect(lambda _: load_selection_to_fields())
        yn_list.itemDoubleClicked.connect(lambda _: load_selection_to_fields())

        def on_delete():
            target = open_list if open_list.currentRow() >= 0 else yn_list
            key_prefix = "open_questions" if target is open_list else "yes_no_questions"
            idx = target.currentRow()
            if idx < 0:
                return
            mode_data.setdefault(key_prefix, [])
            del mode_data[key_prefix][idx]
            target.takeItem(idx)

        def on_save():
            # Persist to file
            try:
                # Ensure outer structure
                all_data = data
                all_data[mode] = {
                    "description": mode_data.get("description", ""),
                    "open_questions": mode_data.get("open_questions", []),
                    "yes_no_questions": mode_data.get("yes_no_questions", []),
                }
                with q_path.open("w", encoding="utf-8") as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                QMessageBox.information(dialog, t("success"), t("question_config_saved"))
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, t("error"), t("save_question_config_failed", error=str(e)))

        def on_cancel():
            dialog.reject()

        add_open.clicked.connect(on_add_open)
        add_yn.clicked.connect(on_add_yn)
        edit_btn.clicked.connect(on_edit)
        del_btn.clicked.connect(on_delete)
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(on_cancel)

        # Select first item to prefill if available
        if open_list.count() > 0:
            open_list.setCurrentRow(0)
        elif yn_list.count() > 0:
            yn_list.setCurrentRow(0)

        dialog.resize(760, 480)
        dialog.exec()

    def open_ai_mode_assistant(self) -> None:
        """Launch AI assistant to generate a new screening mode and save it."""
        dlg = AIModeAssistantDialog(self, self.parent_window.build_config())
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result:
            try:
                # Load existing config
                import json
                q_path = self._questions_path()
                try:
                    with open(q_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    data = {}

                mode = dlg.result
                # Normalize: support new schema (mode_name/criteria/questions)
                def _slugify(s: str) -> str:
                    s = s or 'new_mode'
                    out = []
                    for ch in s:
                        out.append(ch.lower() if ch.isalnum() else '_')
                    slug = ''.join(out).strip('_')
                    while '__' in slug:
                        slug = slug.replace('__', '_')
                    return slug or 'new_mode'

                if 'mode_name' in mode or 'criteria' in mode or 'questions' in mode:
                    key = _slugify(mode.get('mode_name', 'new_mode'))
                    yes_no_questions = []
                    for it in mode.get('criteria', []) or []:
                        if isinstance(it, dict):
                            yes_no_questions.append({
                                'key': it.get('key', ''),
                                'question': it.get('question', ''),
                                'column_name': it.get('column_name', ''),
                            })
                    open_questions = []
                    for it in mode.get('questions', []) or []:
                        if isinstance(it, dict):
                            open_questions.append({
                                'key': it.get('key', ''),
                                'question': it.get('question', ''),
                                'column_name': it.get('column_name', ''),
                            })
                    legacy_mode = {
                        'description': mode.get('description', ''),
                        'yes_no_questions': yes_no_questions,
                        'open_questions': open_questions,
                    }
                else:
                    # Legacy schema path
                    key = mode.get('mode_key', 'new_mode')
                    legacy_mode = {
                        'description': mode.get('description', ''),
                        'yes_no_questions': mode.get('yes_no_questions', []),
                        'open_questions': mode.get('open_questions', []),
                    }
                if key in data:
                    # Custom dialog with localized buttons
                    box = QMessageBox(self)
                    box.setIcon(QMessageBox.Icon.Warning)
                    box.setWindowTitle(t("conflict_mode_key", key=key) or f"Key exists: {key}")
                    box.setText(t("choose_action") or "Choose action")
                    overwrite_btn = box.addButton(t("overwrite") or "Overwrite", QMessageBox.ButtonRole.AcceptRole)
                    rename_btn = box.addButton(t("rename") or "Rename", QMessageBox.ButtonRole.ActionRole)
                    cancel_btn = box.addButton(t("cancel") or "Cancel", QMessageBox.ButtonRole.RejectRole)
                    box.exec()
                    clicked = box.clickedButton()
                    if clicked == cancel_btn:
                        return
                    elif clicked == rename_btn:
                        suffix = 1
                        while f"{key}_{suffix}" in data:
                            suffix += 1
                        key = f"{key}_{suffix}"
                        mode['mode_key'] = key
                        do_backup = False
                    else:
                        # overwrite with backup
                        do_backup = True
                else:
                    do_backup = False

                data[key] = legacy_mode
                self._write_questions_config(data, backup=do_backup)

                # refresh combo
                self._load_modes()
                self.mode_combo.clear(); self.mode_combo.addItems(self.mode_options)
                idx = self.mode_combo.findText(key)
                if idx >= 0:
                    self.mode_combo.setCurrentIndex(idx)
                QMessageBox.information(self, t("success") or "Success", t("saved") or "Saved")
            except Exception as e:
                QMessageBox.critical(self, t("error") or "Error", str(e))

    def show_statistics(self) -> None:
        """Show statistics summary for current results and mode."""
        if self.df is None:
            QMessageBox.information(self, t("hint"), t("please_complete_screening"))
            return
        # Load questions for mode
        mode = self.mode_combo.currentText().strip()
        q = load_mode_questions(mode)
        screener = AbstractScreener(self.parent_window.build_config())
        stats = screener.generate_statistics(self.df, q.get("open_questions", []), q.get("yes_no_questions", []))

        # Render as simple text
        lines = [t("statistics_summary", count=stats.get('total_articles', 0))]
        for qtext, counts in stats.get('yes_no_results', {}).items():
            lines.append(f"- {qtext}: 是 {counts.get('是', 0)}, 否 {counts.get('否', 0)}, 不确定 {counts.get('不确定', 0)}")
        for qtext, oc in stats.get('open_question_stats', {}).items():
            lines.append(f"- {qtext}: answered {oc.get('answered', 0)}, missing {oc.get('missing', 0)}")

        QMessageBox.information(self, t("screening_statistics"), "\n".join(lines))

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
