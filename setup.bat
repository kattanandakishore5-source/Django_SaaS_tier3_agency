@echo off
REM Django Starter Setup Script for Windows

setlocal enabledelayedexpansion

echo.
echo 🚀 Django Starter Setup
echo =========================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo ✓ .env created
    echo.
) else (
    echo ✓ .env already exists
    echo.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.12+
    exit /b 1
)

echo Installing Python dependencies...
pip install -r requirements.txt
echo ✓ Dependencies installed
echo.

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Running migrations...
python manage.py migrate
echo ✓ Migrations completed
echo.

echo Creating demo data...
python manage.py create_demo_data
echo ✓ Demo data created
echo.

echo Collecting static files...
python manage.py collectstatic --noinput
echo ✓ Static files collected
echo.

echo.
echo ✓ Setup Complete!
echo.
echo Next steps:
echo 1. Start the development server:
echo    python manage.py runserver
echo.
echo 2. In another terminal, start Celery:
echo    celery -A config worker -l info
echo.
echo 3. In another terminal, start Celery Beat:
echo    celery -A config beat -l info
echo.
echo Demo credentials:
echo Email: owner@example.com
echo Password: password123
echo.
echo URLs:
echo Dashboard: http://localhost:8000/dashboard/
echo Admin: http://localhost:8000/admin/
echo API Docs: http://localhost:8000/api/docs/
echo.
pause
