from .base_window import BaseWindow
from .tabs import CsvTab, AbstractTab, PdfTab


class LitRxApp(BaseWindow):
    """Main application window that manages individual tabs."""

    def __init__(self) -> None:
        super().__init__()
        self.csv_tab = CsvTab(self)
        self.abstract_tab = AbstractTab(self)
        self.pdf_tab = PdfTab(self)


def launch_gui() -> None:
    """Launch the GUI application."""
    LitRxApp().run()
