"""AI assistant dialog for creating abstract screening modes."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from ...tk_compat import ensure_native_macos_version

ensure_native_macos_version()

import tkinter as tk
from tkinter import ttk, messagebox

from ...ai_config_generator import AbstractModeGenerator
from ...i18n import t


class AIModeAssistantDialog:
    """Dialog for AI-assisted mode creation."""

    def __init__(self, parent: tk.Misc, config: Dict[str, Any]):
        """Initialize AI mode assistant dialog.

        Args:
            parent: Parent window (Tk or Toplevel)
            config: Configuration dict with AI_SERVICE, API keys, etc.
        """
        self.parent = parent
        self.config = config
        self.generator = AbstractModeGenerator(config)
        self.result = None  # Generated config if user clicks Apply
        self.generated_config = None  # Temporary storage for generated config

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(t("ai_mode_assistant_title"))
        self.dialog.geometry("700x650")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_dialog()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Guide text
        guide_text = t("ai_mode_guide")
        guide_label = ttk.Label(main_frame, text=guide_text, wraplength=650)
        guide_label.pack(anchor=tk.W, pady=(0, 10))

        # 2. User input area
        input_label = ttk.Label(main_frame, text=t("describe_your_needs"), font=("", 10, "bold"))
        input_label.pack(anchor=tk.W)

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.input_text = tk.Text(input_frame, height=6, wrap=tk.WORD, font=("", 10))
        input_scroll = ttk.Scrollbar(input_frame, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scroll.set)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 3. Generate button
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        self.generate_btn = ttk.Button(
            btn_frame,
            text=t("generate_config"),
            command=self._on_generate
        )
        self.generate_btn.pack()

        # 4. Status label
        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.pack(pady=5)

        # 5. Preview area
        preview_label = ttk.Label(main_frame, text=t("preview_label"), font=("", 10, "bold"))
        preview_label.pack(anchor=tk.W, pady=(10, 5))

        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(
            preview_frame,
            height=15,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("", 9)
        )
        preview_scroll = ttk.Scrollbar(preview_frame, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 6. Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(pady=10)

        self.regenerate_btn = ttk.Button(
            bottom_frame,
            text=t("regenerate"),
            command=self._on_generate,
            state=tk.DISABLED
        )
        self.regenerate_btn.pack(side=tk.LEFT, padx=5)

        self.apply_btn = ttk.Button(
            bottom_frame,
            text=t("apply"),
            command=self._on_apply,
            state=tk.DISABLED
        )
        self.apply_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            bottom_frame,
            text=t("cancel"),
            command=self._on_cancel
        ).pack(side=tk.LEFT, padx=5)

    def _on_generate(self) -> None:
        """Handle generate button click."""
        description = self.input_text.get("1.0", tk.END).strip()
        if not description:
            messagebox.showwarning(
                t("warning"),
                t("please_enter_description")
            )
            return

        # Disable buttons
        self.generate_btn.config(state=tk.DISABLED)
        self.regenerate_btn.config(state=tk.DISABLED)
        self.apply_btn.config(state=tk.DISABLED)
        self.status_label.config(text=t("generating"), foreground="blue")

        # Clear previous preview
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.config(state=tk.DISABLED)

        # Run generation in background thread
        thread = threading.Thread(
            target=self._generate_thread,
            args=(description,),
            daemon=True
        )
        thread.start()

    def _generate_thread(self, description: str) -> None:
        """Background thread for generation.

        Args:
            description: User's description
        """
        try:
            language = self.config.get("LANGUAGE", "zh")
            result = self.generator.generate_mode(description, language)
            self.dialog.after(0, self._on_generation_success, result)
        except Exception as e:
            self.dialog.after(0, self._on_generation_error, str(e))

    def _on_generation_success(self, result: Dict[str, Any]) -> None:
        """Handle successful generation.

        Args:
            result: Generated mode configuration
        """
        self.generated_config = result
        self.status_label.config(text=t("generation_success"), foreground="green")

        # Show preview
        preview = self._format_preview(result)
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview)
        self.preview_text.config(state=tk.DISABLED)

        # Enable buttons
        self.generate_btn.config(state=tk.NORMAL)
        self.regenerate_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)

    def _on_generation_error(self, error: str) -> None:
        """Handle generation error.

        Args:
            error: Error message
        """
        self.status_label.config(text=t("generation_failed"), foreground="red")
        messagebox.showerror(
            t("error"),
            f"{t('generation_error')}:\n\n{error}"
        )

        # Re-enable generate button
        self.generate_btn.config(state=tk.NORMAL)

    def _format_preview(self, config: Dict[str, Any]) -> str:
        """Format config for preview display.

        Args:
            config: Mode configuration

        Returns:
            Formatted preview string
        """
        lines = []
        lines.append(f"{t('mode_key')}: {config['mode_key']}")
        lines.append(f"{t('description')}: {config['description']}")
        lines.append("")

        lines.append(f"{t('yes_no_questions')} ({len(config['yes_no_questions'])}):")
        for q in config['yes_no_questions']:
            lines.append(f"  ✓ {q['question']}")
            lines.append(f"    [{t('column')}: {q['column_name']}]")

        lines.append("")
        lines.append(f"{t('open_questions')} ({len(config['open_questions'])}):")
        for q in config['open_questions']:
            lines.append(f"  • {q['question']}")
            lines.append(f"    [{t('column')}: {q['column_name']}]")

        return "\n".join(lines)

    def _on_apply(self) -> None:
        """Handle apply button click."""
        self.result = self.generated_config
        self.dialog.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.result = None
        self.dialog.destroy()

    def _center_dialog(self) -> None:
        """Center dialog on parent window."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
