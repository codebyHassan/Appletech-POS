import os
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QSpinBox,
    QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QAbstractItemView,
    QScrollArea, QFrame, QTabWidget, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from app.config import get_database_path, get_app_data_dir
from app.services.backup_service import BackupService, SettingsService
from app.services.auth_service import AuthService
from app.ui.icons import get_icon
from app.ui.dialogs.user_dialog import UserDialog


class SettingsView(QWidget):
    """
    Shop Profile & Settings, Thermal Slip Customization,
    Staff User Accounts (RBAC), and Database Backup/Restore.
    """
    settings_saved = Signal()
    database_restored = Signal()
    logo_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_settings()
        self.load_users()
        self.load_backups()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header Row
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        page_title = QLabel("⚙️ Shop Settings & Administration")
        page_title.setProperty("class", "page-title")
        page_subtitle = QLabel("Configure shop receipt branding, manage staff accounts & permissions, and secure offline database backups.")
        page_subtitle.setProperty("class", "page-subtitle")

        title_box.addWidget(page_title)
        title_box.addWidget(page_subtitle)
        main_layout.addLayout(title_box)

        # Main Tab Widget
        self.tab_widget = QTabWidget()

        # ==========================================
        # TAB 1: Shop Profile & Receipt Customization
        # ==========================================
        tab_shop = QWidget()
        tab_shop_outer = QVBoxLayout(tab_shop)
        tab_shop_outer.setContentsMargins(0, 0, 0, 0)
        tab_shop_outer.setSpacing(0)

        shop_scroll = QScrollArea()
        shop_scroll.setWidgetResizable(True)
        shop_scroll.setFrameShape(QFrame.NoFrame)
        shop_scroll.setObjectName("shopScroll")
        shop_scroll.setStyleSheet("#shopScroll { background: #ffffff; border: none; }")
        shop_scroll.viewport().setObjectName("shopViewport")
        shop_scroll.viewport().setStyleSheet("#shopViewport { background: #ffffff; }")

        shop_inner = QWidget()
        shop_inner.setObjectName("shopInner")
        shop_inner.setStyleSheet("#shopInner { background: #ffffff; }")
        tab_shop_layout = QVBoxLayout(shop_inner)
        tab_shop_layout.setContentsMargins(12, 12, 12, 12)
        tab_shop_layout.setSpacing(14)

        shop_group = QGroupBox("🏪  Shop Profile & 3-Inch Thermal Slip Details")
        shop_grid = QGridLayout(shop_group)
        shop_grid.setHorizontalSpacing(18)
        shop_grid.setVerticalSpacing(16)
        shop_grid.setContentsMargins(18, 24, 18, 20)

        self.shop_name_input = QLineEdit()
        self.shop_name_input.setPlaceholderText("e.g. APPLE TECH MOBILE CARE")
        shop_grid.addWidget(
            self._labeled_field("Shop Name", self.shop_name_input, required=True), 0, 0, 1, 2
        )

        self.shop_tagline_input = QLineEdit()
        self.shop_tagline_input.setPlaceholderText("e.g. Professional Smartphone & Tablet Repair Solutions")
        shop_grid.addWidget(
            self._labeled_field("Tagline / Subtitle", self.shop_tagline_input), 1, 0, 1, 2
        )

        self.shop_phone_input = QLineEdit()
        self.shop_phone_input.setPlaceholderText("e.g. +92 300 1234567 / 0312-9876543")
        shop_grid.addWidget(
            self._labeled_field("Contact Phone(s)", self.shop_phone_input), 2, 0
        )

        self.currency_input = QLineEdit()
        self.currency_input.setPlaceholderText("e.g. Rs. or $")
        shop_grid.addWidget(
            self._labeled_field("Currency Symbol", self.currency_input), 2, 1
        )

        self.shop_url_input = QLineEdit()
        self.shop_url_input.setPlaceholderText("e.g. https://www.yourshop.com")
        shop_grid.addWidget(
            self._labeled_field(
                "Website / URL",
                self.shop_url_input,
                hint="Printed as a scannable QR code on the customer receipt and delivery invoice.",
            ), 3, 0, 1, 2
        )

        self.shop_address_input = QLineEdit()
        self.shop_address_input.setPlaceholderText("e.g. Shop # 12, Tech Plaza, Main Market")
        shop_grid.addWidget(
            self._labeled_field("Shop Address", self.shop_address_input), 4, 0, 1, 2
        )

        self.terms_input = QTextEdit()
        self.terms_input.setPlaceholderText("Terms printed at bottom of customer receipt slips...")
        self.terms_input.setFixedHeight(84)
        shop_grid.addWidget(
            self._labeled_field("Customer Slip Terms", self.terms_input), 5, 0, 1, 2
        )

        shop_grid.setColumnStretch(0, 1)
        shop_grid.setColumnStretch(1, 1)

        tab_shop_layout.addWidget(shop_group)

        # ── LOGO UPLOAD CARD ──────────────────────────────────────────────
        logo_group = QGroupBox("🖼️  Shop Logo for Thermal Slips")
        logo_lay = QHBoxLayout(logo_group)
        logo_lay.setSpacing(20)
        logo_lay.setContentsMargins(14, 14, 14, 14)

        # Preview box
        self.logo_preview = QLabel("No logo\nuploaded")
        self.logo_preview.setFixedSize(110, 110)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setStyleSheet("""
            QLabel {
                background: #f8fafc;
                border: 2px dashed #cbd5e1;
                border-radius: 10px;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        logo_lay.addWidget(self.logo_preview)

        # Right: info + buttons
        logo_right = QVBoxLayout()
        logo_right.setSpacing(8)

        logo_info = QLabel(
            "Upload your shop logo to print on 3-inch thermal slips.\n"
            "Recommended: PNG or JPG, square format (300×300 px), max 2 MB."
        )
        logo_info.setWordWrap(True)
        logo_info.setStyleSheet("font-size: 12px; color: #475569;")
        logo_right.addWidget(logo_info)

        # Current path label
        self.logo_path_lbl = QLabel("No logo selected")
        self.logo_path_lbl.setStyleSheet(
            "font-size: 10.5px; color: #94a3b8; font-family: Consolas; "
            "background: #f1f5f9; border-radius: 4px; padding: 4px 8px;"
        )
        self.logo_path_lbl.setWordWrap(True)
        logo_right.addWidget(self.logo_path_lbl)

        btn_row_logo = QHBoxLayout()
        btn_row_logo.setSpacing(8)

        self.btn_upload_logo = QPushButton("  Upload Logo...")
        self.btn_upload_logo.setIcon(get_icon("plus", "#ffffff", 15))
        self.btn_upload_logo.setFixedHeight(36)
        self.btn_upload_logo.setStyleSheet("""
            QPushButton {
                background: #2563eb; color: #ffffff;
                border: none; border-radius: 7px;
                font-size: 12.5px; font-weight: 700; padding: 0 14px;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        self.btn_upload_logo.clicked.connect(self._handle_logo_upload)
        btn_row_logo.addWidget(self.btn_upload_logo)

        self.btn_clear_logo = QPushButton("  Remove Logo")
        self.btn_clear_logo.setIcon(get_icon("trash", "#dc2626", 14))
        self.btn_clear_logo.setFixedHeight(36)
        self.btn_clear_logo.setStyleSheet("""
            QPushButton {
                background: #fef2f2; color: #dc2626;
                border: 1px solid #fecaca; border-radius: 7px;
                font-size: 12.5px; font-weight: 700; padding: 0 14px;
            }
            QPushButton:hover { background: #fee2e2; border-color: #ef4444; }
        """)
        self.btn_clear_logo.clicked.connect(self._handle_clear_logo)
        btn_row_logo.addWidget(self.btn_clear_logo)
        btn_row_logo.addStretch()
        logo_right.addLayout(btn_row_logo)
        logo_right.addStretch()

        logo_lay.addLayout(logo_right, 1)
        tab_shop_layout.addWidget(logo_group)

        # ── SAVE BUTTON ───────────────────────────────────────────────────
        btn_save_row = QHBoxLayout()
        btn_save_settings = QPushButton("  Save Shop Profile & Slips")
        btn_save_settings.setIcon(get_icon("check", "#ffffff", 16))
        btn_save_settings.setFixedHeight(40)
        btn_save_settings.setStyleSheet("""
            QPushButton {
                background: #2563eb; color: #ffffff;
                border: none; border-radius: 8px;
                font-size: 13px; font-weight: 700; padding: 0 22px;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        btn_save_settings.clicked.connect(self._handle_save_settings)
        btn_save_row.addStretch()
        btn_save_row.addWidget(btn_save_settings)
        tab_shop_layout.addLayout(btn_save_row)
        tab_shop_layout.addStretch()

        shop_scroll.setWidget(shop_inner)
        tab_shop_outer.addWidget(shop_scroll)
        self.tab_widget.addTab(tab_shop, " Shop Profile & Slips")

        # ==========================================
        # TAB 2: User Accounts & RBAC
        # ==========================================
        tab_users = QWidget()
        tab_users_layout = QVBoxLayout(tab_users)
        tab_users_layout.setContentsMargins(12, 12, 12, 12)
        tab_users_layout.setSpacing(12)

        user_header_layout = QHBoxLayout()
        user_header_lbl = QLabel("Manage system login accounts for technicians, cashiers, and managers:")
        user_header_lbl.setStyleSheet("color: #475569; font-size: 12.5px;")
        user_header_layout.addWidget(user_header_lbl)
        user_header_layout.addStretch()

        btn_add_user = QPushButton("  Add New User Account")
        btn_add_user.setIcon(get_icon("plus", "#ffffff", 16))
        btn_add_user.setProperty("class", "btn-primary")
        btn_add_user.setFixedHeight(38)
        btn_add_user.clicked.connect(self._handle_add_user)
        user_header_layout.addWidget(btn_add_user)
        tab_users_layout.addLayout(user_header_layout)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Full Name", "Role / Access", "Status", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.verticalHeader().setDefaultSectionSize(44)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setShowGrid(False)
        self.user_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                gridline-color: transparent;
                font-size: 12.5px;
                color: #0f172a;
                selection-background-color: #eff6ff;
                selection-color: #1e40af;
            }
            QTableWidget::item {
                padding: 9px 10px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #eff6ff;
                color: #1e40af;
            }
            QTableWidget::item:alternate {
                background-color: #fafafa;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                padding: 10px 10px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 0.6px;
            }
        """)
        tab_users_layout.addWidget(self.user_table, 1)

        self.tab_widget.addTab(tab_users, " Staff Accounts & Permissions")

        # ==========================================
        # TAB 3: Database Backup & Maintenance
        # ==========================================
        tab_db = QWidget()
        tab_db_layout = QVBoxLayout(tab_db)
        tab_db_layout.setContentsMargins(12, 12, 12, 12)
        tab_db_layout.setSpacing(12)

        db_path = get_database_path()
        path_label = QLabel(
            f"<b>Active Database Path:</b> <span style='color:#1e40af; font-family: Consolas;'>{db_path}</span><br>"
            "<span style='color:#64748b; font-size: 11.5px;'>Data is safely stored in user AppData and persists permanently across application updates.</span>"
        )
        path_label.setWordWrap(True)
        tab_db_layout.addWidget(path_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_backup_now = QPushButton("  Create Backup Now")
        self.btn_backup_now.setIcon(get_icon("box", "#ffffff", 16))
        self.btn_backup_now.setProperty("class", "btn-success")
        self.btn_backup_now.setFixedHeight(38)
        self.btn_backup_now.clicked.connect(self._handle_create_backup)
        btn_row.addWidget(self.btn_backup_now)

        self.btn_restore = QPushButton("  Restore from Backup...")
        self.btn_restore.setIcon(get_icon("refresh", "#334155", 16))
        self.btn_restore.setFixedHeight(38)
        self.btn_restore.clicked.connect(self._handle_restore_backup)
        btn_row.addWidget(self.btn_restore)

        self.btn_open_folder = QPushButton("  Open Backup Folder")
        self.btn_open_folder.setFixedHeight(38)
        self.btn_open_folder.clicked.connect(self._handle_open_backup_folder)
        btn_row.addWidget(self.btn_open_folder)

        btn_row.addStretch()
        tab_db_layout.addLayout(btn_row)

        tab_db_layout.addWidget(QLabel("Available Backups in Storage:"))
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(["Backup Filename", "Created On", "Size", "Actions"])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backup_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.backup_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.backup_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.backup_table.verticalHeader().setVisible(False)
        self.backup_table.verticalHeader().setDefaultSectionSize(44)
        self.backup_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.backup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.setShowGrid(False)
        self.backup_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                gridline-color: transparent;
                font-size: 12.5px;
                color: #0f172a;
                selection-background-color: #eff6ff;
                selection-color: #1e40af;
            }
            QTableWidget::item {
                padding: 9px 10px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #eff6ff;
                color: #1e40af;
            }
            QTableWidget::item:alternate {
                background-color: #fafafa;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                padding: 10px 10px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 0.6px;
            }
        """)
        tab_db_layout.addWidget(self.backup_table, 1)

        self.tab_widget.addTab(tab_db, "🗄️ Database Backup & Restore")

        main_layout.addWidget(self.tab_widget, 1)

    def _labeled_field(self, label: str, widget: QWidget, required: bool = False, hint: str = "") -> QWidget:
        """Stack a bold caption (and optional hint) above an input for a tidy form."""
        box = QWidget()
        box.setObjectName("fieldBox")
        box.setStyleSheet("#fieldBox { background: #ffffff; }")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        caption = QLabel(
            f'{label} <span style="color:#dc2626;">*</span>' if required else label
        )
        caption.setStyleSheet(
            "color: #334155; font-size: 12px; font-weight: 700; background: transparent;"
        )
        lay.addWidget(caption)

        if isinstance(widget, QLineEdit):
            widget.setMinimumHeight(38)
        lay.addWidget(widget)

        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setWordWrap(True)
            hint_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
            lay.addWidget(hint_lbl)
        return box

    def load_settings(self):
        settings = SettingsService.get_all_settings()
        self.shop_name_input.setText(settings.get("shop_name", ""))
        self.shop_tagline_input.setText(settings.get("shop_tagline", ""))
        self.shop_phone_input.setText(settings.get("shop_phone", ""))
        self.shop_address_input.setText(settings.get("shop_address", ""))
        self.shop_url_input.setText(settings.get("shop_url", ""))
        self.currency_input.setText(settings.get("currency_symbol", "Rs."))
        self.terms_input.setPlainText(settings.get("terms_conditions", ""))
        # Load existing logo if saved
        logo_path = settings.get("shop_logo_path", "")
        if logo_path and Path(logo_path).exists():
            self._update_logo_preview(logo_path)
        else:
            self._clear_logo_preview()

    def _handle_save_settings(self):
        settings = {
            "shop_name": self.shop_name_input.text().strip(),
            "shop_tagline": self.shop_tagline_input.text().strip(),
            "shop_phone": self.shop_phone_input.text().strip(),
            "shop_address": self.shop_address_input.text().strip(),
            "shop_url": self.shop_url_input.text().strip(),
            "currency_symbol": self.currency_input.text().strip(),
            "terms_conditions": self.terms_input.toPlainText().strip(),
        }

        try:
            SettingsService.save_settings(settings)
            QMessageBox.information(self, "Success", "Shop settings saved successfully.")
            self.settings_saved.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")

    # ─── LOGO HANDLERS ───────────────────────────────────────────────────────

    def _handle_logo_upload(self):
        """Open file picker, copy selected image to AppData, save path to settings."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Shop Logo Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)"
        )
        if not file_path:
            return

        src = Path(file_path)

        # Validate size (max 2 MB)
        if src.stat().st_size > 2 * 1024 * 1024:
            QMessageBox.warning(
                self, "File Too Large",
                "Logo file must be smaller than 2 MB.\nPlease resize the image and try again."
            )
            return

        # Copy to persistent AppData directory
        dest_dir = get_app_data_dir()
        dest = dest_dir / f"shop_logo{src.suffix.lower()}"
        shutil.copy2(str(src), str(dest))

        # Save path to settings DB
        SettingsService.save_settings({"shop_logo_path": str(dest)})

        self._update_logo_preview(str(dest))
        self.logo_updated.emit(str(dest))
        self.settings_saved.emit()
        QMessageBox.information(
            self, "Logo Saved",
            f"Logo uploaded and saved successfully!\n\nSaved to: {dest.name}"
        )

    def _handle_clear_logo(self):
        """Remove logo from settings and delete file from AppData."""
        confirm = QMessageBox.question(
            self, "Remove Logo",
            "Are you sure you want to remove the shop logo?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        # Delete file if exists
        settings = SettingsService.get_all_settings()
        logo_path = settings.get("shop_logo_path", "")
        if logo_path:
            p = Path(logo_path)
            if p.exists():
                p.unlink(missing_ok=True)

        # Clear from settings
        SettingsService.save_settings({"shop_logo_path": ""})
        self._clear_logo_preview()
        self.logo_updated.emit("")
        self.settings_saved.emit()
        QMessageBox.information(self, "Logo Removed", "Shop logo has been removed.")

    def _update_logo_preview(self, path: str):
        """Show thumbnail in the preview box and update the path label."""
        px = QPixmap(path)
        if not px.isNull():
            self.logo_preview.setPixmap(
                px.scaled(106, 106, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.logo_preview.setStyleSheet("""
                QLabel {
                    background: #ffffff;
                    border: 2px solid #2563eb;
                    border-radius: 10px;
                    padding: 2px;
                }
            """)
            filename = Path(path).name
            self.logo_path_lbl.setText(filename)
            self.logo_path_lbl.setStyleSheet(
                "font-size: 10.5px; color: #1e40af; font-family: Consolas; "
                "background: #eff6ff; border-radius: 4px; padding: 4px 8px;"
            )

    def _clear_logo_preview(self):
        """Reset preview to placeholder state."""
        self.logo_preview.setPixmap(QPixmap())
        self.logo_preview.setText("No logo\nuploaded")
        self.logo_preview.setStyleSheet("""
            QLabel {
                background: #f8fafc;
                border: 2px dashed #cbd5e1;
                border-radius: 10px;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        self.logo_path_lbl.setText("No logo selected")
        self.logo_path_lbl.setStyleSheet(
            "font-size: 10.5px; color: #94a3b8; font-family: Consolas; "
            "background: #f1f5f9; border-radius: 4px; padding: 4px 8px;"
        )

    def load_users(self):
        users = AuthService.list_users(include_inactive=True)
        self.user_table.setRowCount(len(users))

        for row, u in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(f"#{u.id}"))
            self.user_table.setItem(row, 1, QTableWidgetItem(u.username))
            self.user_table.setItem(row, 2, QTableWidgetItem(u.full_name))
            
            role_label = u.role_display
            item_role = QTableWidgetItem(role_label)
            item_role.setTextAlignment(Qt.AlignCenter)
            self.user_table.setItem(row, 3, item_role)

            status_text = "🟢 Active" if u.is_active else "🔴 Deactivated"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            self.user_table.setItem(row, 4, item_status)

            act_w = QWidget()
            act_w.setStyleSheet("QWidget { background: transparent; }")
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(6, 4, 6, 4)
            act_l.setSpacing(5)

            btn_edit = QPushButton("  Edit & Password")
            btn_edit.setIcon(get_icon("edit", "#15803d", 14))
            btn_edit.setProperty("class", "btn-tbl-edit")
            btn_edit.setFixedHeight(30)
            btn_edit.setToolTip("Edit User and Password")
            btn_edit.clicked.connect(lambda _, user=u: self._handle_edit_user(user))
            act_l.addWidget(btn_edit)
            self.user_table.setCellWidget(row, 5, act_w)

    def _handle_add_user(self):
        dialog = UserDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_users()

    def _handle_edit_user(self, user):
        dialog = UserDialog(user=user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_users()

    def load_backups(self):
        backups = BackupService.list_backups()
        self.backup_table.setRowCount(len(backups))

        for row, bak in enumerate(backups):
            self.backup_table.setItem(row, 0, QTableWidgetItem(bak["filename"]))
            self.backup_table.setItem(row, 1, QTableWidgetItem(bak["modified"]))
            self.backup_table.setItem(row, 2, QTableWidgetItem(bak["size_kb"]))

            act_w = QWidget()
            act_w.setStyleSheet("QWidget { background: transparent; }")
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(6, 4, 6, 4)
            act_l.setSpacing(5)

            btn_restore_this = QPushButton("  Restore")
            btn_restore_this.setIcon(get_icon("refresh", "#1d4ed8", 14))
            btn_restore_this.setProperty("class", "btn-tbl-print")
            btn_restore_this.setFixedHeight(30)
            btn_restore_this.setToolTip("Restore Database from this Backup")
            btn_restore_this.clicked.connect(lambda _, path=bak["filepath"]: self._restore_file(path))
            act_l.addWidget(btn_restore_this)
            self.backup_table.setCellWidget(row, 3, act_w)

    def _handle_create_backup(self):
        try:
            path = BackupService.create_backup()
            self.load_backups()
            QMessageBox.information(
                self,
                "Backup Created",
                f"Database backup created successfully:\n{path.name}\n\nLocation: {path.parent}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Failed to create database backup:\n{e}")

    def _handle_restore_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database Backup File",
            str(BackupService.get_backup_dir()),
            "SQLite Database (*.db *.sqlite);;All Files (*.*)"
        )
        if file_path:
            self._restore_file(file_path)

    def _restore_file(self, file_path: str):
        confirm = QMessageBox.warning(
            self,
            "Confirm Database Restore",
            "Are you sure you want to restore the database from this backup?\n\n"
            "⚠️ Current data will be replaced by the data in this backup file.\n"
            f"Source: {file_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                BackupService.restore_backup(file_path)
                QMessageBox.information(
                    self,
                    "Restore Successful",
                    "Database has been successfully restored!\nThe application data has been refreshed."
                )
                self.database_restored.emit()
            except Exception as e:
                QMessageBox.critical(self, "Restore Error", f"Failed to restore database:\n{e}")

    def _handle_open_backup_folder(self):
        backup_dir = BackupService.get_backup_dir()
        if os.name == 'nt':
            os.startfile(str(backup_dir))
        else:
            import subprocess
            subprocess.run(["xdg-open", str(backup_dir)])
