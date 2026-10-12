from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox
)
from app.database.models import Customer
from app.services.customer_service import CustomerService


class CustomerDialog(QDialog):
    """
    Dialog to add a new customer or edit an existing customer.
    """
    def __init__(self, customer: Optional[Customer] = None, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.saved_customer: Optional[Customer] = None

        self.setWindowTitle("Edit Customer" if customer else "Add New Customer")
        self.setMinimumWidth(420)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("👤 Customer Information")
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. John Doe / Muhammad Ali")
        form_layout.addRow("Full Name *:", self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g. 0300-1234567")
        form_layout.addRow("Phone Number *:", self.phone_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("e.g. customer@example.com (optional)")
        form_layout.addRow("Email Address:", self.email_input)

        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("e.g. Street, Sector, City (optional)")
        self.address_input.setMaximumHeight(70)
        form_layout.addRow("Physical Address:", self.address_input)

        layout.addLayout(form_layout)

        # Pre-fill if editing
        if self.customer:
            self.name_input.setText(self.customer.name)
            self.phone_input.setText(self.customer.phone)
            if self.customer.email:
                self.email_input.setText(self.customer.email)
            if self.customer.address:
                self.address_input.setPlainText(self.customer.address)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("class", "btn-secondary")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Customer")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _handle_save(self):
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()
        address = self.address_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Customer name is required.")
            self.name_input.setFocus()
            return

        if not phone:
            QMessageBox.warning(self, "Validation Error", "Customer phone number is required.")
            self.phone_input.setFocus()
            return

        try:
            if self.customer:
                self.saved_customer = CustomerService.update(
                    customer_id=self.customer.id,
                    name=name,
                    phone=phone,
                    email=email if email else None,
                    address=address if address else None
                )
            else:
                self.saved_customer = CustomerService.create(
                    name=name,
                    phone=phone,
                    email=email if email else None,
                    address=address if address else None
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save customer:\n{e}")
