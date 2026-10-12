import os
import sys
from pathlib import Path

# Application Metadata
APP_NAME = "Apple Tech - Mobile Repair POS"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Apple Tech Solutions"
ORG_NAME = "AppleTech"

def get_app_data_dir() -> Path:
    """
    Get the persistent application data directory.
    Stores data in %APPDATA%/AppleTechPOS on Windows, ensuring the database
    is stored outside the EXE bundle and persists through software updates.
    """
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        if app_data:
            base_dir = Path(app_data) / "AppleTechPOS"
        else:
            base_dir = Path.home() / ".appletech_pos"
    else:
        base_dir = Path.home() / ".appletech_pos"

    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "backups").mkdir(parents=True, exist_ok=True)
    return base_dir

def get_database_path() -> Path:
    """Returns the persistent SQLite database path."""
    return get_app_data_dir() / "apple_tech.db"

# Default Shop Configuration
DEFAULT_SHOP_CONFIG = {
    "shop_name": "APPLE TECH MOBILE CARE",
    "shop_tagline": "Professional Smartphone & Tablet Repair Services",
    "shop_phone": "+92 300 1234567 / +92 312 9876543",
    "shop_address": "Shop # 12, 1st Floor, Tech City Plaza, Main Market",
    "shop_url": "",               # Website/URL encoded into the slip barcode
    "currency_symbol": "Rs.",
    "terms_conditions": (
        "1. Physical condition verified upon receiving.\n"
        "2. Not responsible for data loss. Customer must back up data.\n"
        "3. Please present this slip when collecting your device.\n"
        "4. Devices not claimed within 30 days are subject to disposal/storage fee."
    ),
    "thermal_paper_width_mm": 76,  # Standard 3-inch (76mm/80mm) thermal printer
    "auto_cut_after_print": "1",   # Send ESC/POS cut command after each thermal print
}
