@echo off
title Digital Library Management System
echo ========================================================
echo   Digital Library Management System (Python Edition)
echo   Starting server at http://localhost:8080 ...
echo ========================================================
echo.

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH. Please install Python 3.8+.
    pause
    exit /b 1
)

python run.py
pause
