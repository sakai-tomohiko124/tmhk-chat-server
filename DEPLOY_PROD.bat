@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo ========================================
echo TMHK Chat Server - Production Deploy
echo ========================================
echo.

REM Resolve PEM key path
set "PEM_FILE=%CD%\tmhk-chat.pem"
if exist "C:\Users\skyto\ARE\tmhk-chat.pem" set "PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem"

if not exist "%PEM_FILE%" (
  echo [ERROR] PEM key not found.
  pause
  exit /b 1
)

REM Host selection: arg1 overrides DDNS
set SERVER_HOST=tmhk-chat.ddns.net
if not "%~1"=="" set SERVER_HOST=%~1
set SERVER=ubuntu@!SERVER_HOST!
echo Target host: !SERVER_HOST!
echo.

echo [1/3] Checking SSH connectivity...
powershell -Command "Test-NetConnection !SERVER_HOST! -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if errorlevel 1 (
  echo [WARN] Port 22 not reachable for !SERVER_HOST!.
  echo.
  echo If DDNS is stale, enter current Public IP from AWS Console.
  set /p NEW_HOST=Enter host/IP or press Enter to abort: 
  if not "!NEW_HOST!"=="" (
    set SERVER_HOST=!NEW_HOST!
    set SERVER=ubuntu@!SERVER_HOST!
    echo Retrying with: !SERVER_HOST!
    powershell -Command "Test-NetConnection !SERVER_HOST! -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
    if errorlevel 1 (
      echo [ERROR] Port 22 still unreachable.
      pause
      exit /b 1
    )
    echo [OK] SSH port reachable.
  ) else (
    echo Aborting. Please fix AWS networking and rerun.
    pause
    exit /b 1
  )
) else (
  echo [OK] SSH port reachable.
)
echo.

echo [2/3] Deploying to server (timeout: 10 min)...
ssh -o ConnectTimeout=600 -o ServerAliveInterval=60 -o ServerAliveCountMax=10 -i "%PEM_FILE%" !SERVER! "set -e; if [ -d ~/tmhk-chat-server ]; then cd ~/tmhk-chat-server && git fetch origin && git reset --hard origin/main; else git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git ~/tmhk-chat-server && cd ~/tmhk-chat-server; fi; bash scripts/setup_nginx_systemd.sh"
if errorlevel 1 (
  echo.
  echo [ERROR] Remote setup failed.
  pause
  exit /b 1
)
echo.

echo [3/3] Verifying service...
ssh -o ConnectTimeout=60 -i "%PEM_FILE%" !SERVER! "systemctl is-active tmhk-chat" >nul 2>&1
if errorlevel 1 (
  echo [WARN] Service may not be active. Check logs.
) else (
  echo [OK] Service active.
)
echo.

echo ========================================
echo Deploy Complete
echo ========================================
echo.
echo Open: http://!SERVER_HOST!/
echo.
echo Logs:
echo   ssh -i "%PEM_FILE%" !SERVER! "journalctl -u tmhk-chat -n 100 --no-pager"
echo.
pause

