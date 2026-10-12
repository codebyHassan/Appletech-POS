from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Signal, Qt


class SearchBar(QWidget):
    """
    Search bar with quick clear button and real-time search signal.
    """
    search_changed = Signal(str)

    def __init__(self, placeholder: str = "Search...", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self._on_text_changed)

        layout.addWidget(self.input)

    def _on_text_changed(self, text: str):
        self.search_changed.emit(text.strip())

    def text(self) -> str:
        return self.input.text().strip()

    def clear(self):
        self.input.clear()
