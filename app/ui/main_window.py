import sys
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QButtonGroup, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QPixmap

from app.config import APP_NAME, APP_VERSION
from app.ui.styles import GLOBAL_STYLESHEET
from app.services.auth_service import AuthService
from app.services.backup_service import SettingsService
from app.ui.icons import get_icon
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.jobs_view import JobsView
from app.ui.views.customers_view import CustomersView
from app.ui.views.devices_view import DevicesView
from app.ui.views.expenses_view import ExpensesView
from app.ui.views.settings_view import SettingsView
from app.ui.dialogs.job_dialog import JobDialog
from app.ui.dialogs.login_dialog import LoginDialog
from app.ui.components.print_preview_dialog import ThermalPrintPreviewDialog


class MainWindow(QMainWindow):
    """
    Main Application Window for Apple Tech Mobile Repair POS.
    Features White & Blue ERP Theme, Role-Based Access Control, Dual 3-inch Slips, and Expense Tracking.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - Enterprise Repair ERP")
        self.resize(1320, 840)
        self.setMinimumSize(1080, 700)

        self._init_ui()
        self._setup_shortcuts()
        self._apply_role_permissions()

    def _init_ui(self):
        self.setStyleSheet(GLOBAL_STYLESHEET)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── LEFT SIDEBAR ──────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Brand Header area
        brand_frame = QFrame()
        brand_frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-bottom: 1px solid #1e293b;
                padding: 0px;
            }
        """)
        brand_frame.setFixedHeight(68)
        brand_lay = QHBoxLayout(brand_frame)
        brand_lay.setContentsMargins(18, 0, 18, 0)
        brand_lay.setSpacing(10)

        # Logo widget
        self.sidebar_logo_lbl = QLabel("A")
        self.sidebar_logo_lbl.setFixedSize(36, 36)
        self.sidebar_logo_lbl.setAlignment(Qt.AlignCenter)
        self.sidebar_logo_lbl.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #2563eb,stop:1 #0284c7);
                color: #ffffff;
                border-radius: 18px;
                font-size: 15px;
                font-weight: 900;
            }
        """)
        brand_lay.addWidget(self.sidebar_logo_lbl)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        self.sidebar_title_lbl = QLabel("APPLE TECH")
        self.sidebar_title_lbl.setStyleSheet("font-size: 15px; font-weight: 900; color: #f8fafc; letter-spacing: 0.5px;")
        self.sidebar_sub_lbl = QLabel("Mobile Repair POS & ERP")
        self.sidebar_sub_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748b; letter-spacing: 0.3px;")
        brand_text.addWidget(self.sidebar_title_lbl)
        brand_text.addWidget(self.sidebar_sub_lbl)
        brand_lay.addLayout(brand_text)
        brand_lay.addStretch()
        sidebar_layout.addWidget(brand_frame)

        # Nav body (scrollable)
        nav_body = QWidget()
        nav_body.setStyleSheet("QWidget { background-color: #0f172a; }")
        nav_body_layout = QVBoxLayout(nav_body)
        nav_body_layout.setContentsMargins(10, 14, 10, 14)
        nav_body_layout.setSpacing(2)

        # Quick Intake button
        self.btn_quick_intake = QPushButton("  Quick Intake  (Ctrl+N)")
        self.btn_quick_intake.setIcon(get_icon("plus", "#ffffff", 15))
        self.btn_quick_intake.setFixedHeight(40)
        self.btn_quick_intake.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12.5px;
                font-weight: 700;
                text-align: left;
                margin-bottom: 10px;
            }
            QPushButton:hover { background: #1d4ed8; border-color: #2563eb; }
            QPushButton:pressed { background: #1e40af; }
        """)
        self.btn_quick_intake.clicked.connect(self._handle_quick_job)
        nav_body_layout.addWidget(self.btn_quick_intake)

        # Nav section label
        nav_lbl = QLabel("NAVIGATION")
        nav_lbl.setStyleSheet(
            "color: #475569; font-size: 9.5px; font-weight: 700; "
            "letter-spacing: 1px; padding: 6px 8px 4px 8px;"
        )
        nav_body_layout.addWidget(nav_lbl)

        # Navigation Buttons Group
        self.nav_btn_group = QButtonGroup(self)
        self.nav_btn_group.setExclusive(True)

        self.btn_nav_dashboard = self._create_nav_button("  Dashboard", 0, icon_name="dashboard")
        self.btn_nav_jobs = self._create_nav_button("  Repair Jobs", 1, icon_name="clipboard")
        self.btn_nav_customers = self._create_nav_button("  Customers", 2, icon_name="users")
        self.btn_nav_devices = self._create_nav_button("  Devices", 3, icon_name="phone")

        for btn in (self.btn_nav_dashboard, self.btn_nav_jobs,
                    self.btn_nav_customers, self.btn_nav_devices):
            nav_body_layout.addWidget(btn)

        # Finance section label
        fin_lbl = QLabel("FINANCE")
        fin_lbl.setStyleSheet(
            "color: #475569; font-size: 9.5px; font-weight: 700; "
            "letter-spacing: 1px; padding: 10px 8px 4px 8px;"
        )
        nav_body_layout.addWidget(fin_lbl)

        self.btn_nav_expenses = self._create_nav_button("  Expenses / Kharcha", 4, icon_name="money")
        nav_body_layout.addWidget(self.btn_nav_expenses)

        # Admin section
        adm_lbl = QLabel("ADMIN")
        adm_lbl.setStyleSheet(
            "color: #475569; font-size: 9.5px; font-weight: 700; "
            "letter-spacing: 1px; padding: 10px 8px 4px 8px;"
        )
        nav_body_layout.addWidget(adm_lbl)

        self.btn_nav_settings = self._create_nav_button("  Settings & Users", 5, icon_name="settings")
        nav_body_layout.addWidget(self.btn_nav_settings)

        nav_body_layout.addStretch()
        sidebar_layout.addWidget(nav_body, 1)

        # ── USER CARD (bottom of sidebar) ─────────────────────────────────
        user_footer = QFrame()
        user_footer.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-top: 1px solid #1e293b;
            }
        """)
        uf_lay = QVBoxLayout(user_footer)
        uf_lay.setContentsMargins(12, 10, 12, 12)
        uf_lay.setSpacing(8)

        # User info row
        user_row = QHBoxLayout()
        user_row.setSpacing(10)

        # User avatar circle
        self.user_avatar = QLabel("A")
        self.user_avatar.setFixedSize(36, 36)
        self.user_avatar.setAlignment(Qt.AlignCenter)
        self.user_avatar.setStyleSheet("""
            QLabel {
                background: #1e293b;
                color: #38bdf8;
                border: 1.5px solid #334155;
                border-radius: 18px;
                font-size: 14px;
                font-weight: 900;
            }
        """)
        user_row.addWidget(self.user_avatar)

        user_info = QVBoxLayout()
        user_info.setSpacing(2)

        current_user = AuthService.get_current_user()
        u_name = current_user.full_name if current_user else "Administrator"
        u_role = current_user.role_display if current_user else "Admin / Owner"

        self.lbl_user_name = QLabel(u_name)
        self.lbl_user_name.setStyleSheet("color: #f1f5f9; font-size: 12px; font-weight: 700;")

        self.lbl_user_role = QLabel(u_role)
        self.lbl_user_role.setStyleSheet(
            "color: #38bdf8; font-size: 10.5px; font-weight: 600;"
        )
        user_info.addWidget(self.lbl_user_name)
        user_info.addWidget(self.lbl_user_role)
        user_row.addLayout(user_info)
        user_row.addStretch()
        uf_lay.addLayout(user_row)

        self.btn_logout = QPushButton("  Sign Out")
        self.btn_logout.setIcon(get_icon("logout", "#ef4444", 13))
        self.btn_logout.setFixedHeight(32)
        self.btn_logout.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #ef4444;
                border: 1px solid #334155;
                border-radius: 6px;
                font-size: 11.5px;
                font-weight: 700;
                text-align: left;
                padding: 0 12px;
            }
            QPushButton:hover { background: #450a0a; border-color: #ef4444; }
        """)
        self.btn_logout.clicked.connect(self._handle_logout)
        uf_lay.addWidget(self.btn_logout)

        # Status dot + version
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("background:#10b981; border-radius:4px;")
        status_row.addWidget(dot)
        status_lbl = QLabel("100% Offline  ·  SQLite")
        status_lbl.setStyleSheet("color: #475569; font-size: 10px; font-weight: 600;")
        status_row.addWidget(status_lbl)
        status_row.addStretch()
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setStyleSheet("color: #334155; font-size: 10px;")
        status_row.addWidget(ver_lbl)
        uf_lay.addLayout(status_row)

        sidebar_layout.addWidget(user_footer)

        main_layout.addWidget(sidebar)

        # 2. Right Content Stack
        self.content_stack = QStackedWidget()

        self.view_dashboard = DashboardView()
        self.view_jobs = JobsView()
        self.view_customers = CustomersView()
        self.view_devices = DevicesView()
        self.view_expenses = ExpensesView()
        self.view_settings = SettingsView()

        self.content_stack.addWidget(self.view_dashboard)  # 0
        self.content_stack.addWidget(self.view_jobs)       # 1
        self.content_stack.addWidget(self.view_customers)  # 2
        self.content_stack.addWidget(self.view_devices)    # 3
        self.content_stack.addWidget(self.view_expenses)   # 4
        self.content_stack.addWidget(self.view_settings)   # 5

        # Connect Navigation & Settings Signals
        self.view_dashboard.navigate_to_jobs.connect(lambda: self._set_page(1))
        self.view_dashboard.navigate_to_expenses.connect(lambda: self._set_page(4))
        self.view_settings.database_restored.connect(self._refresh_all_views)
        self.view_settings.logo_updated.connect(self._update_sidebar_brand)
        self.view_settings.settings_saved.connect(self._update_sidebar_brand)

        # Initialize sidebar brand from saved settings
        self._update_sidebar_brand()

        main_layout.addWidget(self.content_stack, 1)

        # Set default tab
        self.btn_nav_dashboard.setChecked(True)
        self.content_stack.setCurrentIndex(0)

    def _create_nav_button(self, text: str, page_index: int, icon_name: Optional[str] = None) -> QPushButton:
        btn = QPushButton(text)
        if icon_name:
            btn.setIcon(get_icon(icon_name, "#94a3b8", 16))
        btn.setCheckable(True)
        btn.setProperty("class", "nav-btn")
        btn.clicked.connect(lambda: self._set_page(page_index))
        self.nav_btn_group.addButton(btn)
        return btn

    def _apply_role_permissions(self):
        """Enforce role-based tab and button visibility."""
        user = AuthService.get_current_user()
        if not user:
            return

        # Update user badge in sidebar
        self.lbl_user_name.setText(user.full_name)
        self.lbl_user_role.setText(user.role_display)
        # Update avatar letter
        initial = user.full_name[0].upper() if user.full_name else "U"
        self.user_avatar.setText(initial)

        if user.role == "technician":
            # Technician view
            self.btn_nav_settings.setVisible(False)
            self.btn_nav_expenses.setVisible(False)
            self.btn_quick_intake.setText("📋 View My Tasks")
            self.btn_quick_intake.clicked.disconnect()
            self.btn_quick_intake.clicked.connect(lambda: self._set_page(1))
        elif user.role == "cashier":
            # Cashier view
            self.btn_nav_settings.setVisible(False)
            self.btn_nav_expenses.setVisible(True)
        else:
            # Admin view
            self.btn_nav_settings.setVisible(True)
            self.btn_nav_expenses.setVisible(True)

    def _set_page(self, index: int):
        self.content_stack.setCurrentIndex(index)
        buttons = [
            self.btn_nav_dashboard,
            self.btn_nav_jobs,
            self.btn_nav_customers,
            self.btn_nav_devices,
            self.btn_nav_expenses,
            self.btn_nav_settings
        ]
        if 0 <= index < len(buttons):
            buttons[index].setChecked(True)

        # Auto refresh view on focus
        current_view = self.content_stack.widget(index)
        if hasattr(current_view, "refresh_data"):
            current_view.refresh_data()
        elif hasattr(current_view, "load_jobs"):
            current_view.load_jobs()
        elif hasattr(current_view, "load_expenses"):
            current_view.load_expenses()
        elif hasattr(current_view, "load_customers"):
            current_view.load_customers()
        elif hasattr(current_view, "load_devices"):
            current_view.load_devices()

    def _setup_shortcuts(self):
        # Ctrl+N -> New Job
        self.shortcut_new_job = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new_job.activated.connect(self._handle_quick_job)

        # F5 -> Refresh current page
        self.shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        self.shortcut_refresh.activated.connect(self._refresh_all_views)

    def _handle_quick_job(self):
        dialog = JobDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh_all_views()
            if dialog.should_print and dialog.saved_job:
                preview = ThermalPrintPreviewDialog(dialog.saved_job, parent=self)
                preview.exec()

    def _handle_logout(self):
        reply = QMessageBox.question(
            self,
            "Sign Out",
            "Are you sure you want to sign out?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            AuthService.logout()
            self.hide()
            login = LoginDialog()
            if login.exec() == QDialog.DialogCode.Accepted:
                self._apply_role_permissions()
                self._refresh_all_views()
                self._set_page(0)
                self.show()
            else:
                self.close()

    def _update_sidebar_brand(self, logo_path: Optional[str] = None):
        """Update sidebar brand logo and shop title when settings change."""
        try:
            settings = SettingsService.get_all_settings()
            if logo_path is None:
                logo_path = settings.get("shop_logo_path", "")

            # Update shop name if present
            shop_name = settings.get("shop_name", "").strip()
            if shop_name:
                self.sidebar_title_lbl.setText(shop_name.upper())
            else:
                self.sidebar_title_lbl.setText("APPLE TECH")

            shop_tagline = settings.get("shop_tagline", "").strip()
            if shop_tagline:
                self.sidebar_sub_lbl.setText(shop_tagline)
            else:
                self.sidebar_sub_lbl.setText("Mobile Repair POS & ERP")

            # Update logo
            if logo_path and Path(logo_path).exists():
                pix = QPixmap(str(logo_path))
                if not pix.isNull():
                    scaled = pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.sidebar_logo_lbl.setText("")
                    self.sidebar_logo_lbl.setPixmap(scaled)
                    self.sidebar_logo_lbl.setStyleSheet("""
                        QLabel {
                            background: #ffffff;
                            border: 1.5px solid #334155;
                            border-radius: 8px;
                            padding: 2px;
                        }
                    """)
                    return
        except Exception as e:
            print(f"Error updating sidebar brand: {e}")

        # Fallback to default gradient circle "A"
        self.sidebar_logo_lbl.setPixmap(QPixmap())
        self.sidebar_logo_lbl.setText("A")
        self.sidebar_logo_lbl.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #2563eb,stop:1 #0284c7);
                color: #ffffff;
                border-radius: 18px;
                font-size: 15px;
                font-weight: 900;
            }
        """)

    def _refresh_all_views(self):
        self.view_dashboard.refresh_data()
        self.view_jobs.load_jobs()
        self.view_customers.load_customers()
        self.view_devices.load_devices()
        self.view_expenses.load_expenses()
        self._update_sidebar_brand()
