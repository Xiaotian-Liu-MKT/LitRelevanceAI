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
        """Handle input method events properly to avoid duplication.

        Let Qt's default implementation handle both preedit (composition) and
        commit strings. We just ensure proper attributes are set in __init__.
        """
        # Let parent class handle the event completely
        # This avoids duplicate insertion of commit strings
        super().inputMethodEvent(event)
        event.accept()

    def inputMethodQuery(self, query: Qt.InputMethodQuery) -> Any:  # noqa: N802
        if query == Qt.InputMethodQuery.ImCursorRectangle:
            r = self.cursorRect()
            return QRect(r)
        return super().inputMethodQuery(query)

