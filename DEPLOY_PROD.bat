@echo off
chcp 65001 >nul
echo ========================================
echo TMHK Chat Server - Production Deploy (Nginx + systemd)
echo ========================================
echo.

REM Resolve PEM key path
set "PEM_FILE=%CD%\tmhk-chat.pem"
if exist "C:\Users\skyto\ARE\tmhk-chat.pem" set "PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem"

@echo off
chcp 65001 >nul
echo ========================================
echo TMHK Chat Server - Production Deploy (Nginx + systemd)
echo ========================================
echo.

REM Resolve PEM key path
set "PEM_FILE=%CD%\tmhk-chat.pem"
if exist "C:\Users\skyto\ARE\tmhk-chat.pem" set "PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem"

if not exist "%PEM_FILE%" (
  echo [ERROR] PEM key not found.
  echo Place key at ^"%CD%\tmhk-chat.pem^" or ^"C:\Users\skyto\ARE\tmhk-chat.pem^".
  pause
  exit /b 1
)

REM Host selection: arg1 overrides DDNS (useful if DDNS not updated yet)
set SERVER_HOST=tmhk-chat.ddns.net
if not "%~1"=="" set SERVER_HOST=%~1
set SERVER=ubuntu@%SERVER_HOST%
echo Target host: %SERVER_HOST%

echo [1/3] Connectivity quick check (SSH:22, HTTP:80)...
powershell -Command "($r=Test-NetConnection %SERVER_HOST% -Port 22 -InformationLevel Quiet); if(-not $r){exit 1}" >nul 2>&1
if errorlevel 1 (
  echo [WARN] Port 22 not reachable for %SERVER_HOST%.
  for /f "tokens=*" %%i in ('powershell -Command "try{(Resolve-DnsName %SERVER_HOST% -ErrorAction Stop).IPAddress}catch{''}"') do set RESOLVED_IP=%%i
  if not "%RESOLVED_IP%"=="" echo Resolved IP: %RESOLVED_IP%
  echo.
  echo If DDNS is stale, enter current Public IP.
  set /p NEW_HOST=Enter host/IP (blank to abort and fix AWS): 
  if not "%NEW_HOST%"=="" (
    set SERVER_HOST=%NEW_HOST%
    set SERVER=ubuntu@%SERVER_HOST%
    echo Using override host: %SERVER_HOST%
    powershell -Command "($r=Test-NetConnection %SERVER_HOST% -Port 22 -InformationLevel Quiet); if(-not $r){exit 1}" >nul 2>&1
    if errorlevel 1 (
      echo [ERROR] Port 22 still unreachable for %SERVER_HOST%.
      echo Please verify EC2 status checks, SG/NACL/route, and Public IP.
      pause
      exit /b 1
    ) else (
      echo [OK] SSH port reachable.
    )
  ) else (
    echo Aborting. Please recover EC2 connectivity and rerun.
    pause
    exit /b 1
  )
) else (
  echo [OK] SSH port reachable.
)
powershell -Command "($r=Test-NetConnection %SERVER_HOST% -Port 80 -InformationLevel Quiet); if(-not $r){exit 1}" >nul 2>&1
if errorlevel 1 (
  echo [INFO] Port 80 not yet open (will be enabled by Nginx).
) else (
  echo [OK] HTTP port reachable.
)

echo.

echo [2/3] Sync repository and run server setup (10 min timeout)...
ssh -o ConnectTimeout=600 -o ServerAliveInterval=60 -o ServerAliveCountMax=10 -i "%PEM_FILE%" %SERVER% ^
  "set -e; \
   if [ -d ~/tmhk-chat-server ]; then cd ~/tmhk-chat-server && git fetch origin && git reset --hard origin/main; \
   else git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git ~/tmhk-chat-server && cd ~/tmhk-chat-server; fi; \
   bash scripts/setup_nginx_systemd.sh"
if errorlevel 1 (
  echo.
  echo [ERROR] Remote setup failed. See above logs.
  echo For manual SSH:
  echo   ssh -vvv -i "%PEM_FILE%" %SERVER%
  pause
  exit /b 1
)

echo.

echo [3/3] Verify service and HTTP response...
ssh -o ConnectTimeout=60 -i "%PEM_FILE%" %SERVER% "systemctl is-active tmhk-chat && sudo nginx -t" >nul 2>&1
if errorlevel 1 (
  echo [WARN] Verification encountered issues. Check service logs:
  echo   ssh -i "%PEM_FILE%" %SERVER% "journalctl -u tmhk-chat -n 100 --no-pager"
) else (
  echo [OK] Service active and Nginx config looks good.
)

echo.

echo ========================================
echo Deploy Complete
echo ========================================

echo Open: http://%SERVER_HOST%/
echo Logs: ssh -i "%PEM_FILE%" %SERVER% "journalctl -u tmhk-chat -n 100 --no-pager"
echo Status: ssh -i "%PEM_FILE%" %SERVER% "systemctl status tmhk-chat --no-pager"

pause

