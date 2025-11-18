import json
import os
import platform

from ..tk_compat import ensure_native_macos_version

# Fix for macOS Tk version check issue
# On newer macOS versions (e.g., Sequoia), Tk's version check can fail with errors like:
# "macOS 26 (2600) or later required, have instead 16 (1600)"
# This environment variable disables the strict version check
# MUST be set before importing tkinter
ensure_native_macos_version()

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict

from ..config import DEFAULT_CONFIG as BASE_CONFIG, load_config, load_env_file
from ..i18n import get_i18n, t

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - handle missing pyyaml
    yaml = None

try:
    from ..key_manager import get_key_manager, KEY_OPENAI, KEY_SILICONFLOW
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Load environment variables from .env so they can override other sources
load_env_file()

PERSIST_PATH = Path.home() / ".litrx_gui.yaml"
PROMPTS_PATH = Path(__file__).resolve().parents[2] / "prompts_config.json"


class BaseWindow:
    """Base window providing shared config controls and notebook manager."""

    def __init__(self) -> None:
        self.root = tk.Tk()

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
            # Set the initial language before observers are registered so UI setup
            # uses the correct translations without triggering callbacks early.
            self.i18n.current_language = normalized_lang

        self.root.title(t("app_title"))
        self.root.geometry("1000x700")

        # Configure modern styling
        self.setup_styles()

        # Load API keys from keyring (secure storage)
        if KEYRING_AVAILABLE:
            key_manager = get_key_manager()

            # Load keys from keyring if not already in config
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

        # Header Frame
        self.header = ttk.Frame(self.root, style="Header.TFrame")
        self.header.pack(fill=tk.X, padx=15, pady=(10, 5))

        self.title_label = ttk.Label(self.header, text=t("title_label"), style="Title.TLabel")
        self.title_label.pack(side=tk.LEFT)

        self.subtitle_label = ttk.Label(self.header, text=t("subtitle_label"), style="Subtitle.TLabel")
        self.subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

        # Configuration Frame
        self.config_frame = ttk.LabelFrame(self.root, text=t("config_settings"), style="Config.TLabelframe")
        self.config_frame.pack(fill=tk.X, padx=15, pady=(5, 10))

        # Row 1: Service and API Key
        self.row1 = ttk.Frame(self.config_frame)
        self.row1.pack(fill=tk.X, padx=10, pady=8)

        self.service_label = ttk.Label(self.row1, text=t("ai_service"), width=12)
        self.service_label.pack(side=tk.LEFT)
        self.service_var = tk.StringVar(
            value=self.base_config.get("AI_SERVICE", "openai")
        )
        service_menu = ttk.Combobox(
            self.row1,
            textvariable=self.service_var,
            values=["openai", "siliconflow"],
            width=15,
            state="readonly",
        )
        service_menu.pack(side=tk.LEFT, padx=(0, 15))
        self.current_service = self.service_var.get()
        service_menu.bind("<<ComboboxSelected>>", self.on_service_change)

        self.api_key_label = ttk.Label(self.row1, text=t("api_key"))
        self.api_key_label.pack(side=tk.LEFT, padx=(0, 5))
        if self.current_service == "openai":
            initial_key = self.base_config.get("OPENAI_API_KEY", "")
        else:  # siliconflow
            initial_key = self.base_config.get("SILICONFLOW_API_KEY", "")
        self.api_key_var = tk.StringVar(value=initial_key)
        ttk.Entry(self.row1, textvariable=self.api_key_var, width=45, show="*").pack(
            side=tk.LEFT, padx=5
        )

        # Row 2: Model, Language and Buttons
        self.row2 = ttk.Frame(self.config_frame)
        self.row2.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.model_label = ttk.Label(self.row2, text=t("model"), width=12)
        self.model_label.pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self.base_config.get("MODEL_NAME", ""))
        ttk.Entry(self.row2, textvariable=self.model_var, width=20).pack(side=tk.LEFT, padx=(0, 10))

        self.language_label = ttk.Label(self.row2, text=t("language"))
        self.language_label.pack(side=tk.LEFT, padx=(0, 5))
        self.language_var = tk.StringVar(value=self.i18n.current_language)
        self.language_menu = ttk.Combobox(
            self.row2,
            textvariable=self.language_var,
            values=["zh", "en"],
            width=8,
            state="readonly",
        )
        self.language_menu.pack(side=tk.LEFT, padx=(0, 10))
        self.language_menu.bind("<<ComboboxSelected>>", self.on_language_change)
        # Update display to show language names
        self._update_language_display()

        self.save_button = ttk.Button(self.row2, text=t("save_config"), command=self.save_config, style="Primary.TButton")
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.prompt_button = ttk.Button(self.row2, text=t("prompt_settings"), command=self.open_prompt_settings, style="Secondary.TButton")
        self.prompt_button.pack(side=tk.LEFT, padx=5)
        self.view_logs_button = ttk.Button(self.row2, text=t("view_logs"), command=self.open_log_viewer, style="Secondary.TButton")
        self.view_logs_button.pack(side=tk.LEFT, padx=5)

        self.notebook = ttk.Notebook(self.root, style="Main.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        # Register language change observer after UI widgets have been created.
        self.i18n.add_observer(self._on_language_changed)

    def setup_styles(self) -> None:
        """Configure modern ttk styles."""
        style = ttk.Style()

        # Configure colors
        bg_color = "#f5f5f5"
        header_bg = "#2c3e50"
        primary_color = "#3498db"
        secondary_color = "#95a5a6"

        # Configure root background
        self.root.configure(bg=bg_color)

        # Header styles
        style.configure("Header.TFrame", background=bg_color)
        style.configure("Title.TLabel", background=bg_color, foreground="#2c3e50",
                       font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background=bg_color, foreground="#7f8c8d",
                       font=("Segoe UI", 9))

        # Config frame styles
        style.configure("Config.TLabelframe", background=bg_color, relief="solid")
        style.configure("Config.TLabelframe.Label", background=bg_color,
                       font=("Segoe UI", 9, "bold"))

        # Button styles
        style.configure("Primary.TButton", font=("Segoe UI", 9))
        style.configure("Secondary.TButton", font=("Segoe UI", 9))

        # Notebook style
        style.configure("Main.TNotebook", background=bg_color)
        style.configure("TNotebook.Tab", font=("Segoe UI", 9), padding=[20, 8])

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
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
        config = self.base_config.copy()
        service = self.service_var.get()
        config["AI_SERVICE"] = service
        api_key = self.api_key_var.get().strip()
        if service == "openai" and api_key:
            config["OPENAI_API_KEY"] = api_key
        elif service == "siliconflow" and api_key:
            config["SILICONFLOW_API_KEY"] = api_key
        model = self.model_var.get().strip()
        if model:
            config["MODEL_NAME"] = model
        # Persist the actual language code rather than the localized display name
        config["LANGUAGE"] = self.i18n.current_language
        self.base_config.update(config)
        return config

    def browse_file(self, var: tk.StringVar, filetypes):
        path = filedialog.askopenfilename(filetypes=[filetypes])
        if path:
            var.set(path)

    def browse_folder(self, var: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def save_config(self) -> None:
        """Persist current configuration to ``~/.litrx_gui.yaml``.

        API keys are now stored securely in the system keyring instead of
        the YAML file for improved security.
        """

        config = self.build_config()
        if yaml is None:
            messagebox.showerror(
                t("error"), "pyyaml is required to save configuration"
            )
            return

        # Save API keys to secure keyring
        if KEYRING_AVAILABLE:
            key_manager = get_key_manager()

            # Save OpenAI key to keyring
            openai_key = config.get("OPENAI_API_KEY", "")
            if openai_key:
                key_manager.set_key(KEY_OPENAI, openai_key)

            # Save SiliconFlow key to keyring
            siliconflow_key = config.get("SILICONFLOW_API_KEY", "")
            if siliconflow_key:
                key_manager.set_key(KEY_SILICONFLOW, siliconflow_key)

        # Save non-sensitive config to YAML (excluding API keys)
        data = {
            key: config.get(key, "")
            for key in [
                "AI_SERVICE",
                "MODEL_NAME",
                "API_BASE",
                "LANGUAGE",
            ]
        }

        # Migrate: if old config has plaintext keys, try to migrate them
        try:
            if PERSIST_PATH.exists():
                with PERSIST_PATH.open("r", encoding="utf-8") as f:
                    old_config = yaml.safe_load(f) or {}
                if KEYRING_AVAILABLE and (
                    old_config.get("OPENAI_API_KEY") or old_config.get("SILICONFLOW_API_KEY")
                ):
                    key_manager = get_key_manager()
                    # Migrate old plaintext keys to keyring
                    if old_config.get("OPENAI_API_KEY"):
                        key_manager.set_key(KEY_OPENAI, old_config["OPENAI_API_KEY"])
                    if old_config.get("SILICONFLOW_API_KEY"):
                        key_manager.set_key(KEY_SILICONFLOW, old_config["SILICONFLOW_API_KEY"])
        except Exception:
            pass  # Migration is best-effort

        try:
            with PERSIST_PATH.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)
        except Exception as e:  # pragma: no cover - user feedback
            messagebox.showerror(t("error"), t("save_failed", error=str(e)))
        else:  # pragma: no cover - user feedback
            if KEYRING_AVAILABLE:
                messagebox.showinfo(
                    t("saved"),
                    t("config_saved", path=str(PERSIST_PATH)) +
                    "\n\n" + t("api_keys_secured")
                )
            else:
                messagebox.showwarning(
                    t("saved"),
                    t("config_saved", path=str(PERSIST_PATH)) +
                    "\n\nWarning: keyring library not available. API keys cannot be stored securely. "
                    "Please install keyring: pip install keyring"
                )

    def on_service_change(self, event=None) -> None:
        # Save current API key before switching
        if self.current_service == "openai":
            self.base_config["OPENAI_API_KEY"] = self.api_key_var.get().strip()
        elif self.current_service == "siliconflow":
            self.base_config["SILICONFLOW_API_KEY"] = self.api_key_var.get().strip()

        # Switch to new service and load its API key
        self.current_service = self.service_var.get()
        if self.current_service == "openai":
            self.api_key_var.set(self.base_config.get("OPENAI_API_KEY", ""))
        elif self.current_service == "siliconflow":
            self.api_key_var.set(self.base_config.get("SILICONFLOW_API_KEY", ""))

    def on_language_change(self, event=None) -> None:
        """Handle language selection change."""
        selected = self.language_var.get()
        new_lang = self._normalize_language_code(selected)

        if new_lang != self.i18n.current_language:
            self.i18n.current_language = new_lang
            self._update_language_display()
            self.base_config["LANGUAGE"] = new_lang

    def _update_language_display(self) -> None:
        """Update the language combobox to show language names."""
        # Update combobox display values
        lang_display = {
            "zh": t("lang_chinese"),
            "en": t("lang_english")
        }
        current_code = self.i18n.current_language  # Use actual language code from i18n
        display_values = [lang_display["zh"], lang_display["en"]]
        self.language_menu.config(values=display_values)
        display_value = lang_display.get(current_code, lang_display["en"])
        self.language_menu.set(display_value)
        self.language_var.set(display_value)

    def _on_language_changed(self) -> None:
        """Called when language is changed to update all UI text."""
        # Update window title
        self.root.title(t("app_title"))

        # Update header
        self.title_label.config(text=t("title_label"))
        self.subtitle_label.config(text=t("subtitle_label"))

        # Update config frame
        self.config_frame.config(text=t("config_settings"))
        self.service_label.config(text=t("ai_service"))
        self.api_key_label.config(text=t("api_key"))
        self.model_label.config(text=t("model"))
        self.language_label.config(text=t("language"))
        self.save_button.config(text=t("save_config"))
        self.prompt_button.config(text=t("prompt_settings"))
        self.view_logs_button.config(text=t("view_logs"))

        # Update language display
        self._update_language_display()

        # Notify child tabs to update their UI
        # Child classes should override this if they have additional UI to update

    def open_prompt_settings(self) -> None:
        """Open the prompt settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title(t("prompt_settings_title"))
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # Load current prompts
        try:
            with PROMPTS_PATH.open("r", encoding="utf-8") as f:
                prompts = json.load(f)
        except Exception:
            prompts = self._get_default_prompts()

        # Store text widgets for reading values on save
        text_widgets = {}

        # Create notebook for different prompt categories
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # CSV Analysis Tab
        csv_frame = ttk.Frame(notebook)
        notebook.add(csv_frame, text=t("csv_analysis"))
        text_widgets["csv_analysis"] = self._create_prompt_editor(csv_frame, prompts.get("csv_analysis", {}))

        # Abstract Screening Tab
        abstract_frame = ttk.Frame(notebook)
        notebook.add(abstract_frame, text=t("abstract_screening"))
        text_widgets["abstract_screening"] = self._create_prompt_editor(abstract_frame, prompts.get("abstract_screening", {}))

        # PDF Screening Tab
        pdf_frame = ttk.Frame(notebook)
        notebook.add(pdf_frame, text=t("pdf_screening"))
        text_widgets["pdf_screening"] = self._create_prompt_editor(pdf_frame, prompts.get("pdf_screening", {}))

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def save_prompts():
            try:
                # Collect all prompt values from text widgets
                updated_prompts: Dict[str, Dict[str, str]] = {}
                for category, widgets in text_widgets.items():
                    updated_prompts[category] = {}
                    for key, text_widget in widgets.items():
                        updated_prompts[category][key] = text_widget.get("1.0", tk.END).strip()

                with PROMPTS_PATH.open("w", encoding="utf-8") as f:
                    json.dump(updated_prompts, f, ensure_ascii=False, indent=2)
                messagebox.showinfo(t("success"), t("prompt_saved"), parent=dialog)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror(t("error"), t("save_failed", error=str(e)), parent=dialog)

        def reset_defaults():
            if messagebox.askyesno(t("confirm"), t("reset_prompt_confirm"), parent=dialog):
                # Restore default prompts
                default_prompts = self._get_default_prompts()
                try:
                    with PROMPTS_PATH.open("w", encoding="utf-8") as f:
                        json.dump(default_prompts, f, ensure_ascii=False, indent=2)
                    messagebox.showinfo(t("success"), t("reset_success"), parent=dialog)
                    dialog.destroy()
                    self.open_prompt_settings()  # Reopen dialog with defaults
                except Exception as e:
                    messagebox.showerror(t("error"), t("reset_failed", error=str(e)), parent=dialog)

        ttk.Button(button_frame, text=t("save"), command=save_prompts).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text=t("reset_defaults"), command=reset_defaults).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text=t("cancel"), command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _create_prompt_editor(self, parent, prompts_dict):
        """Create prompt editor widgets and return dictionary of text widgets."""
        text_widgets = {}
        for key, value in prompts_dict.items():
            frame = ttk.LabelFrame(parent, text=key.replace("_", " ").title())
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            text = ScrolledText(frame, wrap=tk.WORD, height=10, font=("Consolas", 9))
            text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            text.insert("1.0", value)

            text_widgets[key] = text

        return text_widgets

    def _get_default_prompts(self):
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

    def open_log_viewer(self) -> None:
        """Open a window to view application logs."""
        from pathlib import Path

        log_file = Path.home() / ".litrx" / "logs" / "litrx.log"

        # Create log viewer window
        viewer = tk.Toplevel(self.root)
        viewer.title(t("view_logs"))
        viewer.geometry("900x600")
        viewer.transient(self.root)

        # Create text widget with scrollbar
        text_frame = ttk.Frame(viewer)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        log_text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=text_scroll.set, font=("Consolas", 9))
        text_scroll.config(command=log_text.yview)

        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Load and display log file
        try:
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                log_text.insert("1.0", content)
                # Scroll to end
                log_text.see(tk.END)
            else:
                log_text.insert("1.0", "Log file not found. No logs have been generated yet.")
        except Exception as e:
            log_text.insert("1.0", f"Error reading log file: {e}")

        log_text.config(state=tk.DISABLED)

        # Buttons frame
        button_frame = ttk.Frame(viewer)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def refresh_logs():
            """Refresh log content."""
            log_text.config(state=tk.NORMAL)
            log_text.delete("1.0", tk.END)
            try:
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    log_text.insert("1.0", content)
                    log_text.see(tk.END)
                else:
                    log_text.insert("1.0", "Log file not found.")
            except Exception as e:
                log_text.insert("1.0", f"Error reading log file: {e}")
            log_text.config(state=tk.DISABLED)

        def open_log_folder():
            """Open log folder in file explorer."""
            import platform
            import subprocess

            log_dir = log_file.parent
            if not log_dir.exists():
                messagebox.showwarning(t("warning"), "Log directory does not exist yet.", parent=viewer)
                return

            try:
                if platform.system() == "Windows":
                    os.startfile(log_dir)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", log_dir])
                else:  # Linux
                    subprocess.run(["xdg-open", log_dir])
            except Exception as e:
                messagebox.showerror(t("error"), f"Failed to open folder: {e}", parent=viewer)

        ttk.Button(button_frame, text="Refresh", command=refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Open Log Folder", command=open_log_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=t("close"), command=viewer.destroy).pack(side=tk.RIGHT, padx=5)

    def run(self) -> None:
        self.root.mainloop()
