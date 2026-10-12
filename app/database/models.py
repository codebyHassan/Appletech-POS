from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    func
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)

class Base(DeclarativeBase):
    pass


class UserRole:
    ADMIN = "admin"
    CASHIER = "cashier"
    TECHNICIAN = "technician"

    ALL_ROLES = [ADMIN, CASHIER, TECHNICIAN]
    ROLE_LABELS = {
        ADMIN: "Administrator / Owner",
        CASHIER: "Cashier / Front Desk",
        TECHNICIAN: "Technician / Repairer",
    }


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default=UserRole.CASHIER, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    assigned_jobs: Mapped[List["RepairJob"]] = relationship(
        "RepairJob", back_populates="technician", foreign_keys="RepairJob.technician_id"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="created_by", foreign_keys="Expense.created_by_user_id"
    )

    @property
    def role_display(self) -> str:
        return UserRole.ROLE_LABELS.get(self.role, self.role.capitalize())

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    devices: Mapped[List["Device"]] = relationship(
        "Device", back_populates="customer", cascade="all, delete-orphan", order_by="desc(Device.id)"
    )
    jobs: Mapped[List["RepairJob"]] = relationship(
        "RepairJob", back_populates="customer", cascade="all, delete-orphan", order_by="desc(RepairJob.id)"
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}', phone='{self.phone}')>"


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    imei_serial: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    color: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    accessories_received: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    physical_condition: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="devices")
    jobs: Mapped[List["RepairJob"]] = relationship(
        "RepairJob", back_populates="device", cascade="all, delete-orphan", order_by="desc(RepairJob.id)"
    )

    @property
    def display_name(self) -> str:
        parts = [self.brand, self.model]
        if self.imei_serial:
            parts.append(f"(IMEI/SN: {self.imei_serial})")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, brand='{self.brand}', model='{self.model}')>"


class JobStatus:
    RECEIVED = "Received"
    DIAGNOSING = "Diagnosing"
    IN_PROGRESS = "In Progress"
    READY = "Ready"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"

    ALL_STATUSES = [RECEIVED, DIAGNOSING, IN_PROGRESS, READY, DELIVERED, CANCELLED]


class RepairJob(Base):
    __tablename__ = "repair_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    technician_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Customer complaint and receiving condition
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    physical_condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accessories_received: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    passcode_lock: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Financials
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    advance_paid: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actual_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status & Technician Details
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.IN_PROGRESS, nullable=False, index=True)
    technician_diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technician_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    estimated_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    diagnosed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="jobs")
    device: Mapped["Device"] = relationship("Device", back_populates="jobs")
    technician: Mapped[Optional["User"]] = relationship(
        "User", back_populates="assigned_jobs", foreign_keys=[technician_id]
    )

    @property
    def balance_due(self) -> float:
        cost = self.actual_cost if self.actual_cost > 0 else self.estimated_cost
        return max(0.0, cost - self.advance_paid)

    def __repr__(self) -> str:
        return f"<RepairJob(job_number='{self.job_number}', status='{self.status}')>"


class ExpenseCategory:
    PARTS = "Parts Purchase"
    TOOLS = "Tools & Equipment"
    RENT = "Shop Rent"
    UTILITIES = "Electricity & Utilities"
    TEA_FOOD = "Tea & Refreshments"
    SALARY = "Staff Salary & Commission"
    MARKETING = "Marketing & Promo"
    OTHER = "General / Miscellaneous"

    ALL_CATEGORIES = [PARTS, TOOLS, RENT, UTILITIES, TEA_FOOD, SALARY, MARKETING, OTHER]


class PaymentMethod:
    CASH = "Cash"
    BANK = "Bank Transfer"
    JAZZCASH = "JazzCash"
    EASYPAISA = "EasyPaisa"
    CARD = "Debit/Credit Card"

    ALL_METHODS = [CASH, BANK, JAZZCASH, EASYPAISA, CARD]


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), default=ExpenseCategory.OTHER, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(50), default=PaymentMethod.CASH, nullable=False)
    reference_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    expense_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    created_by: Mapped[Optional["User"]] = relationship(
        "User", back_populates="expenses", foreign_keys=[created_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, title='{self.title}', amount={self.amount})>"


class ShopSetting(Base):
    __tablename__ = "shop_settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<ShopSetting(key='{self.key}')>"
