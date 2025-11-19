#!/usr/bin/env python
"""Test script to verify AI assistant dialogs don't crash without API key."""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from litrx.config import DEFAULT_CONFIG
from litrx.gui.dialogs_qt.ai_mode_assistant_qt import AIModeAssistantDialog
from litrx.gui.dialogs_qt.ai_matrix_assistant_qt import AIMatrixAssistantDialog


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test AI Dialogs")
        layout = QVBoxLayout(self)

        # Test config without API key
        self.config = DEFAULT_CONFIG.copy()
        self.config['OPENAI_API_KEY'] = ''

        btn1 = QPushButton("Test Abstract Mode Assistant")
        btn1.clicked.connect(self.test_mode_assistant)
        layout.addWidget(btn1)

        btn2 = QPushButton("Test Matrix Assistant")
        btn2.clicked.connect(self.test_matrix_assistant)
        layout.addWidget(btn2)

        self.resize(400, 200)

    def test_mode_assistant(self):
        try:
            dlg = AIModeAssistantDialog(self, self.config)
            print("✓ AIModeAssistantDialog created successfully (no crash)")
            dlg.exec()
            print("✓ AIModeAssistantDialog closed successfully (no crash)")
        except Exception as e:
            print(f"✗ AIModeAssistantDialog crashed: {e}")
            import traceback
            traceback.print_exc()

    def test_matrix_assistant(self):
        try:
            dlg = AIMatrixAssistantDialog(self, self.config)
            print("✓ AIMatrixAssistantDialog created successfully (no crash)")
            dlg.exec()
            print("✓ AIMatrixAssistantDialog closed successfully (no crash)")
        except Exception as e:
            print(f"✗ AIMatrixAssistantDialog crashed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
