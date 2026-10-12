import sys
import os
import traceback
import logging
from pathlib import Path

# Ensure application package path is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtCore import Qt, QCoreApplication

from app.config import APP_NAME, APP_VERSION, ORG_NAME, get_database_path
from app.database.connection import init_db
from app.ui.styles import GLOBAL_STYLESHEET
from app.ui.dialogs.login_dialog import LoginDialog
from app.ui.main_window import MainWindow

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AppleTechPOS")


def exception_hook(exctype, value, tb):
    """Global exception handler to capture and display errors gracefully."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Uncaught Exception: {err_msg}")
    
    # Try displaying a graphical alert if QApplication exists
    if QApplication.instance():
        QMessageBox.critical(
            None,
            "Application Error",
            f"An unexpected error occurred:\n\n{value}\n\nCheck logs for details."
        )
    sys.__excepthook__(exctype, value, tb)


def main():
    # Install exception hook
    sys.excepthook = exception_hook

    # Configure application metadata
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    QCoreApplication.setOrganizationName(ORG_NAME)

    # Initialize PySide6 Application
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)

    # Initialize SQLite Database with required tables, auto-migrations, and default accounts
    logger.info(f"Initializing database at: {get_database_path()}")
    init_db(seed_sample_data=False)

    # Display Login Dialog
    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.DialogCode.Accepted:
        logger.info("Login cancelled by user. Exiting application.")
        sys.exit(0)

    # Create & display main window
    window = MainWindow()
    window.show()

    logger.info(f"{APP_NAME} v{APP_VERSION} started successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
