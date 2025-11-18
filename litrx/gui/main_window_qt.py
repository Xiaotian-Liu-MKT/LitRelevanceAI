"""PyQt6-based main application window."""

from PyQt6.QtWidgets import QApplication
import sys

from .base_window_qt import BaseWindow
from .tabs_qt import CsvTab, AbstractTab, MatrixTab
from ..i18n import t


class LitRxApp(BaseWindow):
    """Main application window that manages individual tabs."""

    def __init__(self) -> None:
        super().__init__()

        # Create tabs
        self.csv_tab = CsvTab(self)
        self.abstract_tab = AbstractTab(self)
        self.matrix_tab = MatrixTab(self)

        # Add tabs to tab widget
        self.tab_widget.addTab(self.csv_tab, t("csv_tab"))
        self.tab_widget.addTab(self.abstract_tab, t("abstract_tab"))
        self.tab_widget.addTab(self.matrix_tab, t("matrix_tab"))

    def _on_language_changed(self) -> None:
        """Override to update tabs when language changes."""
        super()._on_language_changed()

        # Update tab labels
        self.tab_widget.setTabText(0, t("csv_tab"))
        self.tab_widget.setTabText(1, t("abstract_tab"))
        self.tab_widget.setTabText(2, t("matrix_tab"))

        # Notify tabs to update their UI
        if hasattr(self.csv_tab, 'update_language'):
            self.csv_tab.update_language()
        if hasattr(self.abstract_tab, 'update_language'):
            self.abstract_tab.update_language()
        if hasattr(self.matrix_tab, 'update_language'):
            self.matrix_tab.update_language()


def launch_gui() -> None:
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern cross-platform style

    window = LitRxApp()
    window.show()

    sys.exit(app.exec())
