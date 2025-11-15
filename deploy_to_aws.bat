@echo off
echo ====================================
echo AWS EC2サーバーへデプロイ
echo ====================================
echo.

REM サーバー情報
set SERVER=ubuntu@52.69.241.31
set KEY=tmhk-chat.pem
set REMOTE_DIR=/home/ubuntu/tmhk-chat-server

echo 1. ローカルの変更をGitHubにプッシュ
git push origin main
if errorlevel 1 (
    echo エラー: Gitプッシュに失敗しました
    pause
    exit /b 1
)

echo.
echo 2. サーバーに接続してアプリケーションを更新
ssh -i "%KEY%" %SERVER% "cd %REMOTE_DIR% && git pull origin main && pip3 install -r requirements.txt && pm2 restart tmhk-chat"

echo.
echo ====================================
echo デプロイ完了！
echo ====================================
echo.
echo サーバーステータスを確認:
ssh -i "%KEY%" %SERVER% "pm2 status"

pause
