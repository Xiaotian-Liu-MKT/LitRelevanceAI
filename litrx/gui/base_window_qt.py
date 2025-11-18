"""PyQt6-based base window for LitRelevanceAI GUI."""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
)
from PyQt6.QtGui import QFont

from ..config import DEFAULT_CONFIG as BASE_CONFIG, load_config, load_env_file
from ..i18n import get_i18n, t

try:
    import yaml
except ImportError:
    yaml = None

try:
    from ..key_manager import get_key_manager, KEY_OPENAI, KEY_SILICONFLOW
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Load environment variables from .env
load_env_file()

PERSIST_PATH = Path.home() / ".litrx_gui.yaml"
PROMPTS_PATH = Path(__file__).resolve().parents[2] / "prompts_config.json"


class BaseWindow(QMainWindow):
    """Base window providing shared config controls and tab manager."""

    def __init__(self) -> None:
        super().__init__()

        # Initialize i18n and load saved language preference
        repo_root = Path(__file__).resolve().parents[2]
        config_path = repo_root / "configs" / "config.yaml"

        # Start with defaults from config.yaml then layer in persisted config
        self.base_config: Dict[str, str] = load_config(str(config_path), BASE_CONFIG)
        self.base_config = load_config(str(PERSIST_PATH), self.base_config)

        # Load language preference (default to English for first-time users)
        saved_lang = self.base_config.get("LANGUAGE", "en")
        normalized_lang = self._normalize_language_code(saved_lang)
        if normalized_lang != saved_lang:
            self.base_config["LANGUAGE"] = normalized_lang

        self.i18n = get_i18n(normalized_lang)
        if self.i18n.current_language != normalized_lang:
            self.i18n.current_language = normalized_lang

        # Load API keys from keyring (secure storage)
        if KEYRING_AVAILABLE:
            key_manager = get_key_manager()

            if not self.base_config.get("OPENAI_API_KEY"):
                openai_key = key_manager.get_key(KEY_OPENAI)
                if openai_key:
                    self.base_config["OPENAI_API_KEY"] = openai_key

            if not self.base_config.get("SILICONFLOW_API_KEY"):
                siliconflow_key = key_manager.get_key(KEY_SILICONFLOW)
                if siliconflow_key:
                    self.base_config["SILICONFLOW_API_KEY"] = siliconflow_key

        # Environment variables have highest priority
        for key in [
            "AI_SERVICE",
            "MODEL_NAME",
            "OPENAI_API_KEY",
            "SILICONFLOW_API_KEY",
            "API_BASE",
        ]:
            env_val = os.getenv(key)
            if env_val:
                self.base_config[key] = env_val

        # Set up main window
        self.setWindowTitle(t("app_title"))
        self.resize(1000, 700)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(5)

        # Apply modern styling
        self.setup_styles()

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel(t("title_label"))
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(t("subtitle_label"))
        subtitle_font = QFont("Segoe UI", 9)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet("color: #7f8c8d; margin-left: 10px;")
        header_layout.addWidget(self.subtitle_label)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Configuration Group
        self.config_group = QGroupBox(t("config_settings"))
        config_layout = QVBoxLayout()
        config_layout.setSpacing(8)

        # Row 1: Service and API Key
        row1 = QHBoxLayout()
        self.service_label = QLabel(t("ai_service"))
        self.service_label.setMinimumWidth(100)
        row1.addWidget(self.service_label)

        self.service_combo = QComboBox()
        self.service_combo.addItems(["openai", "siliconflow"])
        self.service_combo.setCurrentText(self.base_config.get("AI_SERVICE", "openai"))
        self.service_combo.setMaximumWidth(150)
        self.current_service = self.service_combo.currentText()
        self.service_combo.currentTextChanged.connect(self.on_service_change)
        row1.addWidget(self.service_combo)

        row1.addSpacing(15)

        self.api_key_label = QLabel(t("api_key"))
        row1.addWidget(self.api_key_label)

        self.api_key_entry = QLineEdit()
        self.api_key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        if self.current_service == "openai":
            initial_key = self.base_config.get("OPENAI_API_KEY", "")
        else:
            initial_key = self.base_config.get("SILICONFLOW_API_KEY", "")
        self.api_key_entry.setText(initial_key)
        self.api_key_entry.setMinimumWidth(300)
        row1.addWidget(self.api_key_entry)
        row1.addStretch()

        config_layout.addLayout(row1)

        # Row 2: Model, Language and Buttons
        row2 = QHBoxLayout()
        self.model_label = QLabel(t("model"))
        self.model_label.setMinimumWidth(100)
        row2.addWidget(self.model_label)

        self.model_entry = QLineEdit()
        self.model_entry.setText(self.base_config.get("MODEL_NAME", ""))
        self.model_entry.setMaximumWidth(200)
        row2.addWidget(self.model_entry)

        row2.addSpacing(10)

        self.language_label = QLabel(t("language"))
        row2.addWidget(self.language_label)

        self.language_combo = QComboBox()
        # Will be updated by _update_language_display()
        self.language_combo.currentTextChanged.connect(self.on_language_change)
        self.language_combo.setMaximumWidth(120)
        row2.addWidget(self.language_combo)

        row2.addSpacing(10)

        self.save_button = QPushButton(t("save_config"))
        self.save_button.clicked.connect(self.save_config)
        self.save_button.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 5px 15px; }")
        row2.addWidget(self.save_button)

        self.prompt_button = QPushButton(t("prompt_settings"))
        self.prompt_button.clicked.connect(self.open_prompt_settings)
        self.prompt_button.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; padding: 5px 15px; }")
        row2.addWidget(self.prompt_button)

        self.view_logs_button = QPushButton(t("view_logs"))
        self.view_logs_button.clicked.connect(self.open_log_viewer)
        self.view_logs_button.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; padding: 5px 15px; }")
        row2.addWidget(self.view_logs_button)

        row2.addStretch()

        config_layout.addLayout(row2)
        self.config_group.setLayout(config_layout)
        main_layout.addWidget(self.config_group)

        # Tab Widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Update language display and register observer
        self._update_language_display()
        self.i18n.add_observer(self._on_language_changed)

    def setup_styles(self) -> None:
        """Configure modern styling for the application."""
        app_stylesheet = """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
            }
            QPushButton {
                border-radius: 3px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
        """
        self.setStyleSheet(app_stylesheet)

    @staticmethod
    def _normalize_language_code(lang_value: str) -> str:
        """Return a supported language code for the provided value."""
        if not lang_value:
            return "en"

        raw_value = lang_value.strip()
        lowered_value = raw_value.lower()
        normalized_value = lowered_value.replace("_", "-")

        mapping = {
            "zh": "zh",
            "zh-cn": "zh",
            "zh_cn": "zh",
            "zh-hans": "zh",
            "chinese": "zh",
            "中文": "zh",
            "简体中文": "zh",
            "en": "en",
            "en-us": "en",
            "en_us": "en",
            "en-gb": "en",
            "english": "en",
            "英文": "en",
        }

        return mapping.get(raw_value, mapping.get(lowered_value, mapping.get(normalized_value, "en")))

    def build_config(self) -> Dict[str, str]:
        """Build current configuration from UI widgets."""
        config = self.base_config.copy()
        service = self.service_combo.currentText()
        config["AI_SERVICE"] = service
        api_key = self.api_key_entry.text().strip()
        if service == "openai" and api_key:
            config["OPENAI_API_KEY"] = api_key
        elif service == "siliconflow" and api_key:
            config["SILICONFLOW_API_KEY"] = api_key
        model = self.model_entry.text().strip()
        if model:
            config["MODEL_NAME"] = model
        config["LANGUAGE"] = self.i18n.current_language
        self.base_config.update(config)
        return config

    def browse_file(self, line_edit: QLineEdit, file_filter: str) -> None:
        """Open file dialog and set selected path to line edit."""
        file_path, _ = QFileDialog.getOpenFileName(self, t("browse"), "", file_filter)
        if file_path:
            line_edit.setText(file_path)

    def browse_folder(self, line_edit: QLineEdit) -> None:
        """Open folder dialog and set selected path to line edit."""
        folder_path = QFileDialog.getExistingDirectory(self, t("browse"))
        if folder_path:
            line_edit.setText(folder_path)

    def save_config(self) -> None:
        """Persist current configuration to ~/.litrx_gui.yaml."""
        config = self.build_config()
        if yaml is None:
            QMessageBox.critical(self, t("error"), "pyyaml is required to save configuration")
            return

        # Save API keys to secure keyring
        if KEYRING_AVAILABLE:
            key_manager = get_key_manager()

            openai_key = config.get("OPENAI_API_KEY", "")
            if openai_key:
                key_manager.set_key(KEY_OPENAI, openai_key)

            siliconflow_key = config.get("SILICONFLOW_API_KEY", "")
            if siliconflow_key:
                key_manager.set_key(KEY_SILICONFLOW, siliconflow_key)

        # Save non-sensitive config to YAML
        data = {
            key: config.get(key, "")
            for key in ["AI_SERVICE", "MODEL_NAME", "API_BASE", "LANGUAGE"]
        }

        # Migrate old plaintext keys to keyring
        try:
            if PERSIST_PATH.exists():
                with PERSIST_PATH.open("r", encoding="utf-8") as f:
                    old_config = yaml.safe_load(f) or {}
                if KEYRING_AVAILABLE and (
                    old_config.get("OPENAI_API_KEY") or old_config.get("SILICONFLOW_API_KEY")
                ):
                    key_manager = get_key_manager()
                    if old_config.get("OPENAI_API_KEY"):
                        key_manager.set_key(KEY_OPENAI, old_config["OPENAI_API_KEY"])
                    if old_config.get("SILICONFLOW_API_KEY"):
                        key_manager.set_key(KEY_SILICONFLOW, old_config["SILICONFLOW_API_KEY"])
        except Exception:
            pass

        try:
            with PERSIST_PATH.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

            if KEYRING_AVAILABLE:
                QMessageBox.information(
                    self,
                    t("saved"),
                    t("config_saved", path=str(PERSIST_PATH)) + "\n\n" + t("api_keys_secured")
                )
            else:
                QMessageBox.warning(
                    self,
                    t("saved"),
                    t("config_saved", path=str(PERSIST_PATH)) +
                    "\n\nWarning: keyring library not available. API keys cannot be stored securely. "
                    "Please install keyring: pip install keyring"
                )
        except Exception as e:
            QMessageBox.critical(self, t("error"), t("save_failed", error=str(e)))

    def on_service_change(self, new_service: str) -> None:
        """Handle AI service change."""
        # Save current API key before switching
        if self.current_service == "openai":
            self.base_config["OPENAI_API_KEY"] = self.api_key_entry.text().strip()
        elif self.current_service == "siliconflow":
            self.base_config["SILICONFLOW_API_KEY"] = self.api_key_entry.text().strip()

        # Switch to new service and load its API key
        self.current_service = new_service
        if self.current_service == "openai":
            self.api_key_entry.setText(self.base_config.get("OPENAI_API_KEY", ""))
        elif self.current_service == "siliconflow":
            self.api_key_entry.setText(self.base_config.get("SILICONFLOW_API_KEY", ""))

    def on_language_change(self, display_text: str) -> None:
        """Handle language selection change."""
        # Map display text back to language code
        lang_map = {
            t("lang_chinese"): "zh",
            t("lang_english"): "en",
            "中文": "zh",
            "English": "en"
        }

        new_lang = lang_map.get(display_text, "en")

        if new_lang != self.i18n.current_language:
            self.i18n.current_language = new_lang
            self._update_language_display()
            self.base_config["LANGUAGE"] = new_lang

    def _update_language_display(self) -> None:
        """Update the language combobox to show language names."""
        lang_display = {
            "zh": t("lang_chinese"),
            "en": t("lang_english")
        }
        current_code = self.i18n.current_language
        display_values = [lang_display["zh"], lang_display["en"]]

        # Block signals to prevent triggering on_language_change
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        self.language_combo.addItems(display_values)
        self.language_combo.setCurrentText(lang_display.get(current_code, lang_display["en"]))
        self.language_combo.blockSignals(False)

    def _on_language_changed(self) -> None:
        """Called when language is changed to update all UI text."""
        self.setWindowTitle(t("app_title"))
        self.title_label.setText(t("title_label"))
        self.subtitle_label.setText(t("subtitle_label"))
        self.config_group.setTitle(t("config_settings"))
        self.service_label.setText(t("ai_service"))
        self.api_key_label.setText(t("api_key"))
        self.model_label.setText(t("model"))
        self.language_label.setText(t("language"))
        self.save_button.setText(t("save_config"))
        self.prompt_button.setText(t("prompt_settings"))
        self.view_logs_button.setText(t("view_logs"))
        self._update_language_display()

    def open_prompt_settings(self) -> None:
        """Open the prompt settings dialog."""
        dialog = PromptSettingsDialog(self)
        dialog.exec()

    def open_log_viewer(self) -> None:
        """Open a window to view application logs."""
        dialog = LogViewerDialog(self)
        dialog.exec()

    def _get_default_prompts(self) -> dict:
        """Get default prompt templates."""
        return {
            "csv_analysis": {
                "main_prompt": "Please analyze the relevance of the following paper to the research topic \"{research_topic}\":\n\nTitle: {title}\nAbstract: {abstract}\n\nPlease provide the following information:\n1. Relevance analysis (detailed explanation of the connection between the paper and the research topic)\n2. A relevance score from 0-100, where 0 means completely unrelated and 100 means highly relevant\n3. If this paper were to be included in a literature review on the research topic, how should it be cited and discussed? Please tell me directly how you would write it.\n\nPlease return in the following JSON format:\n{{\n    \"relevance_score\": <number>,\n    \"analysis\": \"<analysis text>\",\n    \"literature_review_suggestion\": \"<literature review suggestion>\"\n}}"
            },
            "abstract_screening": {
                "detailed_prompt": "请仔细阅读以下文献的标题和摘要,并结合给定的理论模型/研究问题进行分析。\n请严格按照以下JSON格式返回您的分析结果,所有文本内容请使用中文:\n\n文献标题:{title}\n文献摘要:{abstract}\n\n理论模型/研究问题:{research_question}\n\nJSON输出格式要求:\n{{\n{detailed_analysis_section}\n    \"screening_results\": {{\n{criteria_prompts_str}\n    }}\n}}\n\n重要提示:\n1.  对于 \"detailed_analysis\" 内的每一个子问题(如果存在),请提供简洁、针对性的中文回答。如果摘要中信息不足以回答某个子问题,请注明\"摘要未提供相关信息\"。\n2.  对于 \"screening_results\" 中的每一个筛选条件,请仅使用 \"是\"、\"否\" 或 \"不确定\" 作为回答。\n3.  确保整个输出是一个合法的JSON对象。",
                "quick_prompt": "请快速分析以下文献的标题和摘要,帮助进行每周文献筛选:\n\n文献标题:{title}\n文献摘要:{abstract}\n\n请按以下JSON格式回答:\n{{\n    \"quick_analysis\": {{\n{open_q_str}\n    }},\n    \"screening_results\": {{\n{yes_no_str}\n    }}\n}}",
                "verification_prompt": "请根据以下文献标题和摘要,核对AI之前的回答是否与文献内容一致。\n文献标题:{title}\n文献摘要:{abstract}\n\n问题与AI初始回答如下:\n{verification_data}\n\n请判断每个回答是否得到标题或摘要支持。如支持回答\"是\",不支持回答\"否\",无法判断回答\"不确定\"。请按如下JSON格式返回:\n{{\n    \"quick_analysis\": {{{open_keys}}},\n    \"screening_results\": {{{yes_no_keys}}}\n}}"
            },
            "pdf_screening": {
                "main_prompt": "请阅读所提供的文献并根据研究问题进行分析。请严格按照以下JSON格式以中文回答:\n{{{da_section}\n    \"screening_results\": {{\n{criteria_str}\n    }}\n}}"
            }
        }


class PromptSettingsDialog(QDialog):
    """Dialog for editing prompt templates."""

    def __init__(self, parent: BaseWindow):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(t("prompt_settings_title"))
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Load current prompts
        try:
            with PROMPTS_PATH.open("r", encoding="utf-8") as f:
                prompts = json.load(f)
        except Exception:
            prompts = parent._get_default_prompts()

        # Create tab widget for different prompt categories
        self.tab_widget = QTabWidget()
        self.text_widgets = {}

        # CSV Analysis Tab
        csv_widget = QWidget()
        self.text_widgets["csv_analysis"] = self._create_prompt_editor(
            csv_widget, prompts.get("csv_analysis", {})
        )
        self.tab_widget.addTab(csv_widget, t("csv_analysis"))

        # Abstract Screening Tab
        abstract_widget = QWidget()
        self.text_widgets["abstract_screening"] = self._create_prompt_editor(
            abstract_widget, prompts.get("abstract_screening", {})
        )
        self.tab_widget.addTab(abstract_widget, t("abstract_screening"))

        # PDF Screening Tab
        pdf_widget = QWidget()
        self.text_widgets["pdf_screening"] = self._create_prompt_editor(
            pdf_widget, prompts.get("pdf_screening", {})
        )
        self.tab_widget.addTab(pdf_widget, t("pdf_screening"))

        layout.addWidget(self.tab_widget)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_prompts)
        button_box.rejected.connect(self.reject)

        reset_button = QPushButton(t("reset_defaults"))
        reset_button.clicked.connect(self.reset_defaults)
        button_box.addButton(reset_button, QDialogButtonBox.ButtonRole.ResetRole)

        layout.addWidget(button_box)

    def _create_prompt_editor(self, parent: QWidget, prompts_dict: dict) -> dict:
        """Create prompt editor widgets and return dictionary of text widgets."""
        layout = QVBoxLayout(parent)
        text_widgets = {}

        for key, value in prompts_dict.items():
            group = QGroupBox(key.replace("_", " ").title())
            group_layout = QVBoxLayout()

            text_edit = QTextEdit()
            text_edit.setPlainText(value)
            text_edit.setMinimumHeight(150)
            font = QFont("Consolas", 9)
            text_edit.setFont(font)

            group_layout.addWidget(text_edit)
            group.setLayout(group_layout)
            layout.addWidget(group)

            text_widgets[key] = text_edit

        return text_widgets

    def save_prompts(self) -> None:
        """Save prompt templates to file."""
        try:
            updated_prompts = {}
            for category, widgets in self.text_widgets.items():
                updated_prompts[category] = {}
                for key, text_widget in widgets.items():
                    updated_prompts[category][key] = text_widget.toPlainText().strip()

            with PROMPTS_PATH.open("w", encoding="utf-8") as f:
                json.dump(updated_prompts, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, t("success"), t("prompt_saved"))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, t("error"), t("save_failed", error=str(e)))

    def reset_defaults(self) -> None:
        """Reset prompts to default values."""
        reply = QMessageBox.question(
            self,
            t("confirm"),
            t("reset_prompt_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            default_prompts = self.parent_window._get_default_prompts()
            try:
                with PROMPTS_PATH.open("w", encoding="utf-8") as f:
                    json.dump(default_prompts, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, t("success"), t("reset_success"))
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, t("error"), t("reset_failed", error=str(e)))


class LogViewerDialog(QDialog):
    """Dialog for viewing application logs."""

    def __init__(self, parent: BaseWindow):
        super().__init__(parent)
        self.setWindowTitle(t("view_logs"))
        self.resize(900, 600)

        layout = QVBoxLayout(self)

        # Text widget
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        # Load log file
        self.log_file = Path.home() / ".litrx" / "logs" / "litrx.log"
        self.load_logs()

        # Buttons
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_logs)
        button_layout.addWidget(refresh_button)

        open_folder_button = QPushButton("Open Log Folder")
        open_folder_button.clicked.connect(self.open_log_folder)
        button_layout.addWidget(open_folder_button)

        button_layout.addStretch()

        close_button = QPushButton(t("close"))
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def load_logs(self) -> None:
        """Load and display log file content."""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.log_text.setPlainText(content)
                # Scroll to end
                cursor = self.log_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.log_text.setTextCursor(cursor)
            else:
                self.log_text.setPlainText("Log file not found. No logs have been generated yet.")
        except Exception as e:
            self.log_text.setPlainText(f"Error reading log file: {e}")

    def open_log_folder(self) -> None:
        """Open log folder in file explorer."""
        import platform

        log_dir = self.log_file.parent
        if not log_dir.exists():
            QMessageBox.warning(self, t("warning"), "Log directory does not exist yet.")
            return

        try:
            if platform.system() == "Windows":
                os.startfile(log_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", log_dir])
            else:  # Linux
                subprocess.run(["xdg-open", log_dir])
        except Exception as e:
            QMessageBox.critical(self, t("error"), f"Failed to open folder: {e}")
