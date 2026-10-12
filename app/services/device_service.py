from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.database.connection import session_scope
from app.database.models import Device, Customer, RepairJob


class DeviceService:
    @staticmethod
    def get_by_customer(customer_id: int) -> List[Device]:
        """Fetch all devices registered under a specific customer."""
        with session_scope() as session:
            stmt = select(Device).where(
                Device.customer_id == customer_id
            ).options(
                selectinload(Device.jobs)
            ).order_by(Device.id.desc())
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_all(search_query: str = "") -> List[Device]:
        """Fetch all devices with search across brand, model, IMEI, customer name/phone."""
        with session_scope() as session:
            stmt = select(Device).options(
                selectinload(Device.customer),
                selectinload(Device.jobs)
            ).order_by(Device.id.desc())

            if search_query.strip():
                term = f"%{search_query.strip()}%"
                stmt = stmt.join(Device.customer).where(
                    or_(
                        Device.brand.ilike(term),
                        Device.model.ilike(term),
                        Device.imei_serial.ilike(term),
                        Device.color.ilike(term),
                        Customer.name.ilike(term),
                        Customer.phone.ilike(term)
                    )
                )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_by_id(device_id: int) -> Optional[Device]:
        """Fetch single device by ID with relations."""
        with session_scope() as session:
            stmt = select(Device).where(Device.id == device_id).options(
                selectinload(Device.customer),
                selectinload(Device.jobs)
            )
            return session.scalars(stmt).first()

    @staticmethod
    def create(
        customer_id: int,
        brand: str,
        model: str,
        imei_serial: Optional[str] = None,
        color: Optional[str] = None,
        accessories_received: Optional[str] = None,
        physical_condition: Optional[str] = None
    ) -> Device:
        """Register a new device under a customer."""
        if not brand.strip():
            raise ValueError("Device brand is required.")
        if not model.strip():
            raise ValueError("Device model is required.")

        with session_scope() as session:
            device = Device(
                customer_id=customer_id,
                brand=brand.strip(),
                model=model.strip(),
                imei_serial=imei_serial.strip() if imei_serial else None,
                color=color.strip() if color else None,
                accessories_received=accessories_received.strip() if accessories_received else None,
                physical_condition=physical_condition.strip() if physical_condition else None
            )
            session.add(device)
            session.flush()
            session.refresh(device)
            return device

    @staticmethod
    def update(
        device_id: int,
        brand: str,
        model: str,
        imei_serial: Optional[str] = None,
        color: Optional[str] = None,
        accessories_received: Optional[str] = None,
        physical_condition: Optional[str] = None
    ) -> Device:
        """Update existing device specs."""
        if not brand.strip():
            raise ValueError("Device brand is required.")
        if not model.strip():
            raise ValueError("Device model is required.")

        with session_scope() as session:
            device = session.get(Device, device_id)
            if not device:
                raise ValueError(f"Device with ID {device_id} not found.")

            device.brand = brand.strip()
            device.model = model.strip()
            device.imei_serial = imei_serial.strip() if imei_serial else None
            device.color = color.strip() if color else None
            device.accessories_received = accessories_received.strip() if accessories_received else None
            device.physical_condition = physical_condition.strip() if physical_condition else None
            session.flush()
            session.refresh(device)
            return device

    @staticmethod
    def delete(device_id: int) -> bool:
        """Delete device and associated jobs."""
        with session_scope() as session:
            device = session.get(Device, device_id)
            if not device:
                return False
            session.delete(device)
            return True
