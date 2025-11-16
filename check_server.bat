@echo off
chcp 65001 >nul
echo ========================================
echo Server Connection Diagnostic Tool (DDNS)
echo ========================================
echo.

set SERVER_HOST=tmhk-chat.ddns.net
set PEM_FILE=tmhk-chat.pem

echo [1/5] Checking PEM key file...
if exist "%PEM_FILE%" (
    echo [OK] PEM key file found: %PEM_FILE%
) else if exist "C:\Users\skyto\ARE\tmhk-chat.pem" (
    echo [OK] PEM key file found: C:\Users\skyto\ARE\tmhk-chat.pem
    set PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem
) else (
    echo [!] PEM key file not found
    echo Please check these locations:
    echo - %CD%\tmhk-chat.pem
    echo - C:\Users\skyto\ARE\tmhk-chat.pem
    pause
    exit /b 1
)
echo.

echo [2/5] Resolving DNS...
powershell -Command "try{(Resolve-DnsName %SERVER_HOST% -ErrorAction Stop).IPAddress; exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 (
    echo [!] DNS resolution failed for %SERVER_HOST%
    echo Check DDNS settings.
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('powershell -Command "(Resolve-DnsName %SERVER_HOST% | Select-Object -First 1).IPAddress"') do set SERVER_IP=%%i
    echo [OK] %SERVER_HOST% -> %SERVER_IP%
)
echo.

echo [3/5] Checking port 22 (SSH)...
powershell -Command "Test-NetConnection %SERVER_HOST% -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if errorlevel 1 (
    echo [!] Cannot connect to port 22
) else (
    echo [OK] Port 22 is open
)
echo.

echo [4/5] Checking port 80 (HTTP via Nginx)...
powershell -Command "Test-NetConnection %SERVER_HOST% -Port 80 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if errorlevel 1 (
    echo [!] Port 80 closed (Nginx not reachable yet)
) else (
    echo [OK] Port 80 is open
)
echo.

echo [5/5] Testing SSH connection (Timeout: 10 min)...
echo Attempting connection...
ssh -i "%PEM_FILE%" -o ConnectTimeout=600 -o ServerAliveInterval=60 -o BatchMode=yes ubuntu@%SERVER_HOST% "echo 'SSH connection successful'" 2>nul
if errorlevel 1 (
    echo [!] SSH connection failed
    echo For detailed logs:
    echo   ssh -vvv -i "%PEM_FILE%" ubuntu@%SERVER_HOST%
) else (
    echo [OK] SSH connection successful!
    echo You can deploy: DEPLOY_PROD.bat
)
echo.

echo ========================================
echo Diagnostic Complete
echo ========================================
echo.
echo Check EC2 in AWS Console:
echo https://console.aws.amazon.com/ec2/
echo.

pause
