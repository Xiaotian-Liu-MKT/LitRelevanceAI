import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict

from ..config import DEFAULT_CONFIG as BASE_CONFIG, load_config, load_env_file

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - handle missing pyyaml
    yaml = None

# Load environment variables from .env so they can override other sources
load_env_file()

PERSIST_PATH = Path.home() / ".litrx_gui.yaml"


class BaseWindow:
    """Base window providing shared config controls and notebook manager."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("LitRx Toolkit")

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
            "API_BASE",
        ]:
            env_val = os.getenv(key)
            if env_val:
                self.base_config[key] = env_val

        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top, text="Service:").pack(side=tk.LEFT)
        self.service_var = tk.StringVar(
            value=self.base_config.get("AI_SERVICE", "openai")
        )
        service_menu = ttk.Combobox(
            top,
            textvariable=self.service_var,
            values=["openai", "gemini"],
            width=10,
            state="readonly",
        )
        service_menu.pack(side=tk.LEFT, padx=5)
        self.current_service = self.service_var.get()
        service_menu.bind("<<ComboboxSelected>>", self.on_service_change)

        ttk.Label(top, text="API Key:").pack(side=tk.LEFT, padx=(10, 0))
        initial_key = (
            self.base_config.get("OPENAI_API_KEY")
            if self.current_service == "openai"
            else self.base_config.get("GEMINI_API_KEY", "")
        )
        self.api_key_var = tk.StringVar(value=initial_key)
        ttk.Entry(top, textvariable=self.api_key_var, width=40, show="*").pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(top, text="Model:").pack(side=tk.LEFT, padx=(10, 0))
        self.model_var = tk.StringVar(value=self.base_config.get("MODEL_NAME", ""))
        ttk.Entry(top, textvariable=self.model_var, width=20).pack(side=tk.LEFT)
        ttk.Button(top, text="Save Config", command=self.save_config).pack(
            side=tk.LEFT, padx=(10, 0)
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

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
        if self.current_service == "openai":
            self.base_config["OPENAI_API_KEY"] = self.api_key_var.get().strip()
        else:
            self.base_config["GEMINI_API_KEY"] = self.api_key_var.get().strip()

        self.current_service = self.service_var.get()
        if self.current_service == "openai":
            self.api_key_var.set(self.base_config.get("OPENAI_API_KEY", ""))
        else:
            self.api_key_var.set(self.base_config.get("GEMINI_API_KEY", ""))

    def run(self) -> None:
        self.root.mainloop()
