"""Athena Windows Executable Builder using PyInstaller.
Builds standalone single-file athena.exe with all dependencies bundled
and deploys it to the user's Downloads folder.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def build():
    root_dir = Path(__file__).resolve().parent
    main_script = root_dir / "run_athena.py"
    dist_dir = root_dir / "dist"
    downloads_dir = Path.home() / "Downloads"
    target_exe = downloads_dir / "athena.exe"

    # Clean up previous build artifacts
    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree(root_dir / "build", ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name", "athena",
        "--noconsole",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--add-data", f"{root_dir / 'athena'};athena",
        "--collect-all", "faster_whisper",
        "--collect-all", "ctranslate2",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pytest",
        "--exclude-module", "IPython",
        "--exclude-module", "notebook",
        "--exclude-module", "tornado",
        "--exclude-module", "sympy",
        "--exclude-module", "bokeh",
        "--exclude-module", "statsmodels",
        "--exclude-module", "seaborn",
        "--hidden-import", "PyQt5",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui",
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "edge_tts",
        "--hidden-import", "mss",
        "--hidden-import", "httpx",
        "--hidden-import", "PIL",
        "--hidden-import", "winsound",
        "--hidden-import", "psutil",
        str(main_script)
    ]

    print("=" * 60)
    print("STARTING ATHENA STANDALONE EXECUTABLE BUILD")
    print("=" * 60)
    print(f"Target: Single-file Windows executable (athena.exe)")
    print(f"Output destination: {target_exe}")
    print("Executing command:", " ".join(cmd[:10]), "...")

    result = subprocess.run(cmd, cwd=str(root_dir))
    if result.returncode != 0:
        print(f"\n[ERROR] Build failed with exit code {result.returncode}")
        return False

    built_exe = dist_dir / "athena.exe"
    if not built_exe.exists():
        print(f"\n[ERROR] Built executable not found at: {built_exe}")
        return False

    size_mb = built_exe.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Generated athena.exe ({size_mb:.2f} MB)")

    # Copy to user's Downloads folder
    print(f"Copying to Downloads folder: {target_exe}")
    try:
        shutil.copy2(built_exe, target_exe)
        copied_size_mb = target_exe.stat().st_size / (1024 * 1024)
        print(f"[VERIFIED] Successfully placed athena.exe ({copied_size_mb:.2f} MB) in {downloads_dir}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to copy athena.exe to Downloads: {e}")
        return False

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
