from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import or_, select, func
from sqlalchemy.orm import selectinload

from app.database.connection import session_scope
from app.database.models import RepairJob, Customer, Device, JobStatus, User


class JobService:
    @staticmethod
    def generate_job_number() -> str:
        """
        Generate a unique, human-readable job number formatted as AT-YYYYMM-XXXX.
        Example: AT-202610-0001
        """
        now = datetime.now()
        prefix = f"AT-{now.year}{now.month:02d}-"

        with session_scope() as session:
            stmt = select(RepairJob.job_number).where(
                RepairJob.job_number.like(f"{prefix}%")
            ).order_by(RepairJob.id.desc()).limit(1)
            last_job_num = session.scalar(stmt)

            if last_job_num:
                try:
                    last_seq = int(last_job_num.split("-")[-1])
                    new_seq = last_seq + 1
                except (ValueError, IndexError):
                    new_seq = 1
            else:
                new_seq = 1

            return f"{prefix}{new_seq:04d}"

    @staticmethod
    def create(
        customer_id: int,
        device_id: int,
        complaint: str,
        physical_condition: Optional[str] = None,
        accessories_received: Optional[str] = None,
        passcode_lock: Optional[str] = None,
        technician_id: Optional[int] = None,
        estimated_delivery_date: Optional[datetime] = None,
        estimated_cost: float = 0.0,
        advance_paid: float = 0.0,
        custom_job_number: Optional[str] = None,
        status: Optional[str] = None
    ) -> RepairJob:
        """Create and persist a new repair job."""
        if not complaint.strip():
            raise ValueError("Customer complaint is required.")

        job_number = custom_job_number or JobService.generate_job_number()
        initial_status = status or JobStatus.IN_PROGRESS

        with session_scope() as session:
            job = RepairJob(
                job_number=job_number,
                customer_id=customer_id,
                device_id=device_id,
                complaint=complaint.strip(),
                physical_condition=physical_condition.strip() if physical_condition else None,
                accessories_received=accessories_received.strip() if accessories_received else None,
                passcode_lock=passcode_lock.strip() if passcode_lock else None,
                technician_id=technician_id,
                estimated_delivery_date=estimated_delivery_date,
                estimated_cost=float(estimated_cost or 0.0),
                advance_paid=float(advance_paid or 0.0),
                actual_cost=float(estimated_cost or 0.0),
                status=initial_status,
                received_at=datetime.now(timezone.utc)
            )
            session.add(job)
            session.flush()
            session.refresh(job)
            return job

    @staticmethod
    def update(
        job_id: int,
        complaint: str,
        physical_condition: Optional[str] = None,
        accessories_received: Optional[str] = None,
        passcode_lock: Optional[str] = None,
        technician_id: Optional[int] = None,
        estimated_delivery_date: Optional[datetime] = None,
        estimated_cost: float = 0.0,
        advance_paid: float = 0.0,
        actual_cost: float = 0.0,
        status: Optional[str] = None,
        technician_diagnosis: Optional[str] = None,
        technician_notes: Optional[str] = None
    ) -> RepairJob:
        """Update job information, financials, technician assignment, or findings."""
        if not complaint.strip():
            raise ValueError("Customer complaint is required.")

        with session_scope() as session:
            job = session.get(RepairJob, job_id)
            if not job:
                raise ValueError(f"Repair job with ID {job_id} not found.")

            job.complaint = complaint.strip()
            job.physical_condition = physical_condition.strip() if physical_condition else None
            job.accessories_received = accessories_received.strip() if accessories_received else None
            job.passcode_lock = passcode_lock.strip() if passcode_lock else None
            job.technician_id = technician_id
            job.estimated_delivery_date = estimated_delivery_date
            job.estimated_cost = float(estimated_cost or 0.0)
            job.advance_paid = float(advance_paid or 0.0)
            job.actual_cost = float(actual_cost or 0.0)

            if technician_diagnosis is not None:
                job.technician_diagnosis = technician_diagnosis.strip() if technician_diagnosis else None
                if job.technician_diagnosis and not job.diagnosed_at:
                    job.diagnosed_at = datetime.now(timezone.utc)

            if technician_notes is not None:
                job.technician_notes = technician_notes.strip() if technician_notes else None

            if status and status != job.status:
                job.status = status
                if status == JobStatus.DIAGNOSING and not job.diagnosed_at:
                    job.diagnosed_at = datetime.now(timezone.utc)
                elif status == JobStatus.READY and not job.completed_at:
                    job.completed_at = datetime.now(timezone.utc)
                elif status == JobStatus.DELIVERED and not job.delivered_at:
                    job.delivered_at = datetime.now(timezone.utc)

            session.flush()
            session.refresh(job)
            return job

    @staticmethod
    def update_diagnosis(
        job_id: int,
        technician_diagnosis: str,
        technician_notes: Optional[str] = None,
        actual_cost: Optional[float] = None,
        status: Optional[str] = None,
        technician_id: Optional[int] = None
    ) -> RepairJob:
        """Record technician diagnosis, update actual cost and status."""
        with session_scope() as session:
            job = session.get(RepairJob, job_id)
            if not job:
                raise ValueError(f"Repair job with ID {job_id} not found.")

            job.technician_diagnosis = technician_diagnosis.strip() if technician_diagnosis else None
            job.diagnosed_at = datetime.now(timezone.utc)

            if technician_notes is not None:
                job.technician_notes = technician_notes.strip() if technician_notes else None

            if actual_cost is not None:
                job.actual_cost = float(actual_cost)

            if technician_id is not None:
                job.technician_id = technician_id

            if status:
                job.status = status
                if status == JobStatus.READY and not job.completed_at:
                    job.completed_at = datetime.now(timezone.utc)
                elif status == JobStatus.DELIVERED and not job.delivered_at:
                    job.delivered_at = datetime.now(timezone.utc)

            session.flush()
            session.refresh(job)
            return job

    @staticmethod
    def get_by_id(job_id: int) -> Optional[RepairJob]:
        """Fetch job with fully loaded customer, device and technician objects."""
        with session_scope() as session:
            stmt = select(RepairJob).where(RepairJob.id == job_id).options(
                selectinload(RepairJob.customer),
                selectinload(RepairJob.device),
                selectinload(RepairJob.technician)
            )
            return session.scalars(stmt).first()

    @staticmethod
    def get_by_number(job_number: str) -> Optional[RepairJob]:
        """Lookup job by unique job number."""
        with session_scope() as session:
            stmt = select(RepairJob).where(RepairJob.job_number == job_number).options(
                selectinload(RepairJob.customer),
                selectinload(RepairJob.device),
                selectinload(RepairJob.technician)
            )
            return session.scalars(stmt).first()

    @staticmethod
    def get_all(
        status_filter: str = "All",
        search_query: str = "",
        technician_id: Optional[int] = None
    ) -> List[RepairJob]:
        """
        Query repair jobs with optional status, technician filtering, and search query.
        """
        with session_scope() as session:
            stmt = select(RepairJob).options(
                selectinload(RepairJob.customer),
                selectinload(RepairJob.device),
                selectinload(RepairJob.technician)
            ).order_by(RepairJob.id.desc())

            if status_filter and status_filter != "All":
                stmt = stmt.where(RepairJob.status == status_filter)

            if technician_id is not None:
                stmt = stmt.where(RepairJob.technician_id == technician_id)

            if search_query.strip():
                term = f"%{search_query.strip()}%"
                stmt = stmt.join(RepairJob.customer).join(RepairJob.device).where(
                    or_(
                        RepairJob.job_number.ilike(term),
                        Customer.name.ilike(term),
                        Customer.phone.ilike(term),
                        Device.brand.ilike(term),
                        Device.model.ilike(term),
                        Device.imei_serial.ilike(term),
                        RepairJob.complaint.ilike(term),
                        RepairJob.passcode_lock.ilike(term)
                    )
                )

            return list(session.scalars(stmt).all())

    @staticmethod
    def get_recent(limit: int = 10) -> List[RepairJob]:
        """Fetch the most recent repair jobs for dashboard display."""
        with session_scope() as session:
            stmt = select(RepairJob).options(
                selectinload(RepairJob.customer),
                selectinload(RepairJob.device),
                selectinload(RepairJob.technician)
            ).order_by(RepairJob.id.desc()).limit(limit)
            return list(session.scalars(stmt).all())

    @staticmethod
    def delete(job_id: int) -> bool:
        """Delete repair job."""
        with session_scope() as session:
            job = session.get(RepairJob, job_id)
            if not job:
                return False
            session.delete(job)
            return True

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        """Calculate and return key operational metrics for the dashboard."""
        with session_scope() as session:
            total_customers = session.query(Customer).count()
            total_jobs = session.query(RepairJob).count()

            pending_diagnosis = session.query(RepairJob).filter(
                RepairJob.status.in_([JobStatus.RECEIVED, JobStatus.DIAGNOSING])
            ).count()

            in_progress = session.query(RepairJob).filter(
                RepairJob.status == JobStatus.IN_PROGRESS
            ).count()

            ready = session.query(RepairJob).filter(
                RepairJob.status == JobStatus.READY
            ).count()

            delivered = session.query(RepairJob).filter(
                RepairJob.status == JobStatus.DELIVERED
            ).count()

            return {
                "total_customers": total_customers,
                "total_jobs": total_jobs,
                "pending_diagnosis": pending_diagnosis,
                "in_progress": in_progress,
                "ready_for_delivery": ready,
                "delivered": delivered,
            }
