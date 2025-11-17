from .base_window import BaseWindow
from .tabs import CsvTab, AbstractTab, MatrixTab
from ..i18n import t


class LitRxApp(BaseWindow):
    """Main application window that manages individual tabs."""

    def __init__(self) -> None:
        super().__init__()
        self.csv_tab = CsvTab(self)
        self.abstract_tab = AbstractTab(self)
        self.matrix_tab = MatrixTab(self)

        # Update tab labels with translations
        self._update_tab_labels()

    def _update_tab_labels(self) -> None:
        """Update notebook tab labels with current language."""
        tabs = self.notebook.tabs()
        if len(tabs) >= 3:
            self.notebook.tab(tabs[0], text=t("csv_tab"))
            self.notebook.tab(tabs[1], text=t("abstract_tab"))
            self.notebook.tab(tabs[2], text=t("matrix_tab"))

    def _on_language_changed(self) -> None:
        """Override to update tabs when language changes."""
        super()._on_language_changed()
        self._update_tab_labels()

        # Notify tabs to update their UI
        if hasattr(self.csv_tab, 'update_language'):
            self.csv_tab.update_language()
        if hasattr(self.abstract_tab, 'update_language'):
            self.abstract_tab.update_language()
        if hasattr(self.matrix_tab, 'update_language'):
            self.matrix_tab.update_language()


def launch_gui() -> None:
    """Launch the GUI application."""
    LitRxApp().run()
