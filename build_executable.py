#!/usr/bin/env python3
"""
Build standalone executable for Personal Task Tracker

This script creates a standalone executable that can run without Python installed.
Requires PyInstaller: pip install pyinstaller
"""

import subprocess
import sys
import os
import platform

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

def build_executable():
    """Build the executable"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, 'personal_tracker.py')

    # PyInstaller options
    options = [
        'pyinstaller',
        '--onefile',           # Single executable file
        '--windowed',          # No console window (GUI app)
        '--name=PersonalTracker',  # Output name
        f'--distpath={os.path.join(script_dir, "dist")}',
        f'--workpath={os.path.join(script_dir, "build")}',
        f'--specpath={script_dir}',
        '--clean',             # Clean build
    ]

    # Add icon if available (optional)
    icon_path = os.path.join(script_dir, 'icon.ico')
    if os.path.exists(icon_path):
        options.append(f'--icon={icon_path}')

    options.append(main_script)

    print("Building executable...")
    print(f"Platform: {platform.system()}")
    print(f"Python version: {sys.version}")
    print()

    subprocess.check_call(options)

    # Print success message
    if platform.system() == 'Windows':
        exe_name = 'PersonalTracker.exe'
    else:
        exe_name = 'PersonalTracker'

    exe_path = os.path.join(script_dir, 'dist', exe_name)

    print()
    print("=" * 50)
    print("BUILD SUCCESSFUL!")
    print("=" * 50)
    print(f"Executable created at: {exe_path}")
    print()
    print("You can now run the application directly without Python!")

def main():
    print("Personal Task Tracker - Executable Builder")
    print("=" * 50)
    print()

    # Check/install PyInstaller
    if not check_pyinstaller():
        print("PyInstaller not found.")
        response = input("Would you like to install it? (y/n): ").lower()
        if response == 'y':
            install_pyinstaller()
        else:
            print("Cannot build without PyInstaller. Exiting.")
            sys.exit(1)

    # Build
    try:
        build_executable()
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
