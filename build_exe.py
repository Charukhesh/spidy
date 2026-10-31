"""Athena Windows Executable Builder using PyInstaller.
Builds athena.exe with all dependencies bundled.
"""

import os
import sys
import subprocess
from pathlib import Path

def build():
    root_dir = Path(__file__).resolve().parent
    main_script = root_dir / "run_athena.py"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name", "athena",
        "--noconsole",
        "--onedir",
        "--clean",
        "--add-data", f"{root_dir / 'athena'}:athena",
        "--hidden-import", "PyQt5",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui",
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "edge_tts",
        "--hidden-import", "pygame",
        "--hidden-import", "mss",
        "--hidden-import", "httpx",
        "--hidden-import", "PIL",
        str(main_script)
    ]

    print("Executing build command:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(root_dir))
    if result.returncode == 0:
        print("\nBuild successful! Application generated at: dist/athena/athena.exe")
    else:
        print(f"\nBuild failed with exit code {result.returncode}")

if __name__ == "__main__":
    build()

