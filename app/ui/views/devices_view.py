from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
    QDialog, QFrame
)
from PySide6.QtCore import Qt

from app.database.models import Device
from app.services.device_service import DeviceService
from app.ui.icons import get_icon
from app.ui.components.search_bar import SearchBar
from app.ui.dialogs.device_dialog import DeviceDialog
from app.ui.dialogs.job_dialog import JobDialog
from app.ui.components.print_preview_dialog import ThermalPrintPreviewDialog


class DevicesView(QWidget):
    """
    Device Directory View allowing search by IMEI/Model/Customer
    and quick creation of repair jobs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_query = ""
        self._init_ui()
        self.load_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header Row
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        page_title = QLabel("Device Directory")
        page_title.setProperty("class", "page-title")
        page_subtitle = QLabel("Search devices by IMEI, serial number, brand, model, or owner")
        page_subtitle.setProperty("class", "page-subtitle")

        title_box.addWidget(page_title)
        title_box.addWidget(page_subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_new_device = QPushButton("  Register New Device")
        self.btn_new_device.setIcon(get_icon("plus", "#ffffff", 16))
        self.btn_new_device.setProperty("class", "btn-primary")
        self.btn_new_device.setFixedHeight(38)
        self.btn_new_device.clicked.connect(self._handle_new_device)
        header_layout.addWidget(self.btn_new_device)

        layout.addLayout(header_layout)

        # Search Bar
        search_card = QFrame()
        search_card.setProperty("class", "card")
        search_card.setStyleSheet("QFrame.card { padding: 6px 12px; background-color: #ffffff; }")
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(4, 4, 4, 4)

        self.search_bar = SearchBar("Search device by IMEI, Serial, Model, Brand, Customer Name...")
        self.search_bar.search_changed.connect(self._on_search_changed)
        search_layout.addWidget(self.search_bar)

        self.btn_refresh = QPushButton("  Refresh")
        self.btn_refresh.setIcon(get_icon("refresh", "#334155", 16))
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.clicked.connect(self.load_devices)
        search_layout.addWidget(self.btn_refresh)

        layout.addWidget(search_card)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Brand", "Model", "IMEI / Serial", "Color", "Owner / Customer", "Phone", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
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
        """)
        self.table.doubleClicked.connect(self._on_row_double_click)

        layout.addWidget(self.table, 1)

        # Count
        self.count_label = QLabel("Showing 0 devices")
        self.count_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.count_label)

    def _on_search_changed(self, text: str):
        self.search_query = text
        self.load_devices()

    def load_devices(self):
        devices = DeviceService.get_all(search_query=self.search_query)
        self.table.setRowCount(len(devices))
        self.count_label.setText(f"Showing {len(devices)} device(s)")

        for row, dev in enumerate(devices):
            item_brand = QTableWidgetItem(dev.brand)
            item_brand.setData(Qt.ItemDataRole.UserRole, dev.id)
            self.table.setItem(row, 0, item_brand)

            self.table.setItem(row, 1, QTableWidgetItem(dev.model))
            self.table.setItem(row, 2, QTableWidgetItem(dev.imei_serial or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(dev.color or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(dev.customer.name))
            self.table.setItem(row, 5, QTableWidgetItem(dev.customer.phone))

            # Actions
            actions = QWidget()
            actions.setStyleSheet("QWidget { background: transparent; }")
            act_layout = QHBoxLayout(actions)
            act_layout.setContentsMargins(6, 4, 6, 4)
            act_layout.setSpacing(5)

            btn_job = QPushButton("  Job")
            btn_job.setIcon(get_icon("plus", "#1d4ed8", 14))
            btn_job.setProperty("class", "btn-tbl-print")
            btn_job.setFixedHeight(30)
            btn_job.setToolTip("Receive New Repair Job for this Device")
            btn_job.clicked.connect(lambda _, d=dev: self._handle_new_job_for_device(d))
            act_layout.addWidget(btn_job)

            btn_edit = QPushButton("  Edit")
            btn_edit.setIcon(get_icon("edit", "#15803d", 14))
            btn_edit.setProperty("class", "btn-tbl-edit")
            btn_edit.setFixedHeight(30)
            btn_edit.setToolTip("Edit Device")
            btn_edit.clicked.connect(lambda _, d=dev: self._handle_edit_device(d))
            act_layout.addWidget(btn_edit)

            btn_del = QPushButton("  Delete")
            btn_del.setIcon(get_icon("trash", "#dc2626", 14))
            btn_del.setProperty("class", "btn-tbl-delete")
            btn_del.setFixedHeight(30)
            btn_del.setToolTip("Delete Device")
            btn_del.clicked.connect(lambda _, d=dev: self._handle_delete_device(d))
            act_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 6, actions)

    def _handle_new_device(self):
        dialog = DeviceDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_devices()

    def _handle_edit_device(self, device: Device):
        fresh_dev = DeviceService.get_by_id(device.id)
        if fresh_dev:
            dialog = DeviceDialog(device=fresh_dev, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_devices()

    def _handle_new_job_for_device(self, device: Device):
        dialog = JobDialog(
            preselected_customer_id=device.customer_id,
            preselected_device_id=device.id,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.should_print and dialog.saved_job:
                preview = ThermalPrintPreviewDialog(dialog.saved_job, parent=self)
                preview.exec()

    def _handle_delete_device(self, device: Device):
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete device '{device.brand} {device.model}'?\n"
            f"This will also delete {len(device.jobs)} repair job(s) associated with this device.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DeviceService.delete(device.id)
            self.load_devices()

    def _on_row_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            device_id = item.data(Qt.ItemDataRole.UserRole)
            dev = DeviceService.get_by_id(device_id)
            if dev:
                self._handle_edit_device(dev)
