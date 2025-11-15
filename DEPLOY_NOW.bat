@echo off
chcp 65001 >nul
echo ========================================
echo TMHK Chat Server - Deploy
echo ========================================
echo.
echo PEM key location: C:\Users\skyto\ARE\tmhk-chat.pem
echo Server IP: 52.69.241.31
echo.

set PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem
set SERVER=ubuntu@52.69.241.31

echo [1/3] Checking server connection...
ping -n 1 52.69.241.31 >nul 2>&1
if errorlevel 1 (
    echo [!] Cannot connect to server
    echo.
    echo Please check:
    echo - Is your internet connection working?
    echo - Is the AWS EC2 instance running?
    echo - Is SSH (port 22) open in security group?
    echo.
    pause
    exit /b 1
)

echo [OK] Server is reachable
echo.

echo [2/3] Attempting SSH connection...
echo Timeout: 10 minutes
ssh -i "%PEM_FILE%" -o ConnectTimeout=600 -o ServerAliveInterval=60 -o ServerAliveCountMax=10 %SERVER% "echo 'SSH connection successful'" 2>nul
if errorlevel 1 (
    echo [!] SSH connection failed
    echo.
    echo Troubleshooting:
    echo 1. Check EC2 instance status in AWS Console
    echo 2. Verify security group inbound rules
    echo    - Type: SSH
    echo    - Port: 22
    echo    - Source: 0.0.0.0/0 or your IP
    echo 3. Verify SSH key file path is correct
    echo.
    echo To connect manually:
    echo ssh -i "%PEM_FILE%" %SERVER%
    echo.
    pause
    exit /b 1
)

echo [OK] SSH connection successful
echo.

echo [3/3] Deploying application...
ssh -i "%PEM_FILE%" %SERVER% "bash -s" << 'ENDSSH'
set -e

echo "=== Deploy Started ==="

# Navigate to or create project directory
if [ -d "/home/ubuntu/tmhk-chat-server" ]; then
    echo "[1/6] Updating existing project..."
    cd /home/ubuntu/tmhk-chat-server
    git fetch origin
    git reset --hard origin/main
else
    echo "[1/6] Cloning project..."
    cd /home/ubuntu
    git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
    cd tmhk-chat-server
fi

echo "[2/6] Installing Python packages..."
pip3 install -r requirements.txt --quiet

echo "[3/6] Initializing database (if needed)..."
if [ ! -f "chat.db" ]; then
    python3 scripts/init_database.py 2>/dev/null || echo "Skipping database initialization"
fi

echo "[4/6] Checking PM2 status..."
if pm2 describe tmhk-chat > /dev/null 2>&1; then
    echo "[5/6] Restarting application..."
    pm2 restart tmhk-chat
else
    echo "[5/6] Starting application for the first time..."
    pm2 start app.py --name tmhk-chat --interpreter python3
    pm2 save
fi

echo "[6/6] Checking status..."
pm2 status

echo ""
echo "=== Deploy Complete ==="
echo "Application URL: http://52.69.241.31:5000"
echo ""
ENDSSH

if errorlevel 1 (
    echo.
    echo [!] Error occurred during deployment
    echo.
    echo To check logs:
    echo ssh -i "%PEM_FILE%" %SERVER% "pm2 logs tmhk-chat --lines 50"
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Deploy Successful!
echo ========================================
echo.
echo Application URL: http://52.69.241.31:5000
echo.
echo To check logs:
echo ssh -i "%PEM_FILE%" %SERVER% "pm2 logs tmhk-chat --lines 50"
echo.
echo To check status:
echo ssh -i "%PEM_FILE%" %SERVER% "pm2 status"
echo.
pause
