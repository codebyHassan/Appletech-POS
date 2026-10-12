import logging
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from app.database.connection import session_scope
from app.database.models import Expense, ExpenseCategory, PaymentMethod, RepairJob, JobStatus, User

logger = logging.getLogger(__name__)


class ExpenseService:
    """
    Business logic for managing daily shop expenses and calculating net profits.
    """

    @classmethod
    def add_expense(
        cls,
        title: str,
        amount: float,
        category: str = ExpenseCategory.OTHER,
        payment_mode: str = PaymentMethod.CASH,
        reference_no: Optional[str] = None,
        notes: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        expense_date: Optional[datetime] = None
    ) -> Tuple[bool, Optional[Expense], str]:
        if not title or not title.strip():
            return False, None, "Expense title / description is required."
        if amount <= 0:
            return False, None, "Expense amount must be greater than zero."

        if expense_date is None:
            expense_date = datetime.now(timezone.utc)

        with session_scope() as session:
            expense = Expense(
                title=title.strip(),
                category=category or ExpenseCategory.OTHER,
                amount=float(amount),
                payment_mode=payment_mode or PaymentMethod.CASH,
                reference_no=reference_no.strip() if reference_no else None,
                notes=notes.strip() if notes else None,
                created_by_user_id=created_by_user_id,
                expense_date=expense_date
            )
            session.add(expense)
            session.flush()
            session.refresh(expense)
            session.expunge(expense)
            return True, expense, "Expense recorded successfully."

    @classmethod
    def update_expense(
        cls,
        expense_id: int,
        title: str,
        amount: float,
        category: str,
        payment_mode: str,
        reference_no: Optional[str] = None,
        notes: Optional[str] = None,
        expense_date: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        if not title or not title.strip():
            return False, "Expense title is required."
        if amount <= 0:
            return False, "Amount must be greater than zero."

        with session_scope() as session:
            expense = session.query(Expense).filter_by(id=expense_id).first()
            if not expense:
                return False, "Expense not found."

            expense.title = title.strip()
            expense.category = category
            expense.amount = float(amount)
            expense.payment_mode = payment_mode
            expense.reference_no = reference_no.strip() if reference_no else None
            expense.notes = notes.strip() if notes else None
            if expense_date:
                expense.expense_date = expense_date

            return True, "Expense updated successfully."

    @classmethod
    def delete_expense(cls, expense_id: int) -> Tuple[bool, str]:
        with session_scope() as session:
            expense = session.query(Expense).filter_by(id=expense_id).first()
            if not expense:
                return False, "Expense not found."
            session.delete(expense)
            return True, "Expense deleted successfully."

    @classmethod
    def get_expense_by_id(cls, expense_id: int) -> Optional[Expense]:
        with session_scope() as session:
            expense = session.query(Expense).filter_by(id=expense_id).first()
            if expense:
                session.expunge(expense)
            return expense

    @classmethod
    def get_expenses(
        cls,
        search_query: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        payment_mode: Optional[str] = None,
        limit: int = 200
    ) -> List[Expense]:
        with session_scope() as session:
            query = session.query(Expense)

            if search_query and search_query.strip():
                pattern = f"%{search_query.strip()}%"
                query = query.filter(
                    or_(
                        Expense.title.ilike(pattern),
                        Expense.reference_no.ilike(pattern),
                        Expense.notes.ilike(pattern)
                    )
                )

            if category and category != "All Categories":
                query = query.filter(Expense.category == category)

            if payment_mode and payment_mode != "All Methods":
                query = query.filter(Expense.payment_mode == payment_mode)

            if start_date:
                query = query.filter(Expense.expense_date >= start_date)

            if end_date:
                query = query.filter(Expense.expense_date <= end_date)

            expenses = query.order_by(desc(Expense.expense_date)).limit(limit).all()
            for exp in expenses:
                if exp.created_by:
                    _ = exp.created_by.full_name
            session.expunge_all()
            return expenses

    @classmethod
    def get_financial_summary(cls, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculate complete financial metrics:
        - Total Repair Revenue (Delivered Jobs actual costs + non-delivered advance payments)
        - Total Shop Expenses
        - Net Shop Profit (Revenue - Expenses)
        - Category breakdown of expenses
        """
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
        this_month_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

        with session_scope() as session:
            # 1. Expenses queries
            exp_query = session.query(func.coalesce(func.sum(Expense.amount), 0.0))
            if start_date:
                exp_query = exp_query.filter(Expense.expense_date >= start_date)
            if end_date:
                exp_query = exp_query.filter(Expense.expense_date <= end_date)
            period_expenses = float(exp_query.scalar())

            # Today's expenses
            today_expenses = float(
                session.query(func.coalesce(func.sum(Expense.amount), 0.0))
                .filter(Expense.expense_date >= today_start)
                .scalar()
            )

            # This month's expenses
            month_expenses = float(
                session.query(func.coalesce(func.sum(Expense.amount), 0.0))
                .filter(Expense.expense_date >= this_month_start)
                .scalar()
            )

            # Category Breakdown
            cat_query = session.query(
                Expense.category,
                func.sum(Expense.amount).label("total")
            )
            if start_date:
                cat_query = cat_query.filter(Expense.expense_date >= start_date)
            if end_date:
                cat_query = cat_query.filter(Expense.expense_date <= end_date)
            cat_rows = cat_query.group_by(Expense.category).all()
            category_breakdown = {row[0]: float(row[1]) for row in cat_rows}

            # 2. Revenue calculation
            # Delivered jobs revenue (actual_cost)
            rev_delivered_query = session.query(func.coalesce(func.sum(RepairJob.actual_cost), 0.0)).filter(
                RepairJob.status == JobStatus.DELIVERED
            )
            # In-progress / ready jobs advance collected
            rev_advance_query = session.query(func.coalesce(func.sum(RepairJob.advance_paid), 0.0)).filter(
                RepairJob.status.in_([JobStatus.RECEIVED, JobStatus.DIAGNOSING, JobStatus.IN_PROGRESS, JobStatus.READY])
            )

            if start_date:
                rev_delivered_query = rev_delivered_query.filter(RepairJob.delivered_at >= start_date)
                rev_advance_query = rev_advance_query.filter(RepairJob.received_at >= start_date)
            if end_date:
                rev_delivered_query = rev_delivered_query.filter(RepairJob.delivered_at <= end_date)
                rev_advance_query = rev_advance_query.filter(RepairJob.received_at <= end_date)

            total_revenue = float(rev_delivered_query.scalar()) + float(rev_advance_query.scalar())
            net_profit = total_revenue - period_expenses

            return {
                "total_revenue": total_revenue,
                "total_expenses": period_expenses,
                "net_profit": net_profit,
                "today_expenses": today_expenses,
                "month_expenses": month_expenses,
                "category_breakdown": category_breakdown
            }
