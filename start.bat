@echo off
:: IIT (ISM) Dhanbad - One-Click Launcher for Windows
title IIT (ISM) Dhanbad - Exam Paper Generator
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python run.py
pause
