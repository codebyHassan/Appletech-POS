"""
Premium StatCard — Modern ERP KPI card with tinted icon circle,
large numeric value, trend pill, and accent left-border.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.ui.icons import get_icon


class StatCard(QFrame):
    """
    Premium KPI card:
    ┌─────────────────────────────┐
    │  [●] TITLE           TREND  │
    │                             │
    │  42               (icon bg) │
    └─────────────────────────────┘
    """
    def __init__(
        self,
        title: str,
        value: str | int,
        icon: str = "clipboard",       # icon name for get_icon()
        accent_color: str = "#2563eb",
        trend: str = "",                # e.g. "+5 today"
        parent=None
    ):
        super().__init__(parent)
        self._accent = accent_color
        self._icon_name = icon

        # Compute light tint from accent (alpha overlay)
        self.setObjectName("statCard")
        self._apply_style()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── TOP ROW: icon circle + title + trend ──────────────────────────
        top = QHBoxLayout()
        top.setSpacing(10)

        # Icon in a soft tinted circle
        self._icon_frame = QFrame()
        self._icon_frame.setFixedSize(38, 38)
        self._icon_frame.setStyleSheet(f"""
            QFrame {{
                background: {self._hex_with_alpha(accent_color, 0.12)};
                border-radius: 19px;
            }}
        """)
        icon_lay = QHBoxLayout(self._icon_frame)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(get_icon(icon, accent_color, 18).pixmap(18, 18))
        icon_lbl.setStyleSheet("background: transparent;")
        icon_lay.addWidget(icon_lbl)
        top.addWidget(self._icon_frame)

        # Title
        self._title_lbl = QLabel(title.upper())
        self._title_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #64748b; "
            "letter-spacing: 0.8px; background: transparent;"
        )
        top.addWidget(self._title_lbl)
        top.addStretch()

        # Trend pill (optional)
        if trend:
            trend_lbl = QLabel(trend)
            trend_lbl.setStyleSheet("""
                QLabel {
                    background: #f0fdf4;
                    color: #16a34a;
                    border: 1px solid #bbf7d0;
                    border-radius: 8px;
                    padding: 2px 7px;
                    font-size: 10px;
                    font-weight: 700;
                }
            """)
            top.addWidget(trend_lbl)

        root.addLayout(top)

        # ── VALUE ─────────────────────────────────────────────────────────
        self._value_lbl = QLabel(str(value))
        self._value_lbl.setStyleSheet(
            f"font-size: 28px; font-weight: 900; color: {accent_color}; "
            "letter-spacing: -1px; background: transparent;"
        )
        root.addWidget(self._value_lbl)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background: #ffffff;
                border: 1px solid #e8edf5;
                border-left: 4px solid {self._accent};
                border-radius: 12px;
            }}
            QFrame#statCard:hover {{
                background: #fafbff;
                border-color: {self._accent};
            }}
        """)

    @staticmethod
    def _hex_with_alpha(hex_color: str, alpha: float) -> str:
        """Convert '#rrggbb' + alpha to rgba(r,g,b,a) string."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def set_value(self, value: str | int):
        self._value_lbl.setText(str(value))
