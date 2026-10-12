from typing import Optional
from datetime import datetime, timedelta, timezone
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QDoubleSpinBox, QComboBox,
    QPushButton, QLabel, QGroupBox, QCheckBox, QMessageBox,
    QDateTimeEdit
)
from PySide6.QtCore import Qt, QDateTime

from app.database.models import RepairJob, Customer, Device, JobStatus
from app.services.customer_service import CustomerService
from app.services.device_service import DeviceService
from app.services.job_service import JobService
from app.services.auth_service import AuthService
from app.ui.dialogs.customer_dialog import CustomerDialog
from app.ui.dialogs.device_dialog import DeviceDialog


class JobDialog(QDialog):
    """
    Dialog for registering a new repair job or editing an existing job in White & Blue ERP style.
    Includes technician assignment, device passcode lock, and delivery target.
    """
    def __init__(self, job: Optional[RepairJob] = None, preselected_customer_id: Optional[int] = None, preselected_device_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.job = job
        self.preselected_customer_id = preselected_customer_id
        self.preselected_device_id = preselected_device_id
        self.saved_job: Optional[RepairJob] = None
        self.should_print: bool = False

        self.setWindowTitle("Edit Repair Job" if job else "New Repair Job Receiving (Intake)")
        self.setMinimumWidth(640)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Customer & Device Selection Section
        cd_group = QGroupBox("1. Customer & Device Selection")
        cd_layout = QVBoxLayout(cd_group)
        cd_layout.setSpacing(10)

        # Customer Row
        cust_row = QHBoxLayout()
        cust_label = QLabel("Customer *:")
        cust_label.setFixedWidth(90)
        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)

        self.btn_new_customer = QPushButton("➕ New Customer")
        self.btn_new_customer.setFixedWidth(135)
        self.btn_new_customer.clicked.connect(self._handle_new_customer)

        cust_row.addWidget(cust_label)
        cust_row.addWidget(self.customer_combo, 1)
        cust_row.addWidget(self.btn_new_customer)
        cd_layout.addLayout(cust_row)

        # Device Row
        dev_row = QHBoxLayout()
        dev_label = QLabel("Device *:")
        dev_label.setFixedWidth(90)
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

        self.btn_new_device = QPushButton("➕ New Device")
        self.btn_new_device.setFixedWidth(135)
        self.btn_new_device.clicked.connect(self._handle_new_device)

        dev_row.addWidget(dev_label)
        dev_row.addWidget(self.device_combo, 1)
        dev_row.addWidget(self.btn_new_device)
        cd_layout.addLayout(dev_row)

        layout.addWidget(cd_group)

        # 2. Job Receiving Details Section
        job_group = QGroupBox("2. Repair Details, Passcode & Technician Assignment")
        job_form = QFormLayout(job_group)
        job_form.setSpacing(8)

        # Job Number
        self.job_number_input = QLineEdit()
        if not self.job:
            self.job_number_input.setText(JobService.generate_job_number())
        self.job_number_input.setReadOnly(True)
        self.job_number_input.setStyleSheet("background-color: #f1f5f9; font-weight: bold; color: #1e40af;")
        job_form.addRow("Job Number:", self.job_number_input)

        # Complaint
        self.complaint_input = QTextEdit()
        self.complaint_input.setPlaceholderText("Customer's description of fault (e.g. Broken screen, water damaged, battery draining fast...)")
        self.complaint_input.setMaximumHeight(60)
        job_form.addRow("Complaint / Fault *:", self.complaint_input)

        # Physical condition
        self.condition_input = QTextEdit()
        self.condition_input.setPlaceholderText("Physical condition upon intake (e.g. Scratches, dent on corner, bent frame)")
        self.condition_input.setMaximumHeight(50)
        job_form.addRow("Physical Condition:", self.condition_input)

        # Passcode / Lock Pattern
        tech_meta_row = QHBoxLayout()
        self.passcode_input = QLineEdit()
        self.passcode_input.setPlaceholderText("e.g. 1234, Pattern: Z-shape, or None")
        tech_meta_row.addWidget(QLabel("🔑 Passcode / Pattern:"))
        tech_meta_row.addWidget(self.passcode_input, 1)

        self.accessories_input = QLineEdit()
        self.accessories_input.setPlaceholderText("e.g. SIM Tray, Case, Box")
        tech_meta_row.addWidget(QLabel("Accessories:"))
        tech_meta_row.addWidget(self.accessories_input, 1)
        job_form.addRow("Security & Items:", tech_meta_row)

        # Technician & Delivery Promise Date Row
        assign_row = QHBoxLayout()
        self.tech_combo = QComboBox()
        self.tech_combo.addItem("Unassigned (General Queue)", None)
        techs = AuthService.list_technicians()
        for t in techs:
            self.tech_combo.addItem(f"🔧 {t.full_name} ({t.username})", t.id)
        assign_row.addWidget(QLabel("Assigned Tech:"))
        assign_row.addWidget(self.tech_combo, 1)

        self.delivery_date_edit = QDateTimeEdit()
        self.delivery_date_edit.setCalendarPopup(True)
        self.delivery_date_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        assign_row.addWidget(QLabel("Promise Date:"))
        assign_row.addWidget(self.delivery_date_edit, 1)
        job_form.addRow("Assignment:", assign_row)

        # Status Dropdown Row
        self.status_combo = QComboBox()
        for s in JobStatus.ALL_STATUSES:
            self.status_combo.addItem(s, s)
        self.status_combo.setCurrentText(JobStatus.IN_PROGRESS)
        job_form.addRow("Repair Status *:", self.status_combo)

        # Financials row
        fin_row = QHBoxLayout()
        self.est_cost_spin = QDoubleSpinBox()
        self.est_cost_spin.setRange(0.0, 1000000.0)
        self.est_cost_spin.setSingleStep(100.0)
        self.est_cost_spin.valueChanged.connect(self._update_balance)

        self.adv_paid_spin = QDoubleSpinBox()
        self.adv_paid_spin.setRange(0.0, 1000000.0)
        self.adv_paid_spin.setSingleStep(100.0)
        self.adv_paid_spin.valueChanged.connect(self._update_balance)

        self.balance_label = QLabel("Rs. 0.00")
        self.balance_label.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 14px;")

        fin_row.addWidget(QLabel("Est. Charges:"))
        fin_row.addWidget(self.est_cost_spin)
        fin_row.addWidget(QLabel("Advance Paid:"))
        fin_row.addWidget(self.adv_paid_spin)
        fin_row.addWidget(QLabel("Balance Due:"))
        fin_row.addWidget(self.balance_label)

        job_form.addRow("Financials:", fin_row)

        layout.addWidget(job_group)

        # Print Slip Checkbox
        self.print_checkbox = QCheckBox("🖨️ Automatically open 3-Inch Thermal Slip Print (Shopkeeper Box Slip / Customer Receipt)")
        self.print_checkbox.setChecked(True)
        self.print_checkbox.setStyleSheet("font-weight: 600; color: #1e40af;")
        layout.addWidget(self.print_checkbox)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Repair Job")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

        # Load initial customer and device data
        self._load_customers()

        # Pre-fill if editing
        if self.job:
            self.job_number_input.setText(self.job.job_number)
            self.complaint_input.setPlainText(self.job.complaint)
            if self.job.physical_condition:
                self.condition_input.setPlainText(self.job.physical_condition)
            if self.job.accessories_received:
                self.accessories_input.setText(self.job.accessories_received)
            if self.job.passcode_lock:
                self.passcode_input.setText(self.job.passcode_lock)
            if self.job.technician_id:
                t_idx = self.tech_combo.findData(self.job.technician_id)
                if t_idx >= 0:
                    self.tech_combo.setCurrentIndex(t_idx)
            if self.job.estimated_delivery_date:
                self.delivery_date_edit.setDateTime(self.job.estimated_delivery_date)

            if self.job.status:
                s_idx = self.status_combo.findData(self.job.status)
                if s_idx >= 0:
                    self.status_combo.setCurrentIndex(s_idx)
                else:
                    self.status_combo.setCurrentText(self.job.status)

            self.est_cost_spin.setValue(self.job.estimated_cost)
            self.adv_paid_spin.setValue(self.job.advance_paid)

            # Lock customer/device on edit
            c_idx = self.customer_combo.findData(self.job.customer_id)
            if c_idx >= 0:
                self.customer_combo.setCurrentIndex(c_idx)
            self.customer_combo.setEnabled(False)
            self.btn_new_customer.setEnabled(False)

            d_idx = self.device_combo.findData(self.job.device_id)
            if d_idx >= 0:
                self.device_combo.setCurrentIndex(d_idx)
            self.device_combo.setEnabled(False)
            self.btn_new_device.setEnabled(False)

        elif self.preselected_customer_id:
            c_idx = self.customer_combo.findData(self.preselected_customer_id)
            if c_idx >= 0:
                self.customer_combo.setCurrentIndex(c_idx)
            if self.preselected_device_id:
                d_idx = self.device_combo.findData(self.preselected_device_id)
                if d_idx >= 0:
                    self.device_combo.setCurrentIndex(d_idx)

    def _load_customers(self):
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        customers = CustomerService.get_all()
        for cust in customers:
            self.customer_combo.addItem(f"{cust.name} ({cust.phone})", cust.id)
        self.customer_combo.blockSignals(False)
        self._on_customer_changed()

    def _on_customer_changed(self):
        customer_id = self.customer_combo.currentData()
        self.device_combo.clear()
        if customer_id:
            devices = DeviceService.get_by_customer(customer_id)
            for dev in devices:
                label = f"{dev.brand} {dev.model}"
                if dev.imei_serial:
                    label += f" [IMEI: {dev.imei_serial}]"
                self.device_combo.addItem(label, dev.id)

            self.btn_new_device.setEnabled(True)
        else:
            self.btn_new_device.setEnabled(False)

        self._on_device_changed()

    def _on_device_changed(self):
        device_id = self.device_combo.currentData()
        if device_id and not self.job and not self.condition_input.toPlainText():
            dev = DeviceService.get_by_id(device_id)
            if dev:
                if dev.physical_condition:
                    self.condition_input.setPlainText(dev.physical_condition)
                if dev.accessories_received:
                    self.accessories_input.setText(dev.accessories_received)

    def _update_balance(self):
        est = self.est_cost_spin.value()
        adv = self.adv_paid_spin.value()
        bal = max(0.0, est - adv)
        self.balance_label.setText(f"Rs. {bal:,.2f}")

    def _handle_new_customer(self):
        dialog = CustomerDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_customer:
            new_cust = dialog.saved_customer
            self._load_customers()
            idx = self.customer_combo.findData(new_cust.id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)

    def _handle_new_device(self):
        cust_id = self.customer_combo.currentData()
        if not cust_id:
            QMessageBox.warning(self, "Warning", "Please select a customer first.")
            return

        dialog = DeviceDialog(preselected_customer_id=cust_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_device:
            new_dev = dialog.saved_device
            self._on_customer_changed()
            idx = self.device_combo.findData(new_dev.id)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)

    def _handle_save(self):
        customer_id = self.customer_combo.currentData()
        device_id = self.device_combo.currentData()
        complaint = self.complaint_input.toPlainText().strip()
        condition = self.condition_input.toPlainText().strip()
        accessories = self.accessories_input.text().strip()
        passcode = self.passcode_input.text().strip()
        tech_id = self.tech_combo.currentData()
        status = self.status_combo.currentText()
        qdt = self.delivery_date_edit.dateTime()
        est_delivery = qdt.toPython()

        est_cost = self.est_cost_spin.value()
        adv_paid = self.adv_paid_spin.value()

        if not customer_id:
            QMessageBox.warning(self, "Validation Error", "Please select or create a customer.")
            return

        if not device_id:
            QMessageBox.warning(self, "Validation Error", "Please select or register a device for this customer.")
            return

        if not complaint:
            QMessageBox.warning(self, "Validation Error", "Please describe customer complaint/fault.")
            self.complaint_input.setFocus()
            return

        try:
            if self.job:
                self.saved_job = JobService.update(
                    job_id=self.job.id,
                    complaint=complaint,
                    physical_condition=condition if condition else None,
                    accessories_received=accessories if accessories else None,
                    passcode_lock=passcode if passcode else None,
                    technician_id=tech_id,
                    estimated_delivery_date=est_delivery,
                    estimated_cost=est_cost,
                    advance_paid=adv_paid,
                    actual_cost=self.job.actual_cost,
                    status=status
                )
            else:
                self.saved_job = JobService.create(
                    customer_id=customer_id,
                    device_id=device_id,
                    complaint=complaint,
                    physical_condition=condition if condition else None,
                    accessories_received=accessories if accessories else None,
                    passcode_lock=passcode if passcode else None,
                    technician_id=tech_id,
                    estimated_delivery_date=est_delivery,
                    estimated_cost=est_cost,
                    advance_paid=adv_paid,
                    custom_job_number=self.job_number_input.text().strip(),
                    status=status
                )

            self.should_print = self.print_checkbox.isChecked()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save job:\n{e}")
