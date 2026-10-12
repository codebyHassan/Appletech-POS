import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.database.connection import session_scope
from app.database.models import User, UserRole


class AuthService:
    """
    Handles user authentication, password hashing, user session management,
    and role-based permissions.
    """
    _current_user: Optional[User] = None

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password with PBKDF2-HMAC-SHA256 and salt."""
        salt = secrets.token_hex(16)
        iterations = 100_000
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        return f"pbkdf2:sha256:{iterations}${salt}${key.hex()}"

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """Verify plain password against hashed password."""
        try:
            if not password_hash or not password:
                return False
            parts = password_hash.split("$")
            if len(parts) != 3:
                # Fallback for plain sha256 or legacy
                return hashlib.sha256(password.encode()).hexdigest() == password_hash
            header, salt, stored_key = parts
            _, _, iterations = header.split(":")
            key = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations)
            )
            return secrets.compare_digest(key.hex(), stored_key)
        except Exception:
            return False

    @classmethod
    def authenticate(cls, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate user credentials. Returns (success, user, message).
        """
        username = username.strip().lower()
        with session_scope() as session:
            user = session.query(User).filter(User.username.ilike(username)).first()
            if not user:
                return False, None, "Invalid username or password"
            
            if not user.is_active:
                return False, None, "This user account has been deactivated"
            
            if not cls.verify_password(password, user.password_hash):
                return False, None, "Invalid username or password"
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            session.flush()

            # Detach user representation for session tracking
            user_data = User(
                id=user.id,
                username=user.username,
                password_hash=user.password_hash,
                full_name=user.full_name,
                role=user.role,
                phone=user.phone,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login
            )
            cls._current_user = user_data
            return True, user_data, "Login successful"

    @classmethod
    def get_current_user(cls) -> Optional[User]:
        return cls._current_user

    @classmethod
    def set_current_user(cls, user: Optional[User]):
        cls._current_user = user

    @classmethod
    def logout(cls):
        cls._current_user = None

    @classmethod
    def is_admin(cls) -> bool:
        return cls._current_user is not None and cls._current_user.role == UserRole.ADMIN

    @classmethod
    def is_cashier(cls) -> bool:
        return cls._current_user is not None and cls._current_user.role in [UserRole.ADMIN, UserRole.CASHIER]

    @classmethod
    def is_technician(cls) -> bool:
        return cls._current_user is not None and cls._current_user.role in [UserRole.ADMIN, UserRole.TECHNICIAN]

    @classmethod
    def can_manage_users(cls) -> bool:
        return cls.is_admin()

    @classmethod
    def can_view_financials(cls) -> bool:
        return cls.is_admin()

    @classmethod
    def can_manage_expenses(cls) -> bool:
        # Admin has full access, cashier can view/add
        return cls.is_admin() or (cls._current_user is not None and cls._current_user.role == UserRole.CASHIER)

    @classmethod
    def can_delete_records(cls) -> bool:
        return cls.is_admin()

    # User Management CRUD
    @classmethod
    def list_users(cls, include_inactive: bool = False) -> List[User]:
        with session_scope() as session:
            query = session.query(User)
            if not include_inactive:
                query = query.filter(User.is_active == True)
            users = query.order_by(User.role, User.full_name).all()
            session.expunge_all()
            return users

    @classmethod
    def list_technicians(cls) -> List[User]:
        with session_scope() as session:
            techs = session.query(User).filter(
                User.is_active == True,
                User.role.in_([UserRole.TECHNICIAN, UserRole.ADMIN])
            ).order_by(User.full_name).all()
            session.expunge_all()
            return techs

    @classmethod
    def create_user(cls, username: str, password: str, full_name: str, role: str, phone: str = "") -> Tuple[bool, str]:
        username = username.strip().lower()
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long."
        if not password or len(password) < 4:
            return False, "Password must be at least 4 characters long."
        if not full_name.strip():
            return False, "Full Name is required."

        with session_scope() as session:
            existing = session.query(User).filter(User.username.ilike(username)).first()
            if existing:
                return False, f"Username '{username}' is already taken."

            pw_hash = cls.hash_password(password)
            new_user = User(
                username=username,
                password_hash=pw_hash,
                full_name=full_name.strip(),
                role=role,
                phone=phone.strip() if phone else None,
                is_active=True
            )
            session.add(new_user)
            return True, f"User '{username}' created successfully."

    @classmethod
    def update_user(cls, user_id: int, full_name: str, role: str, phone: str = "", is_active: bool = True, new_password: Optional[str] = None) -> Tuple[bool, str]:
        with session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "User not found."

            user.full_name = full_name.strip()
            user.role = role
            user.phone = phone.strip() if phone else None
            user.is_active = is_active

            if new_password and len(new_password.strip()) >= 4:
                user.password_hash = cls.hash_password(new_password.strip())

            return True, f"User '{user.username}' updated successfully."

    @classmethod
    def ensure_default_users(cls):
        """Seed default admin account if no users exist."""
        with session_scope() as session:
            user_count = session.query(User).count()
            if user_count == 0:
                admin_pw = cls.hash_password("admin123")
                admin = User(
                    username="admin",
                    password_hash=admin_pw,
                    full_name="System Administrator",
                    role=UserRole.ADMIN,
                    phone="0300-0000000",
                    is_active=True
                )
                session.add(admin)
