"""AI assistant dialog for creating matrix dimensions."""

from __future__ import annotations

import threading
from typing import Any, Dict, List

from ...tk_compat import ensure_native_macos_version

ensure_native_macos_version()

import tkinter as tk
from tkinter import ttk, messagebox

from ...ai_config_generator import MatrixDimensionGenerator
from ...i18n import t


class AIDimensionAssistantDialog:
    """Dialog for AI-assisted dimension creation."""

    # Dimension type display names (Chinese)
    TYPE_DISPLAY_NAMES_ZH = {
        "text": "开放文本",
        "yes_no": "是/否",
        "single_choice": "单选题",
        "multiple_choice": "多选题",
        "number": "数值提取",
        "rating": "评分",
        "list": "列表提取"
    }

    # Dimension type display names (English)
    TYPE_DISPLAY_NAMES_EN = {
        "text": "Text",
        "yes_no": "Yes/No",
        "single_choice": "Single Choice",
        "multiple_choice": "Multiple Choice",
        "number": "Number",
        "rating": "Rating",
        "list": "List"
    }

    def __init__(self, parent: tk.Misc, config: Dict[str, Any]):
        """Initialize AI dimension assistant dialog.

        Args:
            parent: Parent window (Tk or Toplevel)
            config: Configuration dict with AI_SERVICE, API keys, etc.
        """
        self.parent = parent
        self.config = config
        self.generator = MatrixDimensionGenerator(config)
        self.result = None  # List of selected dimensions if user clicks Apply
        self.generated_dimensions = []  # Temporary storage

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(t("ai_dimension_assistant_title"))
        self.dialog.geometry("950x750")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_dialog()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Guide text
        guide_text = t("ai_dimension_guide")
        ttk.Label(main_frame, text=guide_text, wraplength=900).pack(anchor=tk.W, pady=(0, 10))

        # 2. User input area
        ttk.Label(main_frame, text=t("describe_your_needs"), font=("", 10, "bold")).pack(anchor=tk.W)
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        self.input_text = tk.Text(input_frame, height=4, wrap=tk.WORD, font=("", 10))
        input_scroll = ttk.Scrollbar(input_frame, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scroll.set)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 3. Generate button
        self.generate_btn = ttk.Button(
            main_frame,
            text=t("generate_dimensions"),
            command=self._on_generate
        )
        self.generate_btn.pack(pady=10)

        # 4. Status label
        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.pack()

        # 5. Preview area with table
        ttk.Label(main_frame, text=t("generated_dimensions"), font=("", 10, "bold")).pack(
            anchor=tk.W, pady=(10, 5)
        )

        # Select all checkbox
        self.select_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text=t("select_all"),
            variable=self.select_all_var,
            command=self._on_select_all
        ).pack(anchor=tk.W)

        # Table frame
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Treeview for dimensions
        columns = ("select", "type", "question", "column", "details")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        self.tree.heading("select", text="✓")
        self.tree.heading("type", text=t("type"))
        self.tree.heading("question", text=t("question"))
        self.tree.heading("column", text=t("column_name"))
        self.tree.heading("details", text=t("details"))

        self.tree.column("select", width=40, anchor=tk.CENTER)
        self.tree.column("type", width=100)
        self.tree.column("question", width=400)
        self.tree.column("column", width=120)
        self.tree.column("details", width=180)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to toggle selection
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        # 6. Statistics label
        self.stats_label = ttk.Label(main_frame, text="")
        self.stats_label.pack(pady=5)

        # 7. Bottom buttons
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
            text=t("apply_selected"),
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

        # Clear previous results
        self.tree.delete(*self.tree.get_children())

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
            dimensions = self.generator.generate_dimensions(description, language)
            self.dialog.after(0, self._on_generation_success, dimensions)
        except Exception as e:
            self.dialog.after(0, self._on_generation_error, str(e))

    def _on_generation_success(self, dimensions: List[Dict[str, Any]]) -> None:
        """Handle successful generation.

        Args:
            dimensions: List of generated dimensions
        """
        self.generated_dimensions = dimensions
        self.status_label.config(text=t("generation_success"), foreground="green")

        # Populate table
        self._populate_table(dimensions)

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

    def _populate_table(self, dimensions: List[Dict[str, Any]]) -> None:
        """Populate tree with dimensions.

        Args:
            dimensions: List of dimension dicts
        """
        # Clear existing items
        self.tree.delete(*self.tree.get_children())

        # Choose display names based on language
        language = self.config.get("LANGUAGE", "zh")
        type_names = self.TYPE_DISPLAY_NAMES_ZH if language == "zh" else self.TYPE_DISPLAY_NAMES_EN

        for dim in dimensions:
            dim_type = type_names.get(dim["type"], dim["type"])
            question = dim["question"]
            if len(question) > 60:
                question = question[:60] + "..."
            column = dim["column_name"]

            # Build details string
            details = []
            if "options" in dim:
                details.append(f"{len(dim['options'])} {t('options')}")
            if "unit" in dim:
                details.append(f"{t('unit')}: {dim['unit']}")
            if "scale" in dim:
                details.append(f"1-{dim['scale']}{t('points')}")
            if "separator" in dim:
                details.append(f"{t('separator')}: {dim['separator']}")
            detail_str = ", ".join(details) if details else "-"

            self.tree.insert("", tk.END, values=("☑", dim_type, question, column, detail_str))

        self._update_stats()

    def _on_tree_double_click(self, event) -> None:
        """Toggle selection on double-click.

        Args:
            event: Click event
        """
        item = self.tree.identify_row(event.y)
        if item:
            values = list(self.tree.item(item, "values"))
            values[0] = "☐" if values[0] == "☑" else "☑"
            self.tree.item(item, values=values)
            self._update_stats()

    def _on_select_all(self) -> None:
        """Toggle all selections."""
        symbol = "☑" if self.select_all_var.get() else "☐"
        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            values[0] = symbol
            self.tree.item(item, values=values)
        self._update_stats()

    def _update_stats(self) -> None:
        """Update selection statistics label."""
        total = len(self.tree.get_children())
        if total == 0:
            self.stats_label.config(text="")
            return

        selected = sum(
            1 for item in self.tree.get_children()
            if self.tree.item(item, "values")[0] == "☑"
        )
        self.stats_label.config(text=t("dimensions_selected").format(selected=selected, total=total))

    def _on_apply(self) -> None:
        """Apply selected dimensions."""
        selected_dims = []
        for idx, item in enumerate(self.tree.get_children()):
            if self.tree.item(item, "values")[0] == "☑":
                selected_dims.append(self.generated_dimensions[idx])

        if not selected_dims:
            messagebox.showwarning(
                t("warning"),
                t("please_select_dimensions")
            )
            return

        self.result = selected_dims
        self.dialog.destroy()

    def _on_cancel(self) -> None:
        """Cancel and close dialog."""
        self.result = None
        self.dialog.destroy()

    def _center_dialog(self) -> None:
        """Center dialog on parent window."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
