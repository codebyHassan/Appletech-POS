from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QTabWidget,
    QAbstractItemView, QMessageBox, QDialog, QMenu,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QCursor, QColor, QFont, QIcon

from app.database.models import Customer, Device, RepairJob
from app.services.customer_service import CustomerService
from app.services.device_service import DeviceService
from app.services.job_service import JobService
from app.ui.icons import get_icon
from app.ui.components.search_bar import SearchBar
from app.ui.components.status_badge import StatusBadge
from app.ui.components.print_preview_dialog import ThermalPrintPreviewDialog
from app.ui.dialogs.customer_dialog import CustomerDialog
from app.ui.dialogs.device_dialog import DeviceDialog
from app.ui.dialogs.job_dialog import JobDialog


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 1px;")
    return lbl


def _stat_card(value: str, label: str, color: str) -> QFrame:
    card = QFrame()
    card.setFixedWidth(110)
    card.setStyleSheet(f"""
        QFrame {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-left: 3px solid {color};
            border-radius: 8px;
        }}
    """)
    lay = QVBoxLayout(card)
    lay.setSpacing(2)
    lay.setContentsMargins(10, 10, 10, 10)
    v_lbl = QLabel(value)
    v_lbl.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {color};")
    v_lbl.setObjectName("statVal")
    t_lbl = QLabel(label)
    t_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748b;")
    lay.addWidget(v_lbl)
    lay.addWidget(t_lbl)
    return card


def _table_css() -> str:
    return """
        QTableWidget {
            background: #ffffff;
            border: none;
            font-size: 12.5px;
        }
        QTableWidget::item {
            padding: 8px 10px;
            border-bottom: 1px solid #f1f5f9;
        }
        QTableWidget::item:selected {
            background-color: #eff6ff;
            color: #1e40af;
        }
        QHeaderView::section {
            background-color: #f8fafc;
            color: #64748b;
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 8px 10px;
            border: none;
            border-bottom: 2px solid #e2e8f0;
        }
        QTableWidget::item:alternate {
            background-color: #fafafa;
        }
    """


class CustomersView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_customer_id: Optional[int] = None
        self._init_ui()
        self.load_customers()

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #e2e8f0; }")

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([400, 760])

        root.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("customerLeftPanel")
        panel.setStyleSheet("QWidget#customerLeftPanel { background: #f8fafc; border-right: 1px solid #e2e8f0; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("Customers")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #0f172a;")
        hdr.addWidget(title)
        hdr.addStretch()
        self.lbl_count = QLabel("0 customers")
        self.lbl_count.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600;")
        hdr.addWidget(self.lbl_count)
        lay.addLayout(hdr)

        self.search_bar = SearchBar("Search name, phone, email...")
        self.search_bar.search_changed.connect(self._on_search_changed)
        lay.addWidget(self.search_bar)

        self.btn_new_customer = QPushButton("  Add New Customer")
        self.btn_new_customer.setIcon(get_icon("plus", "#ffffff", 16))
        self.btn_new_customer.setFixedHeight(38)
        self.btn_new_customer.setCursor(Qt.PointingHandCursor)
        self.btn_new_customer.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #1d4ed8;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 700;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
                border-color: #1e40af;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        self.btn_new_customer.clicked.connect(self._handle_new_customer)
        lay.addWidget(self.btn_new_customer)

        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(4)
        self.customer_table.setHorizontalHeaderLabels(["Name", "Phone", "Devs", "Jobs"])
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.customer_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.customer_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.customer_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.customer_table.verticalHeader().setVisible(False)
        self.customer_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.customer_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.setShowGrid(False)
        self.customer_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #eff6ff;
                color: #1e40af;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        self.customer_table.setWordWrap(False)
        self.customer_table.itemSelectionChanged.connect(self._on_customer_selected)
        self.customer_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customer_table.customContextMenuRequested.connect(self._show_customer_context_menu)
        lay.addWidget(self.customer_table, 1)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("customerRightPanel")
        panel.setStyleSheet("QWidget#customerRightPanel { background: #f1f5f9; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        top_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        pg_title = QLabel("Customer Management")
        pg_title.setProperty("class", "page-title")
        pg_sub = QLabel("Select a customer to view their profile, devices, and repair history")
        pg_sub.setProperty("class", "page-subtitle")
        title_col.addWidget(pg_title)
        title_col.addWidget(pg_sub)
        top_row.addLayout(title_col)
        top_row.addStretch()

        self.btn_new_customer_top = QPushButton("  Add New Customer")
        self.btn_new_customer_top.setIcon(get_icon("plus", "#ffffff", 16))
        self.btn_new_customer_top.setFixedHeight(38)
        self.btn_new_customer_top.setCursor(Qt.PointingHandCursor)
        self.btn_new_customer_top.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #1d4ed8;
                border-radius: 8px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 700;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
                border-color: #1e40af;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        self.btn_new_customer_top.clicked.connect(self._handle_new_customer)
        top_row.addWidget(self.btn_new_customer_top)

        lay.addLayout(top_row)

        self.profile_card = self._build_profile_card()
        lay.addWidget(self.profile_card)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            QTabBar::tab {
                background: #f1f5f9;
                color: #475569;
                padding: 9px 22px;
                font-size: 12px;
                font-weight: 600;
                border: none;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: #2563eb;
                color: #ffffff;
                border-radius: 6px 6px 0 0;
            }
            QTabBar::tab:hover:!selected {
                background: #e2e8f0;
                color: #1e40af;
            }
        """)
        self.tabs.addTab(self._build_devices_tab(), "  Devices")
        self.tabs.addTab(self._build_history_tab(), "  Repair History")
        self.tabs.setTabIcon(0, get_icon("phone", "#2563eb", 14))
        self.tabs.setTabIcon(1, get_icon("clipboard", "#2563eb", 14))
        lay.addWidget(self.tabs, 1)

        return panel

    def _build_profile_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("profileCard")
        card.setStyleSheet("""
            QFrame#profileCard {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        self.avatar_lbl = QLabel("?")
        self.avatar_lbl.setFixedSize(52, 52)
        self.avatar_lbl.setAlignment(Qt.AlignCenter)
        self.avatar_lbl.setStyleSheet("""
            QLabel {
                background-color: #2563eb;
                color: #ffffff;
                border-radius: 26px;
                font-size: 22px;
                font-weight: 900;
            }
        """)
        top_row.addWidget(self.avatar_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        self.lbl_cust_name = QLabel("Select a Customer")
        self.lbl_cust_name.setStyleSheet("font-size: 17px; font-weight: 800; color: #0f172a;")
        self.lbl_cust_role = QLabel("No customer selected")
        self.lbl_cust_role.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        name_col.addWidget(self.lbl_cust_name)
        name_col.addWidget(self.lbl_cust_role)
        top_row.addLayout(name_col)
        top_row.addStretch()

        self.btn_edit_cust = QPushButton("  Edit Profile")
        self.btn_edit_cust.setIcon(get_icon("edit", "#15803d", 14))
        self.btn_edit_cust.setEnabled(False)
        self.btn_edit_cust.setFixedHeight(34)
        self.btn_edit_cust.setStyleSheet("""
            QPushButton {
                background: #f0fdf4; color: #15803d;
                border: 1px solid #86efac;
                border-radius: 7px; padding: 0 14px;
                font-weight: 700; font-size: 12px;
            }
            QPushButton:hover { background: #dcfce7; }
            QPushButton:disabled { background: #f1f5f9; color: #94a3b8; border-color: #e2e8f0; }
        """)
        self.btn_edit_cust.clicked.connect(self._handle_edit_customer)
        top_row.addWidget(self.btn_edit_cust)

        self.btn_new_job_for_cust = QPushButton("  Receive Job")
        self.btn_new_job_for_cust.setIcon(get_icon("plus", "#ffffff", 14))
        self.btn_new_job_for_cust.setEnabled(False)
        self.btn_new_job_for_cust.setFixedHeight(34)
        self.btn_new_job_for_cust.setStyleSheet("""
            QPushButton {
                background: #2563eb; color: #ffffff;
                border: none; border-radius: 7px; padding: 0 16px;
                font-weight: 700; font-size: 12px;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #bfdbfe; }
        """)
        self.btn_new_job_for_cust.clicked.connect(self._handle_new_job_for_customer)
        top_row.addWidget(self.btn_new_job_for_cust)

        lay.addLayout(top_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;")
        lay.addWidget(divider)

        info_row = QHBoxLayout()
        info_row.setSpacing(24)

        contact_grid = QVBoxLayout()
        contact_grid.setSpacing(7)
        self._contact_phone = self._make_contact_row("Phone", "phone", "")
        self._contact_email = self._make_contact_row("Email", "mail", "")
        self._contact_address = self._make_contact_row("Address", "map", "")
        contact_grid.addLayout(self._contact_phone["lay"])
        contact_grid.addLayout(self._contact_email["lay"])
        contact_grid.addLayout(self._contact_address["lay"])
        info_row.addLayout(contact_grid, 1)

        stats_col = QVBoxLayout()
        stats_col.setSpacing(6)
        stats_col.addWidget(_section_label("Stats"))
        stat_row = QHBoxLayout()
        stat_row.setSpacing(8)
        self.stat_devices = _stat_card("0", "Devices", "#0284c7")
        self.stat_jobs = _stat_card("0", "Jobs", "#7c3aed")
        self.stat_balance = _stat_card("Rs.0", "Balance Due", "#d97706")
        stat_row.addWidget(self.stat_devices)
        stat_row.addWidget(self.stat_jobs)
        stat_row.addWidget(self.stat_balance)
        stat_row.addStretch()
        stats_col.addLayout(stat_row)
        info_row.addLayout(stats_col)

        lay.addLayout(info_row)
        return card

    def _make_contact_row(self, label: str, icon_name: str, value: str) -> dict:
        lay = QHBoxLayout()
        lay.setSpacing(8)
        key_lbl = QLabel(f"{label}:")
        key_lbl.setFixedWidth(60)
        key_lbl.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #64748b;")
        val_lbl = QLabel(value or "—")
        val_lbl.setStyleSheet("font-size: 12px; color: #0f172a;")
        lay.addWidget(key_lbl)
        lay.addWidget(val_lbl, 1)
        return {"lay": lay, "val": val_lbl}

    def _build_devices_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("QWidget { background: #ffffff; }")
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        lbl = QLabel("Registered Devices")
        lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #1e293b;")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self.btn_add_device = QPushButton("  Add Device")
        self.btn_add_device.setIcon(get_icon("plus", "#1e40af", 14))
        self.btn_add_device.setEnabled(False)
        self.btn_add_device.setFixedHeight(32)
        self.btn_add_device.setStyleSheet("""
            QPushButton {
                background: #eff6ff; color: #1e40af;
                border: 1px solid #bfdbfe; border-radius: 7px; padding: 0 14px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #dbeafe; }
            QPushButton:disabled { background: #f8fafc; color: #94a3b8; border-color: #e2e8f0; }
        """)
        self.btn_add_device.clicked.connect(self._handle_add_device)
        hdr.addWidget(self.btn_add_device)
        lay.addLayout(hdr)

        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(5)
        self.devices_table.setHorizontalHeaderLabels(["Brand", "Model", "IMEI / Serial", "Color", "Actions"])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.devices_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.devices_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.devices_table.verticalHeader().setVisible(False)
        self.devices_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.devices_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.devices_table.setShowGrid(False)
        self.devices_table.setAlternatingRowColors(True)
        self.devices_table.setStyleSheet(_table_css())
        lay.addWidget(self.devices_table, 1)
        return tab

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("QWidget { background: #ffffff; }")
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        lbl = QLabel("Repair History")
        lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #1e293b;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self.lbl_history_count = QLabel("0 jobs")
        self.lbl_history_count.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600;")
        hdr.addWidget(self.lbl_history_count)
        lay.addLayout(hdr)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["Job #", "Date", "Device", "Complaint", "Status", "Slip"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setShowGrid(False)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet(_table_css())
        lay.addWidget(self.history_table, 1)
        return tab

    # ── DATA LOADING ─────────────────────────────────────────────────────────

    def _on_search_changed(self, text: str):
        self.load_customers(search_query=text)

    def load_customers(self, search_query: str = ""):
        customers = CustomerService.get_all(search_query=search_query)
        self.customer_table.setRowCount(len(customers))
        self.lbl_count.setText(f"{len(customers)} customer{'s' if len(customers) != 1 else ''}")

        bold_font = QFont()
        bold_font.setBold(True)

        for row, cust in enumerate(customers):
            item_name = QTableWidgetItem(cust.name)
            item_name.setData(Qt.ItemDataRole.UserRole, cust.id)
            item_name.setFont(bold_font)
            item_name.setForeground(QColor("#0f172a"))
            self.customer_table.setItem(row, 0, item_name)

            item_phone = QTableWidgetItem(cust.phone)
            item_phone.setForeground(QColor("#475569"))
            self.customer_table.setItem(row, 1, item_phone)

            dev_count = len(cust.devices)
            item_devs = QTableWidgetItem(str(dev_count))
            item_devs.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if dev_count > 0:
                item_devs.setForeground(QColor("#0284c7"))
                item_devs.setFont(bold_font)
            else:
                item_devs.setForeground(QColor("#94a3b8"))
            self.customer_table.setItem(row, 2, item_devs)

            job_count = len(cust.jobs)
            item_jobs = QTableWidgetItem(str(job_count))
            item_jobs.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if job_count > 0:
                item_jobs.setForeground(QColor("#7c3aed"))
                item_jobs.setFont(bold_font)
            else:
                item_jobs.setForeground(QColor("#94a3b8"))
            self.customer_table.setItem(row, 3, item_jobs)

            self.customer_table.setRowHeight(row, 42)

        if customers:
            if not self.selected_customer_id or not any(c.id == self.selected_customer_id for c in customers):
                self.customer_table.selectRow(0)
        else:
            self._clear_customer_details()

    def _clear_customer_details(self):
        self.selected_customer_id = None
        self.avatar_lbl.setText("?")
        self.lbl_cust_name.setText("Select a Customer")
        self.lbl_cust_role.setText("No customer selected")
        self._contact_phone["val"].setText("—")
        self._contact_email["val"].setText("—")
        self._contact_address["val"].setText("—")
        self._set_stat_val(self.stat_devices, "0")
        self._set_stat_val(self.stat_jobs, "0")
        self._set_stat_val(self.stat_balance, "Rs.0")
        self.btn_edit_cust.setEnabled(False)
        self.btn_new_job_for_cust.setEnabled(False)
        self.btn_add_device.setEnabled(False)
        self.devices_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.lbl_history_count.setText("0 jobs")

    def _on_customer_selected(self):
        selected = self.customer_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        cust_id = self.customer_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if cust_id:
            self.selected_customer_id = cust_id
            self._load_customer_details(cust_id)

    def _load_customer_details(self, customer_id: int):
        cust = CustomerService.get_by_id(customer_id)
        if not cust:
            return

        initials = "".join(w[0].upper() for w in cust.name.split()[:2]) if cust.name else "?"
        self.avatar_lbl.setText(initials)
        self.lbl_cust_name.setText(cust.name)
        joined = cust.created_at.strftime('%b %Y') if hasattr(cust, 'created_at') and cust.created_at else 'N/A'
        self.lbl_cust_role.setText(f"Customer ID #{cust.id}  |  Joined {joined}")

        self._contact_phone["val"].setText(cust.phone or "—")
        self._contact_email["val"].setText(cust.email or "—")
        self._contact_address["val"].setText(cust.address or "—")

        dev_count = len(cust.devices)
        job_count = len(cust.jobs)
        balance_due = sum(getattr(j, 'balance_due', 0) for j in cust.jobs)

        self._set_stat_val(self.stat_devices, str(dev_count))
        self._set_stat_val(self.stat_jobs, str(job_count))
        self._set_stat_val(self.stat_balance, f"Rs.{balance_due:,.0f}")

        self.btn_edit_cust.setEnabled(True)
        self.btn_new_job_for_cust.setEnabled(True)
        self.btn_add_device.setEnabled(True)

        self._load_devices_table(cust)
        self._load_history_table(customer_id)

    def _set_stat_val(self, card: QFrame, value: str):
        lbl = card.findChild(QLabel, "statVal")
        if lbl:
            lbl.setText(value)

    def _load_devices_table(self, cust: Customer):
        self.devices_table.setRowCount(len(cust.devices))
        bold_font = QFont()
        bold_font.setBold(True)

        for row, dev in enumerate(cust.devices):
            brand_item = QTableWidgetItem(dev.brand)
            brand_item.setForeground(QColor("#1e40af"))
            brand_item.setFont(bold_font)
            self.devices_table.setItem(row, 0, brand_item)

            self.devices_table.setItem(row, 1, QTableWidgetItem(dev.model))

            imei_item = QTableWidgetItem(dev.imei_serial or "—")
            imei_item.setForeground(QColor("#64748b"))
            imei_item.setTextAlignment(Qt.AlignCenter)
            self.devices_table.setItem(row, 2, imei_item)

            color_item = QTableWidgetItem(dev.color or "—")
            color_item.setTextAlignment(Qt.AlignCenter)
            self.devices_table.setItem(row, 3, color_item)

            act_w = QWidget()
            act_w.setStyleSheet("QWidget { background: transparent; }")
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(6, 4, 6, 4)
            act_l.setSpacing(5)

            btn_edit = QPushButton("  Edit")
            btn_edit.setIcon(get_icon("edit", "#15803d", 14))
            btn_edit.setProperty("class", "btn-tbl-edit")
            btn_edit.setFixedHeight(30)
            btn_edit.setToolTip("Edit Device")
            btn_edit.clicked.connect(lambda _, d=dev: self._handle_edit_device(d))
            act_l.addWidget(btn_edit)

            btn_job = QPushButton("  Job")
            btn_job.setIcon(get_icon("plus", "#1d4ed8", 14))
            btn_job.setProperty("class", "btn-tbl-print")
            btn_job.setFixedHeight(30)
            btn_job.setToolTip("New Repair Job for this Device")
            btn_job.clicked.connect(lambda _, d=dev: self._handle_new_job_for_device(d))
            act_l.addWidget(btn_job)

            act_l.addStretch()
            self.devices_table.setCellWidget(row, 4, act_w)
            self.devices_table.setRowHeight(row, 44)

    def _load_history_table(self, customer_id: int):
        history = CustomerService.get_customer_history(customer_id)
        self.history_table.setRowCount(len(history))
        self.lbl_history_count.setText(f"{len(history)} job{'s' if len(history) != 1 else ''}")

        bold_font = QFont()
        bold_font.setBold(True)

        for row, job in enumerate(history):
            job_item = QTableWidgetItem(job.job_number)
            job_item.setForeground(QColor("#1e40af"))
            job_item.setFont(bold_font)
            job_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, 0, job_item)

            date_str = job.received_at.strftime("%d-%b-%Y") if job.received_at else "—"
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignCenter)
            date_item.setForeground(QColor("#64748b"))
            self.history_table.setItem(row, 1, date_item)

            dev_str = f"{job.device.brand} {job.device.model}"
            dev_item = QTableWidgetItem(dev_str)
            dev_item.setForeground(QColor("#0f172a"))
            self.history_table.setItem(row, 2, dev_item)

            comp_item = QTableWidgetItem(job.complaint)
            comp_item.setForeground(QColor("#475569"))
            self.history_table.setItem(row, 3, comp_item)

            badge = StatusBadge(job.status)
            self.history_table.setCellWidget(row, 4, badge)

            slip_w = QWidget()
            slip_w.setStyleSheet("QWidget { background: transparent; }")
            slip_l = QHBoxLayout(slip_w)
            slip_l.setContentsMargins(6, 4, 6, 4)
            slip_l.setSpacing(5)
            btn_slip = QPushButton("  Slips")
            btn_slip.setIcon(get_icon("print", "#1d4ed8", 14))
            btn_slip.setProperty("class", "btn-tbl-print")
            btn_slip.setFixedHeight(30)
            btn_slip.setToolTip("Print 3-inch Thermal Slips")
            btn_slip.clicked.connect(lambda _, j=job: self._print_slip(j))
            slip_l.addWidget(btn_slip)
            slip_l.addStretch()
            self.history_table.setCellWidget(row, 5, slip_w)
            self.history_table.setRowHeight(row, 44)

    def refresh_data(self):
        self.load_customers()
        if self.selected_customer_id:
            self._load_customer_details(self.selected_customer_id)

    # ── ACTIONS ──────────────────────────────────────────────────────────────

    def _handle_new_customer(self):
        dialog = CustomerDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_customer:
            self.load_customers()
            self.selected_customer_id = dialog.saved_customer.id
            self._load_customer_details(dialog.saved_customer.id)

    def _handle_edit_customer(self):
        if not self.selected_customer_id:
            return
        cust = CustomerService.get_by_id(self.selected_customer_id)
        if cust:
            dialog = CustomerDialog(customer=cust, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_customers()
                self._load_customer_details(cust.id)

    def _handle_add_device(self):
        if not self.selected_customer_id:
            return
        dialog = DeviceDialog(preselected_customer_id=self.selected_customer_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_customer_details(self.selected_customer_id)
            self.load_customers()

    def _handle_edit_device(self, device: Device):
        fresh_dev = DeviceService.get_by_id(device.id)
        if fresh_dev:
            dialog = DeviceDialog(device=fresh_dev, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._load_customer_details(fresh_dev.customer_id)

    def _handle_new_job_for_customer(self):
        if not self.selected_customer_id:
            return
        dialog = JobDialog(preselected_customer_id=self.selected_customer_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_customer_details(self.selected_customer_id)
            if dialog.should_print and dialog.saved_job:
                self._print_slip(dialog.saved_job)

    def _handle_new_job_for_device(self, device: Device):
        dialog = JobDialog(
            preselected_customer_id=device.customer_id,
            preselected_device_id=device.id,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_customer_details(device.customer_id)
            if dialog.should_print and dialog.saved_job:
                self._print_slip(dialog.saved_job)

    def _print_slip(self, job: RepairJob):
        fresh_job = JobService.get_by_id(job.id)
        if fresh_job:
            dialog = ThermalPrintPreviewDialog(fresh_job, parent=self)
            dialog.exec()

    def _show_customer_context_menu(self, pos):
        item = self.customer_table.itemAt(pos)
        if not item:
            return
        row = item.row()
        cust_id = self.customer_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        cust = CustomerService.get_by_id(cust_id)
        if not cust:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #eff6ff; color: #1e40af; }
            QMenu::separator { height: 1px; background: #e2e8f0; margin: 4px 8px; }
        """)

        act_job = QAction(get_icon("plus", "#2563eb", 14), "  Receive Repair Job", self)
        act_job.triggered.connect(self._handle_new_job_for_customer)
        menu.addAction(act_job)

        act_dev = QAction(get_icon("phone", "#0284c7", 14), "  Add New Device", self)
        act_dev.triggered.connect(self._handle_add_device)
        menu.addAction(act_dev)

        menu.addSeparator()

        act_edit = QAction(get_icon("edit", "#15803d", 14), "  Edit Customer", self)
        act_edit.triggered.connect(self._handle_edit_customer)
        menu.addAction(act_edit)

        act_del = QAction(get_icon("trash", "#dc2626", 14), "  Delete Customer", self)
        act_del.triggered.connect(lambda: self._delete_customer(cust))
        menu.addAction(act_del)

        menu.exec(QCursor.pos())

    def _delete_customer(self, customer: Customer):
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete customer '{customer.name}'?\n\n"
            f"This will also delete {len(customer.devices)} device(s) and {len(customer.jobs)} repair job(s).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            CustomerService.delete(customer.id)
            self.selected_customer_id = None
            self.load_customers()
            self.avatar_lbl.setText("?")
            self.lbl_cust_name.setText("Select a Customer")
            self.lbl_cust_role.setText("No customer selected")
            self._contact_phone["val"].setText("—")
            self._contact_email["val"].setText("—")
            self._contact_address["val"].setText("—")
            self._set_stat_val(self.stat_devices, "0")
            self._set_stat_val(self.stat_jobs, "0")
            self._set_stat_val(self.stat_balance, "Rs.0")
            self.devices_table.setRowCount(0)
            self.history_table.setRowCount(0)
            self.btn_edit_cust.setEnabled(False)
            self.btn_new_job_for_cust.setEnabled(False)
            self.btn_add_device.setEnabled(False)
