from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QLabel,
    QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt

from app.database.models import User, UserRole
from app.services.auth_service import AuthService


class UserDialog(QDialog):
    """
    Dialog to create or edit system user accounts (Admin, Cashier, Technician).
    """
    def __init__(self, user: Optional[User] = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Edit User Account" if user else "Create New Staff / User Account")
        self.setFixedSize(420, 420)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        group = QGroupBox("User Account Details")
        form = QFormLayout(group)
        form.setSpacing(10)

        # Full Name
        self.edit_fullname = QLineEdit()
        self.edit_fullname.setPlaceholderText("e.g. Muhammad Ali")
        form.addRow("Full Name *:", self.edit_fullname)

        # Username
        self.edit_username = QLineEdit()
        self.edit_username.setPlaceholderText("e.g. tech_ali, cashier1")
        form.addRow("Username *:", self.edit_username)

        # Password
        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.Password)
        if self.user:
            self.edit_password.setPlaceholderText("Leave blank to keep existing password")
            form.addRow("New Password:", self.edit_password)
        else:
            self.edit_password.setPlaceholderText("Enter at least 4 characters")
            form.addRow("Password *:", self.edit_password)

        # Role
        self.combo_role = QComboBox()
        self.combo_role.addItem("Admin / Owner (Full Access)", UserRole.ADMIN)
        self.combo_role.addItem("Cashier / Front Desk (Intake & Deliveries)", UserRole.CASHIER)
        self.combo_role.addItem("Technician / Repairer (Job To-Do & Diagnosis)", UserRole.TECHNICIAN)
        form.addRow("Role / Access *:", self.combo_role)

        # Phone
        self.edit_phone = QLineEdit()
        self.edit_phone.setPlaceholderText("e.g. 0300-1234567")
        form.addRow("Phone Number:", self.edit_phone)

        # Active status
        self.chk_active = QCheckBox("Account is Active & Allowed to Sign In")
        self.chk_active.setChecked(True)
        form.addRow("", self.chk_active)

        layout.addWidget(group)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_save = QPushButton("Save Account")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

        # Pre-fill if editing
        if self.user:
            self.edit_fullname.setText(self.user.full_name)
            self.edit_username.setText(self.user.username)
            self.edit_username.setEnabled(False) # Cannot rename username
            idx_r = self.combo_role.findData(self.user.role)
            if idx_r >= 0:
                self.combo_role.setCurrentIndex(idx_r)
            if self.user.phone:
                self.edit_phone.setText(self.user.phone)
            self.chk_active.setChecked(self.user.is_active)

    def _handle_save(self):
        fullname = self.edit_fullname.text().strip()
        username = self.edit_username.text().strip()
        password = self.edit_password.text().strip()
        role = self.combo_role.currentData()
        phone = self.edit_phone.text().strip()
        is_active = self.chk_active.isChecked()

        if not fullname:
            QMessageBox.warning(self, "Validation Error", "Full Name is required.")
            self.edit_fullname.setFocus()
            return

        if self.user:
            success, msg = AuthService.update_user(
                user_id=self.user.id,
                full_name=fullname,
                role=role,
                phone=phone,
                is_active=is_active,
                new_password=password if password else None
            )
        else:
            if not username:
                QMessageBox.warning(self, "Validation Error", "Username is required.")
                self.edit_username.setFocus()
                return
            if not password:
                QMessageBox.warning(self, "Validation Error", "Password is required.")
                self.edit_password.setFocus()
                return

            success, msg = AuthService.create_user(
                username=username,
                password=password,
                full_name=fullname,
                role=role,
                phone=phone
            )

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Error", msg)
