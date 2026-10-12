from typing import Optional
from datetime import datetime, timezone
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QDoubleSpinBox, QComboBox,
    QPushButton, QLabel, QGroupBox, QMessageBox, QDateTimeEdit
)
from PySide6.QtCore import Qt, QDateTime

from app.database.models import Expense, ExpenseCategory, PaymentMethod
from app.services.expense_service import ExpenseService
from app.services.auth_service import AuthService


class ExpenseDialog(QDialog):
    """
    Dialog to record a new shop expense or edit an existing expense in White & Blue ERP style.
    """
    def __init__(self, expense: Optional[Expense] = None, parent=None):
        super().__init__(parent)
        self.expense = expense
        self.saved_expense: Optional[Expense] = None

        self.setWindowTitle("Edit Expense" if expense else "Record Shop Expense (Kharcha / Soda)")
        self.setFixedSize(480, 480)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        form_group = QGroupBox("Expense Details")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        # Title
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("e.g. iPhone 13 Screen Purchase, Daily Shop Tea, Electricity Bill")
        form_layout.addRow("Expense Title *:", self.edit_title)

        # Category
        self.combo_category = QComboBox()
        for cat in ExpenseCategory.ALL_CATEGORIES:
            self.combo_category.addItem(cat, cat)
        form_layout.addRow("Category *:", self.combo_category)

        # Amount
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(1.0, 10000000.0)
        self.spin_amount.setPrefix("Rs. ")
        self.spin_amount.setSingleStep(50.0)
        self.spin_amount.setValue(100.0)
        form_layout.addRow("Amount (Rs.) *:", self.spin_amount)

        # Payment Mode
        self.combo_mode = QComboBox()
        for m in PaymentMethod.ALL_METHODS:
            self.combo_mode.addItem(m, m)
        form_layout.addRow("Payment Mode:", self.combo_mode)

        # Reference / Bill No
        self.edit_ref = QLineEdit()
        self.edit_ref.setPlaceholderText("Optional Invoice / Receipt / Transaction #")
        form_layout.addRow("Bill / Ref #:", self.edit_ref)

        # Expense Date
        self.date_edit = QDateTimeEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow("Expense Date:", self.date_edit)

        # Notes
        self.edit_notes = QTextEdit()
        self.edit_notes.setPlaceholderText("Additional notes, vendor name, or details...")
        self.edit_notes.setMaximumHeight(65)
        form_layout.addRow("Notes:", self.edit_notes)

        layout.addWidget(form_group)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_save = QPushButton("Save Expense")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

        # Pre-fill if editing
        if self.expense:
            self.edit_title.setText(self.expense.title)
            idx_c = self.combo_category.findText(self.expense.category)
            if idx_c >= 0:
                self.combo_category.setCurrentIndex(idx_c)
            self.spin_amount.setValue(self.expense.amount)
            idx_m = self.combo_mode.findText(self.expense.payment_mode)
            if idx_m >= 0:
                self.combo_mode.setCurrentIndex(idx_m)
            if self.expense.reference_no:
                self.edit_ref.setText(self.expense.reference_no)
            if self.expense.expense_date:
                self.date_edit.setDateTime(self.expense.expense_date)
            if self.expense.notes:
                self.edit_notes.setPlainText(self.expense.notes)

    def _handle_save(self):
        title = self.edit_title.text().strip()
        amount = self.spin_amount.value()
        category = self.combo_category.currentText()
        payment_mode = self.combo_mode.currentText()
        ref_no = self.edit_ref.text().strip()
        notes = self.edit_notes.toPlainText().strip()
        exp_date = self.date_edit.dateTime().toPython()

        if not title:
            QMessageBox.warning(self, "Validation Error", "Please enter an expense title / description.")
            self.edit_title.setFocus()
            return

        if amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Amount must be greater than zero.")
            return

        current_user = AuthService.get_current_user()
        user_id = current_user.id if current_user else None

        if self.expense:
            success, msg = ExpenseService.update_expense(
                expense_id=self.expense.id,
                title=title,
                amount=amount,
                category=category,
                payment_mode=payment_mode,
                reference_no=ref_no if ref_no else None,
                notes=notes if notes else None,
                expense_date=exp_date
            )
        else:
            success, new_exp, msg = ExpenseService.add_expense(
                title=title,
                amount=amount,
                category=category,
                payment_mode=payment_mode,
                reference_no=ref_no if ref_no else None,
                notes=notes if notes else None,
                created_by_user_id=user_id,
                expense_date=exp_date
            )
            self.saved_expense = new_exp

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Error", msg)
