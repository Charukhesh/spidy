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
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"
    downloads_dir = Path.home() / "Downloads"
    target_exe = downloads_dir / "athena.exe"
    spec_path = root_dir / "athena.spec"

    # Clean up previous build artifacts
    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree(build_dir, ignore_errors=True)

    # Write optimized athena.spec with explicit exclusions of unused heavy Anaconda packages
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

datas = [(r'{root_dir / "athena"}', 'athena')]
binaries = []
datas += collect_data_files('ctranslate2')
datas += collect_data_files('faster_whisper')
binaries += collect_dynamic_libs('ctranslate2')

a = Analysis(
    [r'{root_dir / "run_athena.py"}'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'faster_whisper', 'ctranslate2', 'edge_tts', 'mss', 'httpx',
        'PIL', 'winsound', 'psutil', 'sqlite3'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'ctranslate2.converters',
        'torch', 'torchvision', 'torchaudio',
        'tensorflow', 'keras', 'onnxruntime', 'transformers',
        'pandas', 'scipy', 'matplotlib', 'pytest',
        'IPython', 'notebook', 'tornado', 'sympy', 'bokeh',
        'statsmodels', 'seaborn', 'cv2', 'skimage', 'sklearn',
        'nltk', 'astropy', 'botocore', 'sqlalchemy', 'plotly',
        'panel', 'dask', 'distributed', 'numba',
        'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtQml', 'PyQt5.QtQuick', 'PyQt5.QtQuickWidgets',
        'PyQt5.QtPositioning', 'PyQt5.QtPrintSupport',
        'PyQt5.QtBluetooth', 'PyQt5.QtNfc', 'PyQt5.QtSensors'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='athena',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    spec_path.write_text(spec_content, encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path)
    ]

    print("=" * 60)
    print("STARTING ATHENA STANDALONE EXECUTABLE BUILD")
    print("=" * 60)
    print(f"Target: Single-file Windows executable (athena.exe)")
    print(f"Output destination: {target_exe}")
    print("Executing command:", " ".join(cmd))

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
