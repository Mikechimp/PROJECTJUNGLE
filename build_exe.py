#!/usr/bin/env python3
"""Build PROJECTJUNGLE as a standalone executable.

Requirements:
    pip install pyinstaller

Usage:
    python build_exe.py

This will create:
    dist/PROJECTJUNGLE.exe  (Windows)
    dist/PROJECTJUNGLE      (macOS/Linux)
"""

import subprocess
import sys
import os


def build():
    """Build the executable using PyInstaller."""
    # Check PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                      # Single executable
        "--windowed",                     # No console window (GUI app)
        "--name", "PROJECTJUNGLE",        # Output name
        "--add-data", f"jungle{os.pathsep}jungle",  # Include package
        "--hidden-import", "jungle",
        "--hidden-import", "jungle.core",
        "--hidden-import", "jungle.core.theory",
        "--hidden-import", "jungle.core.rhythm",
        "--hidden-import", "jungle.core.midi_export",
        "--hidden-import", "jungle.generators",
        "--hidden-import", "jungle.generators.drums",
        "--hidden-import", "jungle.generators.riffs",
        "--hidden-import", "jungle.generators.bass",
        "--hidden-import", "jungle.generators.session",
        "--hidden-import", "jungle.vibes",
        "--hidden-import", "jungle.vibes.metal",
        "--hidden-import", "jungle.gui",
        "--hidden-import", "jungle.gui.app",
        "jungle_gui.py",                  # Entry point
    ]

    print("Building PROJECTJUNGLE executable...")
    print(f"Command: {' '.join(cmd)}\n")
    subprocess.check_call(cmd)

    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print(f"Executable: dist/PROJECTJUNGLE{'.exe' if sys.platform == 'win32' else ''}")
    print("=" * 60)


if __name__ == "__main__":
    build()
