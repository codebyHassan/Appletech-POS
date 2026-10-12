from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QAbstractItemView, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from app.database.models import RepairJob, JobStatus
from app.services.job_service import JobService
from app.services.auth_service import AuthService
from app.services.expense_service import ExpenseService
from app.ui.icons import get_icon
from app.ui.components.stat_card import StatCard
from app.ui.components.status_badge import StatusBadge
from app.ui.components.print_preview_dialog import ThermalPrintPreviewDialog
from app.ui.dialogs.job_dialog import JobDialog
from app.ui.dialogs.diagnosis_dialog import DiagnosisDialog


class DashboardView(QWidget):
    """
    Main Dashboard View with White & Blue ERP style, KPI metrics,
    fast action triggers, and recent jobs overview.
    """
    navigate_to_jobs = Signal()
    navigate_to_new_job = Signal()
    navigate_to_customers = Signal()
    navigate_to_expenses = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── TOP HEADER BAR ──────────────────────────────────────────────
        header_bar = QFrame()
        header_bar.setStyleSheet("""
            QFrame { background: #ffffff; border-bottom: 1px solid #e2e8f0; }
        """)
        header_bar.setFixedHeight(72)
        hb_lay = QHBoxLayout(header_bar)
        hb_lay.setContentsMargins(24, 0, 20, 0)
        hb_lay.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        pg_title = QLabel("Workshop Dashboard")
        pg_title.setStyleSheet(
            "font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px;"
        )
        pg_sub = QLabel("Overview of repairs, workshop queues, and quick operational shortcuts")
        pg_sub.setStyleSheet("font-size: 12px; color: #64748b;")
        title_col.addWidget(pg_title)
        title_col.addWidget(pg_sub)
        hb_lay.addLayout(title_col)
        hb_lay.addStretch()

        self.btn_new_job = QPushButton("  Quick Intake  (Ctrl+N)")
        self.btn_new_job.setIcon(get_icon("plus", "#ffffff", 16))
        self.btn_new_job.setFixedHeight(40)
        self.btn_new_job.setStyleSheet("""
            QPushButton {
                background: #2563eb; color: #ffffff; border: none;
                border-radius: 8px; padding: 0 20px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:pressed { background: #1e40af; }
        """)
        self.btn_new_job.clicked.connect(self._handle_new_job)
        hb_lay.addWidget(self.btn_new_job)

        self.btn_refresh = QPushButton("  Refresh")
        self.btn_refresh.setIcon(get_icon("refresh", "#334155", 15))
        self.btn_refresh.setFixedHeight(40)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #334155;
                border: 1px solid #cbd5e1; border-radius: 8px;
                padding: 0 14px; font-size: 12.5px; font-weight: 600;
            }
            QPushButton:hover { background: #f1f5f9; }
        """)
        self.btn_refresh.clicked.connect(self.refresh_data)
        hb_lay.addWidget(self.btn_refresh)

        layout.addWidget(header_bar)

        # ── SCROLLABLE BODY ────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("QWidget { background: #f8fafc; }")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(20)

        # ── KPI STAT CARDS (SVG icon version) ──────────────────────
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self.card_customers = StatCard("Customers",  "0", "users",     "#0284c7")
        self.card_jobs      = StatCard("Total Jobs", "0", "clipboard", "#2563eb")
        self.card_pending   = StatCard("Diagnosing", "0", "search",    "#7c3aed")
        self.card_progress  = StatCard("In Progress","0", "wrench",    "#d97706")
        self.card_ready     = StatCard("Ready",      "0", "check",     "#16a34a")
        self.card_delivered = StatCard("Delivered",  "0", "box",       "#475569")

        for card in (self.card_customers, self.card_jobs, self.card_pending,
                     self.card_progress, self.card_ready, self.card_delivered):
            stats_layout.addWidget(card)
        body_lay.addLayout(stats_layout)

        # ── SECTION HEADER ─────────────────────────────────────
        tbl_header = QHBoxLayout()
        sec_title = QLabel("Recent Repair Jobs & Queue")
        sec_title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #0f172a;"
        )
        tbl_header.addWidget(sec_title)
        tbl_header.addStretch()

        self.btn_view_all_jobs = QPushButton("View All Jobs & Filters →")
        self.btn_view_all_jobs.setFixedHeight(34)
        self.btn_view_all_jobs.setStyleSheet("""
            QPushButton {
                background: #eff6ff; color: #1d4ed8;
                border: 1px solid #bfdbfe; border-radius: 7px;
                padding: 0 12px; font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #dbeafe; }
        """)
        self.btn_view_all_jobs.clicked.connect(lambda: self.navigate_to_jobs.emit())
        tbl_header.addWidget(self.btn_view_all_jobs)
        body_lay.addLayout(tbl_header)

        # ── RECENT JOBS TABLE ────────────────────────────────────
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(8)
        self.jobs_table.setHorizontalHeaderLabels([
            "JOB #", "CUSTOMER", "DEVICE & MODEL", "FAULT / ISSUE",
            "PASSCODE", "STATUS", "BALANCE DUE", "ACTIONS"
        ])
        hh = self.jobs_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        hh.setHighlightSections(False)

        self.jobs_table.verticalHeader().setVisible(False)
        self.jobs_table.verticalHeader().setDefaultSectionSize(44)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.jobs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setShowGrid(False)
        self.jobs_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                font-size: 12.5px;
                selection-background-color: #eff6ff;
                selection-color: #1e40af;
            }
            QTableWidget::item { padding: 9px 10px; border-bottom: 1px solid #f1f5f9; }
            QTableWidget::item:selected { background: #eff6ff; color: #1e40af; }
            QTableWidget::item:alternate { background: #fafafa; }
            QHeaderView::section {
                background: #f8fafc; color: #64748b;
                padding: 10px; border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: 700; font-size: 11px; letter-spacing: 0.6px;
            }
        """)
        body_lay.addWidget(self.jobs_table, 1)
        layout.addWidget(body, 1)

    def refresh_data(self):
        # 1. Update KPI stats
        metrics = JobService.get_dashboard_metrics()
        self.card_customers.set_value(metrics["total_customers"])
        self.card_jobs.set_value(metrics["total_jobs"])
        self.card_pending.set_value(metrics["pending_diagnosis"])
        self.card_progress.set_value(metrics["in_progress"])
        self.card_ready.set_value(metrics["ready_for_delivery"])
        self.card_delivered.set_value(metrics["delivered"])

        # 2. Update Recent Jobs Table
        recent_jobs = JobService.get_recent(limit=8)
        self.jobs_table.setRowCount(len(recent_jobs))

        for row, job in enumerate(recent_jobs):
            # Job #
            item_job = QTableWidgetItem(job.job_number)
            item_job.setTextAlignment(Qt.AlignCenter)
            item_job.setForeground(QColor("#1e40af"))
            font_bold = item_job.font()
            font_bold.setBold(True)
            item_job.setFont(font_bold)
            self.jobs_table.setItem(row, 0, item_job)

            # Customer
            cust_text = f"{job.customer.name}\n{job.customer.phone}"
            item_cust = QTableWidgetItem(cust_text)
            self.jobs_table.setItem(row, 1, item_cust)

            # Device
            dev_text = f"{job.device.brand} {job.device.model}"
            item_dev = QTableWidgetItem(dev_text)
            self.jobs_table.setItem(row, 2, item_dev)

            # Complaint
            item_comp = QTableWidgetItem(job.complaint)
            self.jobs_table.setItem(row, 3, item_comp)

            # Lock / Passcode
            pass_text = f"🔑 {job.passcode_lock}" if job.passcode_lock else "-"
            item_pass = QTableWidgetItem(pass_text)
            item_pass.setTextAlignment(Qt.AlignCenter)
            self.jobs_table.setItem(row, 4, item_pass)

            # Status Pill Widget
            badge = StatusBadge(job.status)
            self.jobs_table.setCellWidget(row, 5, badge)

            # Balance Due
            bal_text = f"Rs. {job.balance_due:,.2f}"
            item_bal = QTableWidgetItem(bal_text)
            item_bal.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_bal.setFont(font_bold)
            if job.balance_due > 0:
                item_bal.setForeground(QColor("#d97706"))
            else:
                item_bal.setForeground(QColor("#16a34a"))
            self.jobs_table.setItem(row, 6, item_bal)

            # Actions Widget
            actions_widget = QWidget()
            actions_widget.setStyleSheet("QWidget { background: transparent; }")
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(6, 4, 6, 4)
            act_layout.setSpacing(5)

            # Print Dual Slip Button
            btn_print = QPushButton("  Slips")
            btn_print.setIcon(get_icon("print", "#1d4ed8", 14))
            btn_print.setProperty("class", "btn-tbl-print")
            btn_print.setFixedHeight(30)
            btn_print.setToolTip("Print 3-inch Thermal Slips")
            btn_print.clicked.connect(lambda _, j=job: self._handle_print_job(j))
            act_layout.addWidget(btn_print)

            # Diagnose / Tech Checklist
            btn_diag = QPushButton("  Tech")
            btn_diag.setIcon(get_icon("wrench", "#6d28d9", 14))
            btn_diag.setProperty("class", "btn-tbl-diag")
            btn_diag.setFixedHeight(30)
            btn_diag.setToolTip("Technician Diagnosis & Checklist")
            btn_diag.clicked.connect(lambda _, j=job: self._handle_diagnose_job(j))
            act_layout.addWidget(btn_diag)

            # Edit Job
            btn_edit = QPushButton("  Edit")
            btn_edit.setIcon(get_icon("edit", "#15803d", 14))
            btn_edit.setProperty("class", "btn-tbl-edit")
            btn_edit.setFixedHeight(30)
            btn_edit.setToolTip("Edit Job Details")
            btn_edit.clicked.connect(lambda _, j=job: self._handle_edit_job(j))
            act_layout.addWidget(btn_edit)

            self.jobs_table.setCellWidget(row, 7, actions_widget)

    def _handle_new_job(self):
        dialog = JobDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
            if dialog.should_print and dialog.saved_job:
                preview = ThermalPrintPreviewDialog(dialog.saved_job, parent=self)
                preview.exec()

    def _handle_print_job(self, job: RepairJob):
        full_job = JobService.get_by_id(job.id)
        if full_job:
            preview = ThermalPrintPreviewDialog(full_job, parent=self)
            preview.exec()

    def _handle_diagnose_job(self, job: RepairJob):
        full_job = JobService.get_by_id(job.id)
        if full_job:
            dialog = DiagnosisDialog(full_job, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_data()

    def _handle_edit_job(self, job: RepairJob):
        full_job = JobService.get_by_id(job.id)
        if full_job:
            dialog = JobDialog(job=full_job, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_data()
