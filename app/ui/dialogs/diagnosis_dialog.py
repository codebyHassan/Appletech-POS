from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTextEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QLabel, QFrame, QMessageBox
)
from app.database.models import RepairJob, JobStatus
from app.services.job_service import JobService
from app.services.auth_service import AuthService


class DiagnosisDialog(QDialog):
    """
    Dialog for technicians to record diagnosis findings, parts needed,
    final costs, and update job status in White & Blue ERP style.
    """
    def __init__(self, job: RepairJob, parent=None):
        super().__init__(parent)
        self.job = job
        self.saved_job: Optional[RepairJob] = None

        self.setWindowTitle(f"Technician Diagnosis & Checklist - {job.job_number}")
        self.setMinimumWidth(540)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Job Summary Card
        summary_card = QFrame()
        summary_card.setProperty("class", "card")
        summary_card.setStyleSheet("QFrame.card { background-color: #eff6ff; border: 1px solid #bfdbfe; }")
        sc_layout = QVBoxLayout(summary_card)
        sc_layout.setSpacing(4)
        sc_layout.setContentsMargins(12, 10, 12, 10)

        pass_txt = f"🔑 <b>Passcode:</b> <span style='color:#1e40af; font-family:monospace;'>{self.job.passcode_lock}</span>" if self.job.passcode_lock else "🔑 <b>Passcode:</b> None / Unlocked"

        job_info = QLabel(f"<b>Job #:</b> <span style='color:#1d4ed8; font-weight:800;'>{self.job.job_number}</span> | <b>Current Status:</b> [{self.job.status}] | {pass_txt}")
        cust_info = QLabel(f"<b>Customer:</b> {self.job.customer.name} ({self.job.customer.phone})")
        dev_info = QLabel(f"<b>Device:</b> {self.job.device.brand} {self.job.device.model} (IMEI/SN: {self.job.device.imei_serial or 'N/A'})")
        comp_info = QLabel(f"<b>Reported Fault:</b> <span style='color:#d97706; font-weight:bold;'>{self.job.complaint}</span>")
        comp_info.setWordWrap(True)

        sc_layout.addWidget(job_info)
        sc_layout.addWidget(cust_info)
        sc_layout.addWidget(dev_info)
        sc_layout.addWidget(comp_info)
        layout.addWidget(summary_card)

        # Diagnosis Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Assigned Tech Combo
        self.tech_combo = QComboBox()
        self.tech_combo.addItem("Unassigned", None)
        techs = AuthService.list_technicians()
        for t in techs:
            self.tech_combo.addItem(f"🔧 {t.full_name}", t.id)
        if self.job.technician_id:
            idx = self.tech_combo.findData(self.job.technician_id)
            if idx >= 0:
                self.tech_combo.setCurrentIndex(idx)
        form_layout.addRow("Assigned Technician:", self.tech_combo)

        self.diagnosis_input = QTextEdit()
        self.diagnosis_input.setPlaceholderText("Detailed technical findings (e.g. Broken backlight coil, display flex cable replaced, tested touch OK...)")
        self.diagnosis_input.setMaximumHeight(85)
        if self.job.technician_diagnosis:
            self.diagnosis_input.setPlainText(self.job.technician_diagnosis)
        form_layout.addRow("Technician Diagnosis *:", self.diagnosis_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Internal parts used, supplier costs, or warranty remarks...")
        self.notes_input.setMaximumHeight(70)
        if self.job.technician_notes:
            self.notes_input.setPlainText(self.job.technician_notes)
        form_layout.addRow("Parts & Notes:", self.notes_input)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0.0, 1000000.0)
        self.cost_spin.setPrefix("Rs. ")
        self.cost_spin.setSingleStep(100.0)
        self.cost_spin.setValue(self.job.actual_cost if self.job.actual_cost > 0 else self.job.estimated_cost)
        form_layout.addRow("Actual / Final Charges:", self.cost_spin)

        self.status_combo = QComboBox()
        for s in JobStatus.ALL_STATUSES:
            self.status_combo.addItem(s, s)
        if self.job.status:
            s_idx = self.status_combo.findData(self.job.status)
            if s_idx >= 0:
                self.status_combo.setCurrentIndex(s_idx)
            else:
                self.status_combo.setCurrentText(self.job.status)
        form_layout.addRow("Update Repair Status:", self.status_combo)

        layout.addLayout(form_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Findings & Status")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _handle_save(self):
        diag = self.diagnosis_input.toPlainText().strip()
        notes = self.notes_input.toPlainText().strip()
        cost = self.cost_spin.value()
        status = self.status_combo.currentText()
        tech_id = self.tech_combo.currentData()

        if not diag:
            QMessageBox.warning(self, "Validation Error", "Please enter technician diagnosis findings.")
            self.diagnosis_input.setFocus()
            return

        try:
            self.saved_job = JobService.update_diagnosis(
                job_id=self.job.id,
                technician_diagnosis=diag,
                technician_notes=notes if notes else None,
                actual_cost=cost,
                status=status,
                technician_id=tech_id
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save diagnosis:\n{e}")
