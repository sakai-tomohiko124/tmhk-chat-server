@echo off
chcp 65001 >nul
echo ========================================
echo Server Connection Diagnostic Tool
echo ========================================
echo.

set SERVER_IP=52.69.241.31
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

echo [2/5] Pinging server...
ping -n 1 %SERVER_IP% >nul 2>&1
if errorlevel 1 (
    echo [!] Cannot reach server (Ping timeout)
    echo.
    echo Possible causes:
    echo - EC2 instance is stopped
    echo - Network connection issue
    echo - Security group does not allow ICMP
    echo.
    echo Next steps:
    echo 1. Check EC2 instance status in AWS Console
    echo 2. https://console.aws.amazon.com/ec2/
) else (
    echo [OK] Server is reachable
)
echo.

echo [3/5] Checking port 22 (SSH)...
powershell -Command "Test-NetConnection %SERVER_IP% -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if errorlevel 1 (
    echo [!] Cannot connect to port 22
    echo.
    echo Possible causes:
    echo - EC2 instance is stopped
    echo - Security group does not allow port 22
    echo - Firewall is blocking SSH
    echo.
    echo Check:
    echo 1. AWS Console -^> EC2 -^> Security Groups
    echo 2. Inbound rules:
    echo    - Type: SSH
    echo    - Port: 22
    echo    - Source: 0.0.0.0/0 or your IP
) else (
    echo [OK] Port 22 is open
)
echo.

echo [4/5] Checking port 5000 (App)...
powershell -Command "Test-NetConnection %SERVER_IP% -Port 5000 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if errorlevel 1 (
    echo [!] Cannot connect to port 5000
    echo (App may not be running)
) else (
    echo [OK] Port 5000 is open
)
echo.

echo [5/5] Testing SSH connection (Timeout: 10 min)...
echo Attempting connection...
ssh -i "%PEM_FILE%" -o ConnectTimeout=600 -o ServerAliveInterval=60 -o BatchMode=yes ubuntu@%SERVER_IP% "echo 'SSH connection successful'" 2>nul
if errorlevel 1 (
    echo [!] SSH connection failed
    echo.
    echo For detailed logs:
    echo ssh -vvv -i "%PEM_FILE%" ubuntu@%SERVER_IP%
    echo.
    echo To connect manually:
    echo ssh -i "%PEM_FILE%" ubuntu@%SERVER_IP%
) else (
    echo [OK] SSH connection successful!
    echo.
    echo Server is working properly.
    echo You can deploy: DEPLOY_NOW.bat
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
