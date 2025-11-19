from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QInputMethodEvent
from PyQt6.QtWidgets import QPlainTextEdit


class IMEPlainTextEdit(QPlainTextEdit):
    """Plain text edit with improved IME handling (macOS friendly).

    - Ensures WA_InputMethodEnabled is set
    - Provides cursor rectangle via inputMethodQuery
    - Commits composition text explicitly on inputMethodEvent
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        # Hint that this is a multi-line editor (helps some IMEs)
        self.setInputMethodHints(Qt.InputMethodHint.ImhMultiLine)

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:  # noqa: N802
        # If IME commits text, insert explicitly to avoid losing composition
        commit = event.commitString()
        if commit:
            self.insertPlainText(commit)
            event.accept()
            return
        # Fallback to default handling, which may render the preedit
        super().inputMethodEvent(event)

    def inputMethodQuery(self, query: Qt.InputMethodQuery) -> Any:  # noqa: N802
        if query == Qt.InputMethodQuery.ImCursorRectangle:
            r = self.cursorRect()
            return QRect(r)
        return super().inputMethodQuery(query)

