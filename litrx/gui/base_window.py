import tkinter as tk
from tkinter import ttk, filedialog
from typing import Dict

from ..config import DEFAULT_CONFIG as BASE_CONFIG, load_env_file

load_env_file()


class BaseWindow:
    """Base window providing shared config controls and notebook manager."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("LitRx Toolkit")
        self.base_config: Dict[str, str] = BASE_CONFIG.copy()

        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="API Key:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.api_key_var, width=40, show="*").pack(side=tk.LEFT, padx=5)
        ttk.Label(top, text="Model:").pack(side=tk.LEFT, padx=(10, 0))
        self.model_var = tk.StringVar(value=self.base_config.get("MODEL_NAME", ""))
        ttk.Entry(top, textvariable=self.model_var, width=20).pack(side=tk.LEFT)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def build_config(self) -> Dict[str, str]:
        config = self.base_config.copy()
        api_key = self.api_key_var.get().strip()
        if api_key:
            config["OPENAI_API_KEY"] = api_key
            config["AI_SERVICE"] = config.get("AI_SERVICE", "openai")
        model = self.model_var.get().strip()
        if model:
            config["MODEL_NAME"] = model
        return config

    def browse_file(self, var: tk.StringVar, filetypes):
        path = filedialog.askopenfilename(filetypes=[filetypes])
        if path:
            var.set(path)

    def browse_folder(self, var: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def run(self) -> None:
        self.root.mainloop()
