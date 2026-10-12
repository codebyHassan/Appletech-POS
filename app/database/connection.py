import logging
import sqlite3
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session

from app.config import get_database_path, DEFAULT_SHOP_CONFIG
from app.database.models import Base, ShopSetting

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None
_ScopedSession: scoped_session[Session] | None = None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable SQLite Foreign Key enforcement and WAL mode for reliability."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    except Exception as e:
        logger.warning(f"Failed to set sqlite pragma: {e}")


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        db_path = get_database_path()
        db_url = f"sqlite:///{db_path.as_posix()}"
        _engine = create_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory, _ScopedSession
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        _ScopedSession = scoped_session(_SessionFactory)
    return _SessionFactory


def get_session() -> Session:
    """Create a new independent database session."""
    factory = get_session_factory()
    return factory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of database operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction rollback due to: {e}")
        raise
    finally:
        session.close()


def _migrate_columns_if_needed(engine: Engine):
    """
    Safely add newly introduced columns to existing SQLite tables.
    """
    with engine.connect() as conn:
        # Check repair_jobs columns
        try:
            res = conn.execute(text("PRAGMA table_info(repair_jobs)")).fetchall()
            existing_cols = {row[1] for row in res}
            
            if existing_cols:
                if "technician_id" not in existing_cols:
                    conn.execute(text("ALTER TABLE repair_jobs ADD COLUMN technician_id INTEGER REFERENCES users(id) ON DELETE SET NULL"))
                if "passcode_lock" not in existing_cols:
                    conn.execute(text("ALTER TABLE repair_jobs ADD COLUMN passcode_lock VARCHAR(100)"))
                if "estimated_delivery_date" not in existing_cols:
                    conn.execute(text("ALTER TABLE repair_jobs ADD COLUMN estimated_delivery_date DATETIME"))
                conn.commit()
        except Exception as e:
            logger.debug(f"Migration check on repair_jobs: {e}")


def init_db(seed_sample_data: bool = False):
    """
    Initialize database schema, migrate new columns, and seed defaults.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_columns_if_needed(engine)

    from app.services.auth_service import AuthService
    AuthService.ensure_default_users()

    with session_scope() as session:
        # Seed default shop settings if missing
        for key, default_val in DEFAULT_SHOP_CONFIG.items():
            existing = session.query(ShopSetting).filter_by(key=key).first()
            if not existing:
                session.add(ShopSetting(key=key, value=str(default_val)))

        # Optional sample data
        if seed_sample_data:
            from app.database.models import Customer, Device, RepairJob, JobStatus, Expense, ExpenseCategory, PaymentMethod
            cust_count = session.query(Customer).count()
            if cust_count == 0:
                cust1 = Customer(
                    name="Muhammad Ali",
                    phone="0300-1234567",
                    email="ali.tech@example.com",
                    address="Block 5, Clifton, Karachi"
                )
                session.add(cust1)
                session.flush()

                dev1 = Device(
                    customer_id=cust1.id,
                    brand="Apple",
                    model="iPhone 13 Pro",
                    imei_serial="354892109876543",
                    color="Sierra Blue",
                    accessories_received="Original Box, Sim Tray",
                    physical_condition="Minor scratches on back, broken front glass"
                )
                session.add(dev1)
                session.flush()

                job1 = RepairJob(
                    job_number="AT-202610-0001",
                    customer_id=cust1.id,
                    device_id=dev1.id,
                    complaint="OLED display blank after drop, touch not responding",
                    physical_condition="Cracked screen glass, body normal",
                    accessories_received="Sim Tray",
                    passcode_lock="2580",
                    estimated_cost=15000.0,
                    advance_paid=5000.0,
                    actual_cost=14500.0,
                    status=JobStatus.IN_PROGRESS,
                    technician_diagnosis="OLED flex cable cracked, panel requires full replacement.",
                    technician_notes="Original Apple display ordered from supplier."
                )
                session.add(job1)

                cust2 = Customer(
                    name="Sara Khan",
                    phone="0321-7654321",
                    email="sara.k@example.com",
                    address="DHA Phase 6, Lahore"
                )
                session.add(cust2)
                session.flush()

                dev2 = Device(
                    customer_id=cust2.id,
                    brand="Samsung",
                    model="Galaxy S23 Ultra",
                    imei_serial="359871101234567",
                    color="Phantom Black",
                    accessories_received="S-Pen, Silicon Case",
                    physical_condition="Clean condition, water exposure"
                )
                session.add(dev2)
                session.flush()

                job2 = RepairJob(
                    job_number="AT-202610-0002",
                    customer_id=cust2.id,
                    device_id=dev2.id,
                    complaint="Device not turning on after moisture alert",
                    physical_condition="Mint condition",
                    accessories_received="S-Pen",
                    passcode_lock="Pattern: L-shape",
                    estimated_cost=8500.0,
                    advance_paid=2000.0,
                    actual_cost=8500.0,
                    status=JobStatus.READY,
                    technician_diagnosis="Charging port sub-board replaced and ultrasonic mother-board cleaning completed.",
                    technician_notes="Tested charging, mic, and speaker. 100% functional."
                )
                session.add(job2)

                # Seed demo expense
                exp1 = Expense(
                    title="iPhone 13 Pro OLED Original Screen (Hafeez Centre)",
                    category=ExpenseCategory.PARTS,
                    amount=8500.0,
                    payment_mode=PaymentMethod.CASH,
                    reference_no="BILL-9921",
                    notes="Screen replacement part for job AT-202610-0001"
                )
                exp2 = Expense(
                    title="Daily Shop Refreshments & Tea",
                    category=ExpenseCategory.TEA_FOOD,
                    amount=350.0,
                    payment_mode=PaymentMethod.CASH,
                    notes="Daily afternoon tea for staff"
                )
                session.add(exp1)
                session.add(exp2)


def reset_engine_connection():
    """Reset the engine connection pool, used after restoring a database."""
    global _engine, _SessionFactory, _ScopedSession
    if _engine:
        _engine.dispose()
    _engine = None
    _SessionFactory = None
    _ScopedSession = None
