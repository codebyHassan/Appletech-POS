"""
Build script to package Apple Tech Mobile Repair POS into a standalone Windows Executable using PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def build_standalone_exe():
    print("=" * 60)
    print("Building Apple Tech Mobile Repair POS - Standalone Windows EXE")
    print("=" * 60)

    project_root = Path(__file__).resolve().parent
    main_script = project_root / "main.py"
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    # PyInstaller arguments
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=AppleTechPOS",
        "--noconsole",          # GUI mode without black terminal window
        "--onefile",            # Standalone single executable
        "--clean",
        # Hidden imports to guarantee all SQLAlchemy and Qt Print Support plugins are included
        "--hidden-import=sqlalchemy.dialects.sqlite",
        "--hidden-import=PySide6.QtPrintSupport",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        # Main entry script
        str(main_script)
    ]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode == 0:
        exe_path = dist_dir / "AppleTechPOS.exe"
        print("=" * 60)
        print("BUILD SUCCESSFUL!")
        print(f"Standalone Executable: {exe_path}")
        print("Database will be automatically created and stored persistently in %APPDATA%/AppleTechPOS")
        print("=" * 60)
    else:
        print("=" * 60)
        print(f"BUILD FAILED with return code: {result.returncode}")
        print("=" * 60)


if __name__ == "__main__":
    build_standalone_exe()
