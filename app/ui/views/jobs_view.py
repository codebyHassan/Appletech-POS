"""
Jobs View — Premium High-Density Enterprise ERP Grid.
Matches: dark sidebar nav, search+filter bar card, compact data grid with color-coded cells.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QAbstractItemView, QMenu,
    QMessageBox, QDialog, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCursor, QColor, QFont

from app.database.models import RepairJob, JobStatus
from app.services.job_service import JobService
from app.services.auth_service import AuthService
from app.ui.icons import get_icon
from app.ui.components.search_bar import SearchBar
from app.ui.components.status_badge import StatusBadge
from app.ui.components.print_preview_dialog import ThermalPrintPreviewDialog
from app.ui.dialogs.job_dialog import JobDialog
from app.ui.dialogs.diagnosis_dialog import DiagnosisDialog


class JobsView(QWidget):
    """Repair Jobs Management — high-density ERP grid with filters, RBAC, dual-print."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_status_filter = "All"
        self.current_tech_filter: Optional[int] = None
        self.search_query = ""
        self._init_ui()
        self.load_jobs()

    # ─── UI BUILD ────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── TOP HEADER BAR ────────────────────────────────────────────────
        header_bar = QFrame()
        header_bar.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        header_bar.setFixedHeight(72)
        hb_lay = QHBoxLayout(header_bar)
        hb_lay.setContentsMargins(24, 0, 20, 0)
        hb_lay.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        pg_title = QLabel("Repair Jobs & Workshop Queue")
        pg_title.setStyleSheet(
            "font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px;"
        )
        pg_sub = QLabel("Track intake, technician assignments, repair progress, and 3-inch slip printing")
        pg_sub.setStyleSheet("font-size: 12px; color: #64748b;")
        title_col.addWidget(pg_title)
        title_col.addWidget(pg_sub)

        hb_lay.addLayout(title_col)
        hb_lay.addStretch()

        self.btn_new_job = QPushButton("  Receive New Job  (Ctrl+N)")
        self.btn_new_job.setIcon(get_icon("plus", "#ffffff", 16))
        self.btn_new_job.setFixedHeight(40)
        self.btn_new_job.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:pressed { background: #1e40af; }
        """)
        self.btn_new_job.clicked.connect(self._handle_new_job)
        hb_lay.addWidget(self.btn_new_job)

        root.addWidget(header_bar)

        # ── FILTER / SEARCH BAR ───────────────────────────────────────────
        filter_strip = QFrame()
        filter_strip.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        filter_strip.setFixedHeight(58)
        fs_lay = QHBoxLayout(filter_strip)
        fs_lay.setContentsMargins(20, 0, 20, 0)
        fs_lay.setSpacing(10)

        self.search_bar = SearchBar("Search Job #, Customer, Phone, IMEI, Brand, Model, Passcode...")
        self.search_bar.setFixedHeight(36)
        self.search_bar.search_changed.connect(self._on_search_changed)
        fs_lay.addWidget(self.search_bar, 3)

        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(36)
        self.status_combo.setFixedWidth(148)
        self.status_combo.addItem("All Statuses", "All")
        for status in JobStatus.ALL_STATUSES:
            self.status_combo.addItem(status, status)
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        fs_lay.addWidget(self.status_combo)

        self.tech_combo = QComboBox()
        self.tech_combo.setFixedHeight(36)
        self.tech_combo.setFixedWidth(160)
        self.tech_combo.addItem("All Technicians", None)
        for t in AuthService.list_technicians():
            self.tech_combo.addItem(t.full_name, t.id)
        self.tech_combo.currentIndexChanged.connect(self._on_tech_filter_changed)
        fs_lay.addWidget(self.tech_combo)

        self.btn_refresh = QPushButton("  Refresh")
        self.btn_refresh.setIcon(get_icon("refresh", "#334155", 15))
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 7px;
                padding: 0 14px;
                font-size: 12.5px;
                font-weight: 600;
            }
            QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; }
        """)
        self.btn_refresh.clicked.connect(self.load_jobs)
        fs_lay.addWidget(self.btn_refresh)

        root.addWidget(filter_strip)

        # ── DATA TABLE ────────────────────────────────────────────────────
        table_container = QWidget()
        table_container.setStyleSheet("QWidget { background: #f8fafc; }")
        tc_lay = QVBoxLayout(table_container)
        tc_lay.setContentsMargins(20, 14, 20, 0)
        tc_lay.setSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "JOB #", "DATE", "CUSTOMER", "DEVICE & MODEL",
            "PASSCODE", "ASSIGNED TECH", "COMPLAINT",
            "BALANCE DUE", "STATUS", "ACTIONS"
        ])

        # Column resize modes
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.Stretch)
        hh.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        hh.setHighlightSections(False)

        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_row_double_click)
        self.table.setStyleSheet("""
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
            QHeaderView::section:first {
                border-top-left-radius: 10px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 10px;
            }
        """)

        tc_lay.addWidget(self.table, 1)

        # ── BOTTOM STATUS BAR
        status_bar = QHBoxLayout()
        self.count_label = QLabel("Showing 0 jobs")
        self.count_label.setStyleSheet(
            "color: #64748b; font-size: 12px; font-weight: 600; padding: 8px 0;"
        )
        status_bar.addWidget(self.count_label)
        status_bar.addStretch()
        hint = QLabel("Double-click row to edit  ·  Right-click for options")
        hint.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 8px 0;")
        status_bar.addWidget(hint)
        tc_lay.addLayout(status_bar)

        root.addWidget(table_container, 1)

    # ─── FILTERS ─────────────────────────────────────────────────────────────

    def _on_search_changed(self, text: str):
        self.search_query = text
        self.load_jobs()

    def _on_filter_changed(self):
        self.current_status_filter = self.status_combo.currentData()
        self.load_jobs()

    def _on_tech_filter_changed(self):
        self.current_tech_filter = self.tech_combo.currentData()
        self.load_jobs()

    # ─── DATA LOADING ─────────────────────────────────────────────────────────

    def load_jobs(self):
        try:
            jobs = JobService.get_all(
                status_filter=self.current_status_filter,
                search_query=self.search_query,
                technician_id=self.current_tech_filter
            )
            self.table.setRowCount(len(jobs))
            self.count_label.setText(f"Showing {len(jobs)} repair job(s)")

            bold_font = QFont()
            bold_font.setBold(True)

            mono_font = QFont("Consolas", 11)

            for row, job in enumerate(jobs):
                self.table.setRowHeight(row, 46)

                # ── Job # (blue bold monospace)
                item_job = QTableWidgetItem(job.job_number)
                item_job.setData(Qt.UserRole, job.id)
                item_job.setTextAlignment(Qt.AlignCenter)
                item_job.setForeground(QColor("#1e40af"))
                item_job.setFont(bold_font)
                self.table.setItem(row, 0, item_job)

                # ── Date
                date_str = job.received_at.strftime("%d-%b-%Y") if job.received_at else "-"
                item_date = QTableWidgetItem(date_str)
                item_date.setTextAlignment(Qt.AlignCenter)
                item_date.setForeground(QColor("#475569"))
                self.table.setItem(row, 1, item_date)

                # ── Customer (name + phone stacked)
                cust_text = f"{job.customer.name}\n{job.customer.phone}"
                item_cust = QTableWidgetItem(cust_text)
                item_cust.setForeground(QColor("#0f172a"))
                self.table.setItem(row, 2, item_cust)
                self.table.setRowHeight(row, 52)

                # ── Device & Model (brand highlighted)
                dev_str = f"{job.device.brand} {job.device.model}"
                item_dev = QTableWidgetItem(dev_str)
                item_dev.setForeground(QColor("#0f172a"))
                self.table.setItem(row, 3, item_dev)

                # ── Passcode (key icon prefix, amber)
                if job.passcode_lock:
                    pass_str = f"  {job.passcode_lock}"
                    item_pass = QTableWidgetItem(pass_str)
                    item_pass.setIcon(get_icon("key", "#d97706", 13))
                    item_pass.setForeground(QColor("#d97706"))
                    item_pass.setFont(mono_font)
                else:
                    item_pass = QTableWidgetItem("—")
                    item_pass.setForeground(QColor("#94a3b8"))
                item_pass.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, item_pass)

                # ── Assigned Tech
                tech_name = job.technician.full_name if job.technician else "Unassigned"
                item_tech = QTableWidgetItem(tech_name)
                item_tech.setTextAlignment(Qt.AlignCenter)
                if not job.technician:
                    item_tech.setForeground(QColor("#94a3b8"))
                else:
                    item_tech.setForeground(QColor("#0284c7"))
                    item_tech.setFont(bold_font)
                self.table.setItem(row, 5, item_tech)

                # ── Complaint
                item_comp = QTableWidgetItem(job.complaint)
                item_comp.setForeground(QColor("#475569"))
                self.table.setItem(row, 6, item_comp)

                # ── Balance Due (colored bold)
                bal_text = f"Rs. {job.balance_due:,.2f}"
                item_bal = QTableWidgetItem(bal_text)
                item_bal.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item_bal.setFont(bold_font)
                item_bal.setForeground(
                    QColor("#d97706") if job.balance_due > 0 else QColor("#16a34a")
                )
                self.table.setItem(row, 7, item_bal)

                # ── Status Badge (pill widget)
                badge = StatusBadge(job.status)
                self.table.setCellWidget(row, 8, badge)

                # ── Action Buttons
                act_w = QWidget()
                act_w.setStyleSheet("QWidget { background: transparent; }")
                act_l = QHBoxLayout(act_w)
                act_l.setContentsMargins(6, 4, 6, 4)
                act_l.setSpacing(5)

                btn_print = QPushButton("  Slips")
                btn_print.setIcon(get_icon("print", "#1d4ed8", 14))
                btn_print.setProperty("class", "btn-tbl-print")
                btn_print.setFixedHeight(30)
                btn_print.setToolTip("Print 3-inch Thermal Slips")
                btn_print.clicked.connect(lambda _, j=job: self._open_print_preview(j, tab=0))
                act_l.addWidget(btn_print)

                btn_diag = QPushButton("  Tech")
                btn_diag.setIcon(get_icon("wrench", "#6d28d9", 14))
                btn_diag.setProperty("class", "btn-tbl-diag")
                btn_diag.setFixedHeight(30)
                btn_diag.setToolTip("Technician Diagnosis & Checklist")
                btn_diag.clicked.connect(lambda _, j=job: self._open_diagnosis_dialog(j))
                act_l.addWidget(btn_diag)

                btn_edit = QPushButton("  Edit")
                btn_edit.setIcon(get_icon("edit", "#15803d", 14))
                btn_edit.setProperty("class", "btn-tbl-edit")
                btn_edit.setFixedHeight(30)
                btn_edit.setToolTip("Edit Job Details")
                btn_edit.clicked.connect(lambda _, j=job: self._edit_job(j))
                act_l.addWidget(btn_edit)

                self.table.setCellWidget(row, 9, act_w)

        except Exception as e:
            print(f"Error loading jobs: {e}")

    # ─── ACTION HANDLERS ─────────────────────────────────────────────────────

    def _handle_new_job(self):
        dialog = JobDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_jobs()
            if dialog.should_print and dialog.saved_job:
                self._open_print_preview(dialog.saved_job, tab=0)

    def _open_print_preview(self, job: RepairJob, tab: int = 0):
        fresh_job = JobService.get_by_id(job.id)
        if fresh_job:
            dialog = ThermalPrintPreviewDialog(fresh_job, parent=self, initial_tab=tab)
            dialog.exec()

    def _open_diagnosis_dialog(self, job: RepairJob):
        fresh_job = JobService.get_by_id(job.id)
        if fresh_job:
            dialog = DiagnosisDialog(fresh_job, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_jobs()

    def _edit_job(self, job: RepairJob):
        fresh_job = JobService.get_by_id(job.id)
        if fresh_job:
            dialog = JobDialog(job=fresh_job, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_jobs()

    def _on_row_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            job_id = item.data(Qt.UserRole)
            job = JobService.get_by_id(job_id)
            if job:
                self._edit_job(job)

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        job_id = id_item.data(Qt.UserRole)
        job = JobService.get_by_id(job_id)
        if not job:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 8px 20px; font-size: 12.5px; border-radius: 4px; }
            QMenu::item:selected { background: #eff6ff; color: #1e40af; }
            QMenu::separator { height: 1px; background: #e2e8f0; margin: 4px 8px; }
        """)

        act_print_dual = QAction(get_icon("print", "#1d4ed8", 14), "  Print 2-in-1 Dual Slip", self)
        act_print_dual.triggered.connect(lambda: self._open_print_preview(job, tab=0))
        menu.addAction(act_print_dual)

        act_print_cust = QAction(get_icon("print", "#0284c7", 14), "  Print Customer Slip Only", self)
        act_print_cust.triggered.connect(lambda: self._open_print_preview(job, tab=2))
        menu.addAction(act_print_cust)

        act_print_tech = QAction(get_icon("wrench", "#6d28d9", 14), "  Print Repairer To-Do Slip", self)
        act_print_tech.triggered.connect(lambda: self._open_print_preview(job, tab=3))
        menu.addAction(act_print_tech)

        menu.addSeparator()

        act_diag = QAction(get_icon("search", "#475569", 14), "  Record / Update Diagnosis", self)
        act_diag.triggered.connect(lambda: self._open_diagnosis_dialog(job))
        menu.addAction(act_diag)

        status_submenu = menu.addMenu("  Quick Change Status")
        status_submenu.setIcon(get_icon("refresh", "#475569", 14))
        for status in JobStatus.ALL_STATUSES:
            sub_act = QAction(status, self)
            sub_act.triggered.connect(lambda _, s=status: self._quick_update_status(job.id, s))
            status_submenu.addAction(sub_act)

        menu.addSeparator()

        act_edit = QAction(get_icon("edit", "#15803d", 14), "  Edit Repair Job", self)
        act_edit.triggered.connect(lambda: self._edit_job(job))
        menu.addAction(act_edit)

        if AuthService.can_delete_records():
            act_del = QAction(get_icon("trash", "#dc2626", 14), "  Delete Job", self)
            act_del.triggered.connect(lambda: self._delete_job(job))
            menu.addAction(act_del)

        menu.exec(QCursor.pos())

    def _quick_update_status(self, job_id: int, new_status: str):
        try:
            job = JobService.get_by_id(job_id)
            if job:
                JobService.update(job_id=job.id, complaint=job.complaint, status=new_status)
                self.load_jobs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update status:\n{e}")

    def _delete_job(self, job: RepairJob):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete repair job '{job.job_number}' for {job.customer.name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            JobService.delete(job.id)
            self.load_jobs()
