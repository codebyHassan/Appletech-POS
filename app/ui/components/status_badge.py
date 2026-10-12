"""
Premium StatusBadge — rounded pill with dot indicator and soft fill.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.ui.styles import STATUS_COLORS


class StatusBadge(QWidget):
    """
    Modern status pill: [● STATUS]
    Dot color matches the status accent, soft fill background.
    """
    def __init__(self, status: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)

        self._pill = QLabel(status)
        self._pill.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._pill)
        self.update_status(status)

    def update_status(self, status: str):
        self._pill.setText(status)
        cfg = STATUS_COLORS.get(status, {
            "bg": "rgba(100,116,139,0.12)",
            "border": "#94a3b8",
            "text": "#64748b",
            "dot": "#94a3b8"
        })
        dot_color = cfg.get("dot", cfg.get("border", "#94a3b8"))
        self._pill.setStyleSheet(f"""
            QLabel {{
                background-color: {cfg['bg']};
                color: {cfg['text']};
                border: 1px solid {cfg['border']};
                border-radius: 10px;
                padding: 3px 10px 3px 8px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.2px;
            }}
        """)
