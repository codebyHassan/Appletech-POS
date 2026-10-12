"""
Modern White & Blue ERP Theme for Apple Tech Mobile Repair POS.
Clean, crisp enterprise styling with high contrast, polished cards, subtle shadows, and pixel-perfect controls.
"""

# Color Palette Constants - White & Blue ERP Style
COLOR_BG_MAIN = "#f8fafc"         # Ice Slate 50 (Main Viewport)
COLOR_BG_CARD = "#ffffff"         # Pure White Card
COLOR_BG_CARD_ALT = "#f1f5f9"     # Light Slate 100 for headers/subtle boxes
COLOR_BG_SIDEBAR = "#0f172a"      # Deep Navy Slate 900 (High-contrast ERP sidebar)
COLOR_BG_INPUT = "#ffffff"        # White Input Background

COLOR_BORDER = "#e2e8f0"          # Light Slate 200 Border
COLOR_BORDER_STRONG = "#cbd5e1"   # Slate 300
COLOR_BORDER_FOCUS = "#2563eb"    # Royal Blue Focus

COLOR_TEXT_PRIMARY = "#0f172a"    # Slate 900 (High readability)
COLOR_TEXT_SECONDARY = "#475569"  # Slate 600
COLOR_TEXT_MUTED = "#94a3b8"      # Slate 400
COLOR_TEXT_LIGHT = "#ffffff"      # Pure White text (for sidebar/buttons)

COLOR_PRIMARY = "#2563eb"         # Royal Blue 600
COLOR_PRIMARY_HOVER = "#1d4ed8"   # Royal Blue 700
COLOR_PRIMARY_ACTIVE = "#1e40af"  # Royal Blue 800
COLOR_PRIMARY_LIGHT = "#eff6ff"   # Blue 50

COLOR_ACCENT = "#0284c7"          # Sky Blue 600
COLOR_SUCCESS = "#16a34a"         # Green 600
COLOR_SUCCESS_BG = "#f0fdf4"      # Green 50
COLOR_WARNING = "#d97706"         # Amber 600
COLOR_WARNING_BG = "#fffbeb"      # Amber 50
COLOR_DANGER = "#dc2626"          # Red 600
COLOR_DANGER_BG = "#fef2f2"       # Red 50
COLOR_PURPLE = "#7c3aed"          # Violet 600
COLOR_PURPLE_BG = "#f5f3ff"       # Violet 50

# Status Color Map (Light ERP Badges with dot indicator)
STATUS_COLORS = {
    "Received":   {"bg": "#eff6ff", "border": "#3b82f6", "text": "#1d4ed8", "dot": "#3b82f6"},
    "Diagnosing": {"bg": "#f5f3ff", "border": "#8b5cf6", "text": "#6d28d9", "dot": "#8b5cf6"},
    "In Progress":{"bg": "#fffbeb", "border": "#f59e0b", "text": "#b45309", "dot": "#f59e0b"},
    "Ready":      {"bg": "#f0fdf4", "border": "#22c55e", "text": "#15803d", "dot": "#22c55e"},
    "Delivered":  {"bg": "#f1f5f9", "border": "#64748b", "text": "#334155", "dot": "#94a3b8"},
    "Cancelled":  {"bg": "#fef2f2", "border": "#ef4444", "text": "#b91c1c", "dot": "#ef4444"},
}

GLOBAL_STYLESHEET = f"""
/* Global Reset & Base */
QWidget {{
    background-color: {COLOR_BG_MAIN};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: {COLOR_PRIMARY};
    selection-color: #ffffff;
}}

QMainWindow {{
    background-color: {COLOR_BG_MAIN};
}}

QDialog {{
    background-color: #ffffff;
}}

/* Sidebar Container */
#sidebarFrame {{
    background-color: {COLOR_BG_SIDEBAR};
    border-right: 1px solid #1e293b;
    min-width: 240px;
    max-width: 240px;
}}

#sidebarFrame QWidget {{
    background-color: {COLOR_BG_SIDEBAR};
}}

/* Nav Buttons */
QPushButton.nav-btn {{
    text-align: left;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
    background-color: transparent;
    border: 1px solid transparent;
    margin: 1px 4px;
    icon-size: 16px;
}}

QPushButton.nav-btn:hover {{
    background-color: rgba(255, 255, 255, 0.07);
    color: #e2e8f0;
}}

QPushButton.nav-btn:checked, QPushButton.nav-btn.active {{
    background-color: rgba(37, 99, 235, 0.25);
    color: #ffffff;
    font-weight: 700;
    border: 1px solid rgba(59, 130, 246, 0.35);
}}

/* Modern ERP Cards */
QFrame.card {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 16px;
}}

QFrame.card:hover {{
    border: 1px solid {COLOR_BORDER_STRONG};
}}

/* Headings */
QLabel.page-title {{
    font-size: 22px;
    font-weight: 800;
    color: {COLOR_TEXT_PRIMARY};
    letter-spacing: -0.3px;
}}

QLabel.page-subtitle {{
    font-size: 13px;
    color: {COLOR_TEXT_SECONDARY};
}}

QLabel.section-header {{
    font-size: 15px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
    margin-bottom: 6px;
}}

QLabel.card-stat-value {{
    font-size: 24px;
    font-weight: 800;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.card-stat-title {{
    font-size: 12px;
    font-weight: 600;
    color: {COLOR_TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* Buttons */
QPushButton {{
    background-color: #ffffff;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_STRONG};
    border-radius: 7px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #f8fafc;
    border-color: #94a3b8;
}}

QPushButton:pressed {{
    background-color: #e2e8f0;
}}

QPushButton:disabled {{
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}}

/* Primary Royal Blue Button */
QPushButton.btn-primary, QPushButton#btnPrimary {{
    background-color: {COLOR_PRIMARY};
    color: #ffffff;
    border: 1px solid {COLOR_PRIMARY_HOVER};
    font-weight: 700;
}}

QPushButton.btn-primary:hover, QPushButton#btnPrimary:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}

QPushButton.btn-primary:pressed, QPushButton#btnPrimary:pressed {{
    background-color: {COLOR_PRIMARY_ACTIVE};
}}

/* Success Button */
QPushButton.btn-success {{
    background-color: {COLOR_SUCCESS};
    color: #ffffff;
    border: 1px solid #15803d;
    font-weight: 700;
}}

QPushButton.btn-success:hover {{
    background-color: #15803d;
}}

/* Danger Button */
QPushButton.btn-danger {{
    background-color: #ffffff;
    color: {COLOR_DANGER};
    border: 1px solid #fca5a5;
    font-weight: 600;
}}

QPushButton.btn-danger:hover {{
    background-color: {COLOR_DANGER_BG};
    border-color: {COLOR_DANGER};
}}

/* Table Action Buttons (High-end ERP Badged Buttons) */
QPushButton.btn-tbl-print {{
    background-color: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 10px;
}}
QPushButton.btn-tbl-print:hover {{
    background-color: #dbeafe;
    border-color: #3b82f6;
}}

QPushButton.btn-tbl-diag {{
    background-color: #f5f3ff;
    color: #6d28d9;
    border: 1px solid #ddd6fe;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 10px;
}}
QPushButton.btn-tbl-diag:hover {{
    background-color: #ede9fe;
    border-color: #8b5cf6;
}}

QPushButton.btn-tbl-edit {{
    background-color: #f0fdf4;
    color: #15803d;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 10px;
}}
QPushButton.btn-tbl-edit:hover {{
    background-color: #dcfce7;
    border-color: #22c55e;
}}

QPushButton.btn-tbl-delete {{
    background-color: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 8px;
}}
QPushButton.btn-tbl-delete:hover {{
    background-color: #fee2e2;
    border-color: #ef4444;
}}

QPushButton.btn-tbl-view {{
    background-color: #f8fafc;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 10px;
}}
QPushButton.btn-tbl-view:hover {{
    background-color: #f1f5f9;
    border-color: #94a3b8;
}}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {{
    background-color: {COLOR_BG_INPUT};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_STRONG};
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
    border: 1.5px solid {COLOR_PRIMARY};
    background-color: #ffffff;
}}

QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled {{
    background-color: #f1f5f9;
    color: #64748b;
}}

/* ComboBox */
QComboBox {{
    background-color: {COLOR_BG_INPUT};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_STRONG};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 20px;
}}

QComboBox:focus {{
    border: 1.5px solid {COLOR_PRIMARY};
}}

QComboBox QAbstractItemView {{
    background-color: #ffffff;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_PRIMARY_LIGHT};
    selection-color: {COLOR_PRIMARY};
    padding: 4px;
}}

/* Tables */
QTableWidget, QTableView {{
    background-color: #ffffff;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #e0e7ff;
    selection-color: #1e1b4b;
    font-size: 12.5px;
}}

QTableWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid #f1f5f9;
}}

QTableWidget::item:selected {{
    background-color: #e0e7ff;
    color: #1e1b4b;
}}

QHeaderView::section {{
    background-color: #f8fafc;
    color: {COLOR_TEXT_SECONDARY};
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid {COLOR_BORDER};
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ScrollBars */
QScrollBar:vertical {{
    background: #f1f5f9;
    width: 9px;
    border-radius: 4px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #cbd5e1;
    min-height: 25px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: #f1f5f9;
    height: 9px;
    border-radius: 4px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: #cbd5e1;
    min-width: 25px;
    border-radius: 4px;
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: #ffffff;
    border-radius: 8px;
    padding: 12px;
}}

QTabBar::tab {{
    background-color: #f1f5f9;
    color: {COLOR_TEXT_SECONDARY};
    padding: 9px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background-color: #ffffff;
    color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-bottom: 2px solid {COLOR_PRIMARY};
    font-weight: 700;
}}

QTabBar::tab:hover:!selected {{
    background-color: #e2e8f0;
}}

/* Status Badge Pills */
QLabel.status-pill {{
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11.5px;
    font-weight: 700;
    text-align: center;
}}

/* Group Box */
QGroupBox {{
    font-weight: bold;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    background-color: #ffffff;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    color: {COLOR_PRIMARY};
}}
"""


def get_status_style(status: str) -> str:
    """Return inline style for a status pill badge."""
    cfg = STATUS_COLORS.get(status, {"bg": "#f1f5f9", "border": "#64748b", "text": "#334155"})
    return (
        f"background-color: {cfg['bg']}; "
        f"color: {cfg['text']}; "
        f"border: 1px solid {cfg['border']}; "
        f"border-radius: 12px; "
        f"padding: 3px 8px; "
        f"font-weight: bold; "
        f"font-size: 11.5px;"
    )
