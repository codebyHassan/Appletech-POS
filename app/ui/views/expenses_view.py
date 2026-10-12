import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from app.database.models import Expense, ExpenseCategory, PaymentMethod
from app.services.expense_service import ExpenseService
from app.services.auth_service import AuthService
from app.ui.icons import get_icon
from app.ui.dialogs.expense_dialog import ExpenseDialog
from app.ui.components.print_preview_dialog import ThermalPrintPreviewDialog

logger = logging.getLogger(__name__)


class ExpensesView(QWidget):
    """
    Modern White & Blue ERP View for tracking shop expenses, parts purchases,
    and calculating net profit/loss.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_expenses()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Page Header
        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(2)

        page_title = QLabel("Expense & Kharcha Management")
        page_title.setProperty("class", "page-title")
        page_sub = QLabel("Track parts purchase, daily refreshments, shop rent, and calculate net shop profits.")
        page_sub.setProperty("class", "page-subtitle")

        header_left.addWidget(page_title)
        header_left.addWidget(page_sub)
        header_layout.addLayout(header_left)
        header_layout.addStretch()

        self.btn_add_expense = QPushButton("  Record Expense")
        self.btn_add_expense.setIcon(get_icon("plus", "#ffffff", 16))
        self.btn_add_expense.setProperty("class", "btn-primary")
        self.btn_add_expense.setFixedHeight(38)
        self.btn_add_expense.clicked.connect(self._handle_add_expense)
        header_layout.addWidget(self.btn_add_expense)

        main_layout.addLayout(header_layout)

        # 2. Financial KPI Metric Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        # Card 1: Today's Expense
        self.card_today_exp = self._create_kpi_card("TODAY'S EXPENSES", "Rs. 0.00", "#ef4444", "#fef2f2")
        # Card 2: Month's Expense
        self.card_month_exp = self._create_kpi_card("THIS MONTH'S EXPENSES", "Rs. 0.00", "#d97706", "#fffbeb")
        # Card 3: Total Revenue
        self.card_revenue = self._create_kpi_card("REPAIR REVENUE", "Rs. 0.00", "#2563eb", "#eff6ff")
        # Card 4: Net Shop Profit
        self.card_net_profit = self._create_kpi_card("NET SHOP PROFIT", "Rs. 0.00", "#16a34a", "#f0fdf4")

        kpi_layout.addWidget(self.card_today_exp)
        kpi_layout.addWidget(self.card_month_exp)
        kpi_layout.addWidget(self.card_revenue)
        kpi_layout.addWidget(self.card_net_profit)

        main_layout.addLayout(kpi_layout)

        # 3. Filter Toolbar
        toolbar_card = QFrame()
        toolbar_card.setProperty("class", "card")
        toolbar_card.setStyleSheet("QFrame.card { padding: 10px 14px; background-color: #ffffff; }")
        toolbar_layout = QHBoxLayout(toolbar_card)
        toolbar_layout.setSpacing(10)
        toolbar_layout.setContentsMargins(6, 6, 6, 6)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search expenses by title, invoice #, notes...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.load_expenses)
        toolbar_layout.addWidget(self.search_input, 2)

        # Category Filter
        self.combo_category_filter = QComboBox()
        self.combo_category_filter.addItem("All Categories")
        for cat in ExpenseCategory.ALL_CATEGORIES:
            self.combo_category_filter.addItem(cat)
        self.combo_category_filter.currentIndexChanged.connect(self.load_expenses)
        toolbar_layout.addWidget(self.combo_category_filter, 1)

        # Date Range Filter Preset
        self.combo_date_filter = QComboBox()
        self.combo_date_filter.addItem("All Time")
        self.combo_date_filter.addItem("Today")
        self.combo_date_filter.addItem("This Week")
        self.combo_date_filter.addItem("This Month")
        self.combo_date_filter.currentIndexChanged.connect(self.load_expenses)
        toolbar_layout.addWidget(self.combo_date_filter, 1)

        # Refresh button
        btn_refresh = QPushButton("  Refresh")
        btn_refresh.setIcon(get_icon("refresh", "#334155", 16))
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_expenses)
        toolbar_layout.addWidget(btn_refresh)

        main_layout.addWidget(toolbar_card)

        # 4. Expenses Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date & Time", "Expense Title", "Category",
            "Payment", "Ref / Bill #", "Amount (Rs.)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
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

        main_layout.addWidget(self.table, 1)

    def _create_kpi_card(self, title: str, initial_value: str, text_color: str, bg_color: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame.card {{
                background-color: {bg_color};
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 4, 8, 4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")

        v_lbl = QLabel(initial_value)
        v_lbl.setObjectName("valLabel")
        v_lbl.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {text_color};")

        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        return card

    def _get_date_filter_range(self):
        preset = self.combo_date_filter.currentText()
        now = datetime.now(timezone.utc)
        if preset == "Today":
            start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
            return start, None
        elif preset == "This Week":
            start = now - timedelta(days=now.weekday())
            start = datetime(start.year, start.month, start.day, 0, 0, 0, tzinfo=timezone.utc)
            return start, None
        elif preset == "This Month":
            start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            return start, None
        return None, None

    def load_expenses(self):
        query = self.search_input.text().strip()
        cat = self.combo_category_filter.currentText()
        start_date, end_date = self._get_date_filter_range()

        expenses = ExpenseService.get_expenses(
            search_query=query,
            category=cat if cat != "All Categories" else None,
            start_date=start_date,
            end_date=end_date
        )

        self._populate_table(expenses)
        self._update_kpi_cards(start_date, end_date)

    def _populate_table(self, expenses):
        self.table.setRowCount(len(expenses))
        can_delete = AuthService.can_delete_records()

        for row_idx, exp in enumerate(expenses):
            # ID
            item_id = QTableWidgetItem(f"#{exp.id}")
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, item_id)

            # Date
            d_str = exp.expense_date.strftime("%d-%b-%Y %I:%M %p") if exp.expense_date else "-"
            item_date = QTableWidgetItem(d_str)
            item_date.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, item_date)

            # Title & Notes
            title_text = exp.title
            if exp.notes:
                title_text += f"\nNote: {exp.notes}"
            item_title = QTableWidgetItem(title_text)
            self.table.setItem(row_idx, 2, item_title)

            # Category
            item_cat = QTableWidgetItem(exp.category)
            item_cat.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 3, item_cat)

            # Payment
            item_pay = QTableWidgetItem(exp.payment_mode)
            item_pay.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 4, item_pay)

            # Ref
            item_ref = QTableWidgetItem(exp.reference_no or "-")
            item_ref.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 5, item_ref)

            # Amount
            item_amt = QTableWidgetItem(f"Rs. {exp.amount:,.2f}")
            item_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_amt.setForeground(QColor("#ef4444"))
            font_amt = item_amt.font()
            font_amt.setBold(True)
            item_amt.setFont(font_amt)
            self.table.setItem(row_idx, 6, item_amt)

            # Action Buttons Widget
            actions_widget = QWidget()
            actions_widget.setStyleSheet("QWidget { background: transparent; }")
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(6, 4, 6, 4)
            act_layout.setSpacing(5)

            btn_edit = QPushButton("  Edit")
            btn_edit.setIcon(get_icon("edit", "#15803d", 14))
            btn_edit.setProperty("class", "btn-tbl-edit")
            btn_edit.setFixedHeight(30)
            btn_edit.setToolTip("Edit Expense")
            btn_edit.clicked.connect(lambda _, e=exp: self._handle_edit_expense(e))
            act_layout.addWidget(btn_edit)

            if can_delete:
                btn_del = QPushButton("  Delete")
                btn_del.setIcon(get_icon("trash", "#dc2626", 14))
                btn_del.setProperty("class", "btn-tbl-delete")
                btn_del.setFixedHeight(30)
                btn_del.setToolTip("Delete Expense")
                btn_del.clicked.connect(lambda _, e=exp: self._handle_delete_expense(e))
                act_layout.addWidget(btn_del)

            self.table.setCellWidget(row_idx, 7, actions_widget)

    def _update_kpi_cards(self, start_date, end_date):
        summary = ExpenseService.get_financial_summary(start_date=start_date, end_date=end_date)
        
        lbl_today = self.card_today_exp.findChild(QLabel, "valLabel")
        if lbl_today:
            lbl_today.setText(f"Rs. {summary['today_expenses']:,.2f}")

        lbl_month = self.card_month_exp.findChild(QLabel, "valLabel")
        if lbl_month:
            lbl_month.setText(f"Rs. {summary['month_expenses']:,.2f}")

        lbl_rev = self.card_revenue.findChild(QLabel, "valLabel")
        if lbl_rev:
            lbl_rev.setText(f"Rs. {summary['total_revenue']:,.2f}")

        lbl_profit = self.card_net_profit.findChild(QLabel, "valLabel")
        if lbl_profit:
            profit = summary['net_profit']
            lbl_profit.setText(f"Rs. {profit:,.2f}")
            if profit < 0:
                lbl_profit.setStyleSheet("font-size: 20px; font-weight: 900; color: #dc2626;")
            else:
                lbl_profit.setStyleSheet("font-size: 20px; font-weight: 900; color: #16a34a;")

    def _handle_add_expense(self):
        dialog = ExpenseDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_expenses()

    def _handle_edit_expense(self, expense: Expense):
        dialog = ExpenseDialog(expense=expense, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_expenses()

    def _handle_delete_expense(self, expense: Expense):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete expense record:\n\n'{expense.title}' (Rs. {expense.amount:,.2f})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = ExpenseService.delete_expense(expense.id)
            if success:
                self.load_expenses()
            else:
                QMessageBox.critical(self, "Error", msg)
