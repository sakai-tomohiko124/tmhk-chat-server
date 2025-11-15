@echo off
chcp 65001 >nul
echo ====================================
echo EC2 Instance IP Address Check
echo ====================================
echo.
echo Please check the new IP address in AWS EC2 Console:
echo https://ap-northeast-1.console.aws.amazon.com/ec2/home?region=ap-northeast-1#Instances:
echo.
echo After starting the instance:
echo 1. Check "Public IPv4 address" column
echo 2. If IP changed from 52.69.241.31, update:
echo    - DDNS setting (tmhk-chat.ddns.net)
echo    - DEPLOY_NOW.bat (if using direct IP)
echo.
echo Then test connection:
echo   ssh -i "C:\Users\skyto\ARE\tmhk-chat.pem" ubuntu@[NEW_IP]
echo.
echo Or assign Elastic IP to keep IP address fixed
echo ====================================
pause
