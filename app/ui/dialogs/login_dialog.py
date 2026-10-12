"""
LoginDialog — Clean PySide6 implementation.
Uses QLineEdit.addAction() for inline SVG icons (Qt built-in, zero layout bugs).
No wrapper widgets. Pure QSS focus states. QGraphicsDropShadowEffect on card.
"""
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPixmap

from app.config import APP_NAME, APP_VERSION
from app.services.auth_service import AuthService
from app.services.backup_service import SettingsService
from app.ui.icons import get_icon

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """
    Premium enterprise login dialog.
    Layout: gradient bg -> centered frosted card -> brand logo + fields + CTA.
    Icon strategy: QLineEdit.addAction() with get_icon() — no wrapper widgets.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Sign In — {APP_NAME}")
        self.setFixedWidth(440)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Gradient dialog background
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:0.6, y2:1,
                    stop:0 #eef2ff,
                    stop:0.5 #e0f2fe,
                    stop:1 #f0f9ff
                );
            }
        """)
        self._init_ui()
        self.adjustSize()

    # ─────────────────────────────────────────────────────────────────────
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 36, 32, 28)
        root.setSpacing(20)

        # ── BRAND HEADER ─────────────────────────────────────────────────
        brand_row = QHBoxLayout()
        brand_row.setSpacing(14)
        brand_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Fetch shop settings for logo and name
        shop_title_text = "APPLE TECH"
        shop_tagline_text = "Mobile Repair POS & ERP"
        logo_path = ""
        try:
            settings = SettingsService.get_all_settings()
            logo_path = settings.get("shop_logo_path", "")
            s_name = settings.get("shop_name", "").strip()
            if s_name:
                shop_title_text = s_name.upper()
            s_tag = settings.get("shop_tagline", "").strip()
            if s_tag:
                shop_tagline_text = s_tag
        except Exception as e:
            logger.warning("Could not load shop settings for login dialog: %s", e)

        logo = QLabel("A")
        logo.setAlignment(Qt.AlignCenter)

        has_custom_logo = False
        if logo_path and Path(logo_path).exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                scaled = pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo.setFixedSize(50, 50)
                logo.setText("")
                logo.setPixmap(scaled)
                logo.setStyleSheet("""
                    QLabel {
                        background: #ffffff;
                        border: 1.5px solid #cbd5e1;
                        border-radius: 12px;
                        padding: 3px;
                    }
                """)
                has_custom_logo = True

        if not has_custom_logo:
            logo.setFixedSize(48, 48)
            logo.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 #2563eb, stop:1 #0284c7);
                    color: #ffffff;
                    border-radius: 24px;
                    font-size: 20px;
                    font-weight: 900;
                }
            """)
        brand_row.addWidget(logo)

        names = QVBoxLayout()
        names.setSpacing(3)
        title = QLabel(shop_title_text)
        title.setStyleSheet(
            "font-size: 18px; font-weight: 900; color: #0f172a; letter-spacing: 0.5px;"
        )
        sub = QLabel(shop_tagline_text)
        sub.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b;")
        names.addWidget(title)
        names.addWidget(sub)
        brand_row.addLayout(names)
        brand_row.addStretch()
        root.addLayout(brand_row)

        # ── GLASS CARD ────────────────────────────────────────────────────
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(203, 213, 225, 0.8);
                border-radius: 14px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(37, 99, 235, 30))
        card.setGraphicsEffect(shadow)

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(28, 26, 28, 28)
        card_lay.setSpacing(16)

        # Card heading
        heading = QLabel("Sign in to your account")
        heading.setWordWrap(True)
        heading.setStyleSheet(
            "font-size: 16px; font-weight: 800; color: #0f172a; letter-spacing: -0.2px;"
        )
        card_lay.addWidget(heading)

        card_sub = QLabel("Enter your credentials to access the workshop")
        card_sub.setWordWrap(True)
        card_sub.setStyleSheet("font-size: 12px; color: #64748b; margin-top: -8px;")
        card_lay.addWidget(card_sub)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("border: none; border-top: 1px solid #f1f5f9; margin: 0;")
        div.setFixedHeight(1)
        card_lay.addWidget(div)

        # ── USERNAME FIELD ────────────────────────────────────────────────
        card_lay.addWidget(self._field_label("Username"))
        self.edit_username = self._make_lineedit(
            placeholder="Enter username",
            icon_name="users"
        )
        card_lay.addWidget(self.edit_username)

        # ── PASSWORD FIELD ────────────────────────────────────────────────
        card_lay.addWidget(self._field_label("Password"))
        self.edit_password = self._make_lineedit(
            placeholder="Enter password",
            icon_name="key",
            password=True
        )
        self.edit_password.returnPressed.connect(self._handle_login)
        card_lay.addWidget(self.edit_password)

        # ── LOGIN BUTTON ──────────────────────────────────────────────────
        card_lay.addSpacing(4)
        self.btn_login = QPushButton("  Sign In to POS")
        self.btn_login.setIcon(get_icon("check", "#ffffff", 16))
        self.btn_login.setIconSize(QSize(16, 16))
        self.btn_login.setFixedHeight(46)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #2563eb, stop:1 #0284c7);
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                border: none;
                border-radius: 8px;
                letter-spacing: 0.2px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1d4ed8, stop:1 #0369a1);
            }
            QPushButton:pressed { background: #1e40af; }
        """)
        self.btn_login.clicked.connect(self._handle_login)
        card_lay.addWidget(self.btn_login)

        root.addWidget(card)

        # ── VERSION TAG ───────────────────────────────────────────────────
        ver = QLabel(f"v{APP_VERSION}  ·  100% Offline  ·  Powered by SQLite")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("font-size: 9.5px; color: #94a3b8;")
        root.addWidget(ver)

    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #374151; "
            "margin-bottom: 2px; background: transparent;"
        )
        return lbl

    def _make_lineedit(
        self, placeholder: str, icon_name: str, password: bool = False
    ) -> QLineEdit:
        """
        Create a styled QLineEdit with leading SVG icon via addAction().
        Qt's built-in addAction handles icon positioning with no layout bugs.
        """
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(44)
        edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if password:
            edit.setEchoMode(QLineEdit.Password)

        # Leading icon (LeadingPosition = left side)
        lead_action = edit.addAction(
            get_icon(icon_name, "#94a3b8", 16),
            QLineEdit.LeadingPosition
        )

        edit.setStyleSheet("""
            QLineEdit {
                background: #f8fafc;
                border: 1.5px solid #e2e8f0;
                border-radius: 8px;
                padding: 0px 10px 0px 38px;
                font-size: 13px;
                color: #0f172a;
                selection-background-color: #bfdbfe;
            }
            QLineEdit:focus {
                background: #ffffff;
                border: 1.5px solid #2563eb;
            }
            QLineEdit:hover:!focus {
                border: 1.5px solid #94a3b8;
            }
        """)
        return edit

    # ─────────────────────────────────────────────────────────────────────
    def _handle_login(self):
        username = self.edit_username.text().strip()
        password = self.edit_password.text()

        if not username or not password:
            QMessageBox.warning(self, "Sign In Error", "Please enter username and password.")
            return

        success, user, message = AuthService.authenticate(username, password)
        if success and user:
            self.accept()
        else:
            QMessageBox.critical(self, "Authentication Failed", message)
            self.edit_password.selectAll()
            self.edit_password.setFocus()
