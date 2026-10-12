from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QComboBox
)
from app.database.models import Device, Customer
from app.services.device_service import DeviceService
from app.services.customer_service import CustomerService


class DeviceDialog(QDialog):
    """
    Dialog to register a new device or edit existing device specifications.
    """
    def __init__(self, device: Optional[Device] = None, preselected_customer_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.device = device
        self.preselected_customer_id = preselected_customer_id
        self.saved_device: Optional[Device] = None

        self.setWindowTitle("Edit Device" if device else "Register New Device")
        self.setMinimumWidth(440)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📱 Device Specifications")
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Customer Selector
        self.customer_combo = QComboBox()
        self._load_customers()
        form_layout.addRow("Owner (Customer) *:", self.customer_combo)

        # Brand Selector / Input
        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.addItems([
            "Apple", "Samsung", "Xiaomi", "Redmi", "Poco",
            "Google Pixel", "OnePlus", "Vivo", "Oppo", "Realme",
            "Huawei", "Honor", "Infinix", "Tecno", "Motorola", "Other"
        ])
        form_layout.addRow("Brand *:", self.brand_combo)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g. iPhone 13 Pro Max / Galaxy S22 Ultra")
        form_layout.addRow("Model Name / Number *:", self.model_input)

        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("15-digit IMEI or Serial Number (optional)")
        form_layout.addRow("IMEI / Serial:", self.imei_input)

        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("e.g. Space Black, Alpine Green")
        form_layout.addRow("Color:", self.color_input)

        self.accessories_input = QLineEdit()
        self.accessories_input.setPlaceholderText("e.g. SIM Tray, Back Cover, Box, Charger")
        form_layout.addRow("Accessories Received:", self.accessories_input)

        self.condition_input = QTextEdit()
        self.condition_input.setPlaceholderText("e.g. Broken front glass, scratches on edges, water damaged")
        self.condition_input.setMaximumHeight(65)
        form_layout.addRow("Physical Condition:", self.condition_input)

        layout.addLayout(form_layout)

        # Pre-fill values
        if self.device:
            self.brand_combo.setCurrentText(self.device.brand)
            self.model_input.setText(self.device.model)
            if self.device.imei_serial:
                self.imei_input.setText(self.device.imei_serial)
            if self.device.color:
                self.color_input.setText(self.device.color)
            if self.device.accessories_received:
                self.accessories_input.setText(self.device.accessories_received)
            if self.device.physical_condition:
                self.condition_input.setPlainText(self.device.physical_condition)

            # Select customer in combo
            idx = self.customer_combo.findData(self.device.customer_id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
            self.customer_combo.setEnabled(False) # lock owner on edit

        elif self.preselected_customer_id:
            idx = self.customer_combo.findData(self.preselected_customer_id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
                self.customer_combo.setEnabled(False)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("class", "btn-secondary")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Device")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_customers(self):
        self.customer_combo.clear()
        customers = CustomerService.get_all()
        for cust in customers:
            self.customer_combo.addItem(f"{cust.name} ({cust.phone})", cust.id)

    def _handle_save(self):
        customer_id = self.customer_combo.currentData()
        brand = self.brand_combo.currentText().strip()
        model = self.model_input.text().strip()
        imei = self.imei_input.text().strip()
        color = self.color_input.text().strip()
        accessories = self.accessories_input.text().strip()
        condition = self.condition_input.toPlainText().strip()

        if not customer_id:
            QMessageBox.warning(self, "Validation Error", "Please select a customer first.")
            return

        if not brand:
            QMessageBox.warning(self, "Validation Error", "Brand is required.")
            self.brand_combo.setFocus()
            return

        if not model:
            QMessageBox.warning(self, "Validation Error", "Model is required.")
            self.model_input.setFocus()
            return

        try:
            if self.device:
                self.saved_device = DeviceService.update(
                    device_id=self.device.id,
                    brand=brand,
                    model=model,
                    imei_serial=imei if imei else None,
                    color=color if color else None,
                    accessories_received=accessories if accessories else None,
                    physical_condition=condition if condition else None
                )
            else:
                self.saved_device = DeviceService.create(
                    customer_id=customer_id,
                    brand=brand,
                    model=model,
                    imei_serial=imei if imei else None,
                    color=color if color else None,
                    accessories_received=accessories if accessories else None,
                    physical_condition=condition if condition else None
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save device:\n{e}")
