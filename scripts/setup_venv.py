"""Setup script: upgrade pip and install requirements using the active Python interpreter.

Usage (from repo root, with venv activated):
    python .\scripts\setup_venv.py

This avoids pasting Python into the PowerShell prompt (which treats `import` as a shell command).
"""
import subprocess
import sys

def main():
    # Use the same Python interpreter to run pip
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

if __name__ == '__main__':
    main()
