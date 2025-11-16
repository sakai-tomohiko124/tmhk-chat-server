@echo off
chcp 65001 >nul
echo ========================================
echo Wait for SSH, then Deploy
echo ========================================

set SERVER_HOST=tmhk-chat.ddns.net
if not "%~1"=="" set SERVER_HOST=%~1
set PEM_FILE=tmhk-chat.pem

REM Resolve PEM path fallback
if not exist "%PEM_FILE%" if exist "C:\Users\skyto\ARE\tmhk-chat.pem" set "PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem"

if not exist "%PEM_FILE%" (
  echo [ERROR] PEM key not found. Place it next to this script or at C:\Users\skyto\ARE\tmhk-chat.pem
  pause
  exit /b 1
)

echo Waiting for %SERVER_HOST%:22 to open (checks every 20s, max 40 tries)...
set /a COUNT=0
:LOOP
set /a COUNT+=1
powershell -Command "if(Test-NetConnection %SERVER_HOST% -Port 22 -InformationLevel Quiet){exit 0}else{exit 1}" >nul 2>&1
if errorlevel 1 (
  if %COUNT% GEQ 40 goto TIMEOUT
  >nul timeout /t 20 /nobreak
  goto LOOP
)

echo [OK] SSH port is open. Starting production deploy...
call "%~dp0DEPLOY_PROD.bat"
exit /b %ERRORLEVEL%

:TIMEOUT
echo [ERROR] Timed out waiting for SSH to open.
echo Please ensure the EC2 instance is running and SG/NACL/route are correct.
pause
exit /b 1
