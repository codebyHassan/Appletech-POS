import os
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from app.config import get_app_data_dir, get_database_path, DEFAULT_SHOP_CONFIG
from app.database.connection import get_engine, reset_engine_connection, session_scope
from app.database.models import ShopSetting

logger = logging.getLogger(__name__)


class BackupService:
    @staticmethod
    def get_backup_dir() -> Path:
        """Returns the default directory where backups are stored."""
        backup_dir = get_app_data_dir() / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @staticmethod
    def create_backup(destination_file: Optional[str] = None) -> Path:
        """
        Safely create a point-in-time SQLite database backup using SQLite online backup API.
        """
        source_db = get_database_path()
        if not source_db.exists():
            raise FileNotFoundError("Database file does not exist yet. Please perform at least one operation first.")

        if destination_file:
            target_path = Path(destination_file)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = BackupService.get_backup_dir() / f"AppleTech_Backup_{timestamp}.db"

        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Use SQLite Online Backup API for consistency even while app is active
        src_conn = sqlite3.connect(str(source_db))
        dst_conn = sqlite3.connect(str(target_path))
        try:
            with dst_conn:
                src_conn.backup(dst_conn, pages=100)
            logger.info(f"Database backup successfully created at: {target_path}")
            return target_path
        finally:
            dst_conn.close()
            src_conn.close()

    @staticmethod
    def restore_backup(backup_file_path: str) -> bool:
        """
        Restore the database from a backup file after verifying SQLite integrity.
        """
        backup_path = Path(backup_file_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found at: {backup_file_path}")

        # Step 1: Verify backup file integrity
        try:
            test_conn = sqlite3.connect(str(backup_path))
            cursor = test_conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            test_conn.close()
            if not result or result[0] != "ok":
                raise ValueError(f"Backup file integrity check failed: {result}")
        except Exception as e:
            raise ValueError(f"Corrupted or invalid database backup file: {e}")

        # Step 2: Release SQLAlchemy engine connections
        reset_engine_connection()

        # Step 3: Replace current database file
        current_db = get_database_path()
        temp_bak = current_db.with_suffix(".db.prev_bak")
        try:
            if current_db.exists():
                shutil.copy2(current_db, temp_bak)

            # Copy backup to current database
            shutil.copy2(backup_path, current_db)

            # Remove temp backup on success
            if temp_bak.exists():
                temp_bak.unlink(missing_ok=True)

            logger.info(f"Database successfully restored from {backup_file_path}")
            return True
        except Exception as e:
            # Revert if failed
            if temp_bak.exists():
                shutil.copy2(temp_bak, current_db)
                temp_bak.unlink(missing_ok=True)
            logger.error(f"Failed to restore database: {e}")
            raise

    @staticmethod
    def list_backups() -> List[Dict[str, str]]:
        """List all available backup files in the default backup folder."""
        backup_dir = BackupService.get_backup_dir()
        backups = []
        for file in sorted(backup_dir.glob("*.db"), key=os.path.getmtime, reverse=True):
            stat = file.stat()
            backups.append({
                "filename": file.name,
                "filepath": str(file.resolve()),
                "size_kb": f"{stat.st_size / 1024:.1f} KB",
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        return backups


class SettingsService:
    @staticmethod
    def get_all_settings() -> Dict[str, str]:
        """Fetch all settings from database with fallbacks to defaults."""
        settings = dict(DEFAULT_SHOP_CONFIG)
        try:
            with session_scope() as session:
                rows = session.query(ShopSetting).all()
                for row in rows:
                    settings[row.key] = row.value
        except Exception as e:
            logger.warning(f"Could not load settings from DB: {e}")
        return settings

    @staticmethod
    def save_settings(settings_dict: Dict[str, Any]):
        """Persist settings to database."""
        with session_scope() as session:
            for key, val in settings_dict.items():
                setting = session.get(ShopSetting, key)
                if setting:
                    setting.value = str(val)
                else:
                    session.add(ShopSetting(key=key, value=str(val)))
