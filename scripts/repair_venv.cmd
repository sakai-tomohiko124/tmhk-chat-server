@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM tmhk-chat-server: venv repair + deps install (CMD only)
REM Run from repo root or any folder.
REM ============================================================

REM Move to repo root (this file is in scripts\)
cd /d "%~dp0.."

echo [1/6] Repo root: %cd%

REM Optional: show current git status (if git installed)
git --version >nul 2>&1
if %errorlevel%==0 (
  echo.
  echo --- git status ---
  git status -sb
  echo --------------
) else (
  echo (git not found - skipping git status)
)

echo.
echo [2/6] Removing existing .venv ...
if exist ".venv" (
  rmdir /s /q ".venv"
)

echo.
echo [3/6] Creating new venv ...
REM Prefer Python Launcher (py). If 3.13 not available, fall back.
py -3.13 -m venv .venv >nul 2>&1
if %errorlevel%==0 goto venv_ok

py -3 -m venv .venv >nul 2>&1
if %errorlevel%==0 goto venv_ok

py -m venv .venv >nul 2>&1
if %errorlevel%==0 goto venv_ok

python -m venv .venv
if not %errorlevel%==0 (
  echo ERROR: Could not create venv. Install Python and try again.
  exit /b 1
)

:venv_ok

echo.
echo [4/6] Bootstrapping pip ...
".venv\Scripts\python.exe" -m ensurepip --upgrade
if not %errorlevel%==0 (
  echo ERROR: ensurepip failed.
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if not %errorlevel%==0 (
  echo ERROR: pip upgrade failed.
  exit /b 1
)

echo.
echo [5/6] Installing requirements ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if not %errorlevel%==0 (
  echo ERROR: requirements install failed.
  exit /b 1
)

echo.
echo [6/6] Quick import check ...
".venv\Scripts\python.exe" -c "import flask, flask_socketio, redis; import openai; print('OK: core imports')"
if not %errorlevel%==0 (
  echo ERROR: Import check failed.
  exit /b 1
)

echo.
echo DONE.
echo Next: run server
echo   .venv\Scripts\python.exe app.py
exit /b 0
