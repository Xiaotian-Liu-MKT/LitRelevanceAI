import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict

from ..config import DEFAULT_CONFIG as BASE_CONFIG, load_config, load_env_file

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - handle missing pyyaml
    yaml = None

# Load environment variables from .env so they can override other sources
load_env_file()

PERSIST_PATH = Path.home() / ".litrx_gui.yaml"
PROMPTS_PATH = Path(__file__).resolve().parents[2] / "prompts_config.json"


class BaseWindow:
    """Base window providing shared config controls and notebook manager."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("LitRx Toolkit - AI文献分析工具")
        self.root.geometry("1000x700")

        # Configure modern styling
        self.setup_styles()

        repo_root = Path(__file__).resolve().parents[2]
        config_path = repo_root / "configs" / "config.yaml"

        # Start with defaults from config.yaml then layer in persisted config
        self.base_config: Dict[str, str] = load_config(str(config_path), BASE_CONFIG)
        self.base_config = load_config(str(PERSIST_PATH), self.base_config)

        # Environment variables have higher priority than persisted config
        for key in [
            "AI_SERVICE",
            "MODEL_NAME",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "SILICONFLOW_API_KEY",
            "API_BASE",
        ]:
            env_val = os.getenv(key)
            if env_val:
                self.base_config[key] = env_val

        # Header Frame
        header = ttk.Frame(self.root, style="Header.TFrame")
        header.pack(fill=tk.X, padx=15, pady=(10, 5))

        title_label = ttk.Label(header, text="LitRx Toolkit", style="Title.TLabel")
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(header, text="AI-powered Literature Review Assistant", style="Subtitle.TLabel")
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

        # Configuration Frame
        config_frame = ttk.LabelFrame(self.root, text=" 配置设置 ", style="Config.TLabelframe")
        config_frame.pack(fill=tk.X, padx=15, pady=(5, 10))

        # Row 1: Service and API Key
        row1 = ttk.Frame(config_frame)
        row1.pack(fill=tk.X, padx=10, pady=8)

        ttk.Label(row1, text="AI Service:", width=12).pack(side=tk.LEFT)
        self.service_var = tk.StringVar(
            value=self.base_config.get("AI_SERVICE", "openai")
        )
        service_menu = ttk.Combobox(
            row1,
            textvariable=self.service_var,
            values=["openai", "gemini", "siliconflow"],
            width=15,
            state="readonly",
        )
        service_menu.pack(side=tk.LEFT, padx=(0, 15))
        self.current_service = self.service_var.get()
        service_menu.bind("<<ComboboxSelected>>", self.on_service_change)

        ttk.Label(row1, text="API Key:").pack(side=tk.LEFT, padx=(0, 5))
        if self.current_service == "openai":
            initial_key = self.base_config.get("OPENAI_API_KEY", "")
        elif self.current_service == "gemini":
            initial_key = self.base_config.get("GEMINI_API_KEY", "")
        else:  # siliconflow
            initial_key = self.base_config.get("SILICONFLOW_API_KEY", "")
        self.api_key_var = tk.StringVar(value=initial_key)
        ttk.Entry(row1, textvariable=self.api_key_var, width=45, show="*").pack(
            side=tk.LEFT, padx=5
        )

        # Row 2: Model and Buttons
        row2 = ttk.Frame(config_frame)
        row2.pack(fill=tk.X, padx=10, pady=(0, 8))

        ttk.Label(row2, text="Model:", width=12).pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self.base_config.get("MODEL_NAME", ""))
        ttk.Entry(row2, textvariable=self.model_var, width=30).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Button(row2, text="💾 保存配置", command=self.save_config, style="Primary.TButton").pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(row2, text="⚙️ Prompt设置", command=self.open_prompt_settings, style="Secondary.TButton").pack(
            side=tk.LEFT, padx=5
        )

        self.notebook = ttk.Notebook(self.root, style="Main.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

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
    def build_config(self) -> Dict[str, str]:
        config = self.base_config.copy()
        service = self.service_var.get()
        config["AI_SERVICE"] = service
        api_key = self.api_key_var.get().strip()
        if service == "openai" and api_key:
            config["OPENAI_API_KEY"] = api_key
        elif service == "gemini" and api_key:
            config["GEMINI_API_KEY"] = api_key
        elif service == "siliconflow" and api_key:
            config["SILICONFLOW_API_KEY"] = api_key
        model = self.model_var.get().strip()
        if model:
            config["MODEL_NAME"] = model
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
        """Persist current configuration to ``~/.litrx_gui.yaml``."""

        config = self.build_config()
        if yaml is None:
            messagebox.showerror(
                "Error", "pyyaml is required to save configuration"
            )
            return

        data = {
            key: config.get(key, "")
            for key in [
                "AI_SERVICE",
                "MODEL_NAME",
                "API_BASE",
                "OPENAI_API_KEY",
                "GEMINI_API_KEY",
                "SILICONFLOW_API_KEY",
            ]
        }

        try:
            with PERSIST_PATH.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)
        except Exception as e:  # pragma: no cover - user feedback
            messagebox.showerror("Error", f"Failed to save config: {e}")
        else:  # pragma: no cover - user feedback
            messagebox.showinfo(
                "Saved", f"Configuration saved to {PERSIST_PATH}"
            )

    def on_service_change(self, event=None) -> None:
        # Save current API key before switching
        if self.current_service == "openai":
            self.base_config["OPENAI_API_KEY"] = self.api_key_var.get().strip()
        elif self.current_service == "gemini":
            self.base_config["GEMINI_API_KEY"] = self.api_key_var.get().strip()
        elif self.current_service == "siliconflow":
            self.base_config["SILICONFLOW_API_KEY"] = self.api_key_var.get().strip()

        # Switch to new service and load its API key
        self.current_service = self.service_var.get()
        if self.current_service == "openai":
            self.api_key_var.set(self.base_config.get("OPENAI_API_KEY", ""))
        elif self.current_service == "gemini":
            self.api_key_var.set(self.base_config.get("GEMINI_API_KEY", ""))
        elif self.current_service == "siliconflow":
            self.api_key_var.set(self.base_config.get("SILICONFLOW_API_KEY", ""))

    def open_prompt_settings(self) -> None:
        """Open the prompt settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Prompt设置")
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
        notebook.add(csv_frame, text="CSV相关性分析")
        text_widgets["csv_analysis"] = self._create_prompt_editor(csv_frame, prompts.get("csv_analysis", {}))

        # Abstract Screening Tab
        abstract_frame = ttk.Frame(notebook)
        notebook.add(abstract_frame, text="摘要筛选")
        text_widgets["abstract_screening"] = self._create_prompt_editor(abstract_frame, prompts.get("abstract_screening", {}))

        # PDF Screening Tab
        pdf_frame = ttk.Frame(notebook)
        notebook.add(pdf_frame, text="PDF筛选")
        text_widgets["pdf_screening"] = self._create_prompt_editor(pdf_frame, prompts.get("pdf_screening", {}))

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def save_prompts():
            try:
                # Collect all prompt values from text widgets
                updated_prompts = {}
                for category, widgets in text_widgets.items():
                    updated_prompts[category] = {}
                    for key, text_widget in widgets.items():
                        updated_prompts[category][key] = text_widget.get("1.0", tk.END).strip()

                with PROMPTS_PATH.open("w", encoding="utf-8") as f:
                    json.dump(updated_prompts, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", "Prompt设置已保存", parent=dialog)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}", parent=dialog)

        def reset_defaults():
            if messagebox.askyesno("确认", "确定要恢复默认Prompt设置吗？", parent=dialog):
                # Restore default prompts
                default_prompts = self._get_default_prompts()
                try:
                    with PROMPTS_PATH.open("w", encoding="utf-8") as f:
                        json.dump(default_prompts, f, ensure_ascii=False, indent=2)
                    messagebox.showinfo("成功", "已恢复默认设置", parent=dialog)
                    dialog.destroy()
                    self.open_prompt_settings()  # Reopen dialog with defaults
                except Exception as e:
                    messagebox.showerror("错误", f"恢复失败: {e}", parent=dialog)

        ttk.Button(button_frame, text="保存", command=save_prompts).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="恢复默认", command=reset_defaults).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

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

    def run(self) -> None:
        self.root.mainloop()
