from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.database.connection import session_scope, get_session
from app.database.models import Customer, Device, RepairJob


class CustomerService:
    @staticmethod
    def get_all(search_query: str = "") -> List[Customer]:
        """Fetch all customers with optional name/phone/address search filtering."""
        with session_scope() as session:
            stmt = select(Customer).options(
                selectinload(Customer.devices),
                selectinload(Customer.jobs)
            ).order_by(Customer.id.desc())

            if search_query.strip():
                term = f"%{search_query.strip()}%"
                stmt = stmt.where(
                    or_(
                        Customer.name.ilike(term),
                        Customer.phone.ilike(term),
                        Customer.address.ilike(term),
                        Customer.email.ilike(term)
                    )
                )
            result = session.scalars(stmt).all()
            return list(result)

    @staticmethod
    def get_by_id(customer_id: int) -> Optional[Customer]:
        """Fetch single customer by ID with related devices and jobs."""
        with session_scope() as session:
            stmt = select(Customer).where(Customer.id == customer_id).options(
                selectinload(Customer.devices),
                selectinload(Customer.jobs)
            )
            return session.scalars(stmt).first()

    @staticmethod
    def create(name: str, phone: str, email: Optional[str] = None, address: Optional[str] = None) -> Customer:
        """Create and persist a new customer."""
        if not name.strip():
            raise ValueError("Customer name is required.")
        if not phone.strip():
            raise ValueError("Customer phone number is required.")

        with session_scope() as session:
            customer = Customer(
                name=name.strip(),
                phone=phone.strip(),
                email=email.strip() if email else None,
                address=address.strip() if address else None
            )
            session.add(customer)
            session.flush()
            session.refresh(customer)
            return customer

    @staticmethod
    def update(customer_id: int, name: str, phone: str, email: Optional[str] = None, address: Optional[str] = None) -> Customer:
        """Update existing customer details."""
        if not name.strip():
            raise ValueError("Customer name is required.")
        if not phone.strip():
            raise ValueError("Customer phone number is required.")

        with session_scope() as session:
            customer = session.get(Customer, customer_id)
            if not customer:
                raise ValueError(f"Customer with ID {customer_id} not found.")

            customer.name = name.strip()
            customer.phone = phone.strip()
            customer.email = email.strip() if email else None
            customer.address = address.strip() if address else None
            session.flush()
            session.refresh(customer)
            return customer

    @staticmethod
    def delete(customer_id: int) -> bool:
        """Delete customer and associated records."""
        with session_scope() as session:
            customer = session.get(Customer, customer_id)
            if not customer:
                return False
            session.delete(customer)
            return True

    @staticmethod
    def get_customer_history(customer_id: int) -> List[RepairJob]:
        """Get all repair jobs for a customer ordered from newest to oldest."""
        with session_scope() as session:
            stmt = select(RepairJob).where(
                RepairJob.customer_id == customer_id
            ).options(
                selectinload(RepairJob.device)
            ).order_by(RepairJob.id.desc())
            return list(session.scalars(stmt).all())
