@echo off
echo ========================================
echo TMHKチャットサーバー - デプロイ実行
echo ========================================
echo.
echo SSH鍵ファイルの場所: C:\Users\skyto\ARE\tmhk-chat.pem
echo サーバーIP: 52.69.241.31
echo.

set PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem
set SERVER=ubuntu@52.69.241.31

echo [1/3] サーバーへの接続を確認中...
ping -n 1 52.69.241.31 >nul 2>&1
if errorlevel 1 (
    echo [!] サーバーに接続できません
    echo.
    echo 以下を確認してください：
    echo - インターネット接続は正常ですか？
    echo - AWSのEC2インスタンスは起動していますか？
    echo - セキュリティグループでSSH（22番ポート）が開放されていますか？
    echo.
    pause
    exit /b 1
)

echo [OK] サーバーに到達できます
echo.

echo [2/3] SSH接続を試行中...
echo タイムアウト: 10分
ssh -i "%PEM_FILE%" -o ConnectTimeout=600 -o ServerAliveInterval=60 -o ServerAliveCountMax=10 %SERVER% "echo 'SSH接続成功'" 2>nul
if errorlevel 1 (
    echo [!] SSH接続に失敗しました
    echo.
    echo トラブルシューティング：
    echo 1. AWSコンソールでEC2インスタンスのステータスを確認
    echo 2. セキュリティグループのインバウンドルールを確認
    echo    - タイプ: SSH
    echo    - ポート: 22
    echo    - ソース: 0.0.0.0/0 または あなたのIP
    echo 3. SSH鍵ファイルのパスが正しいか確認
    echo.
    echo 手動で接続する場合:
    echo ssh -i "%PEM_FILE%" %SERVER%
    echo.
    pause
    exit /b 1
)

echo [OK] SSH接続成功
echo.

echo [3/3] アプリケーションをデプロイ中...
ssh -i "%PEM_FILE%" %SERVER% "bash -s" << 'ENDSSH'
set -e

echo "=== デプロイ開始 ==="

# プロジェクトディレクトリに移動または作成
if [ -d "/home/ubuntu/tmhk-chat-server" ]; then
    echo "[1/6] 既存のプロジェクトを更新..."
    cd /home/ubuntu/tmhk-chat-server
    git fetch origin
    git reset --hard origin/main
else
    echo "[1/6] プロジェクトをクローン..."
    cd /home/ubuntu
    git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
    cd tmhk-chat-server
fi

echo "[2/6] Pythonパッケージをインストール..."
pip3 install -r requirements.txt --quiet

echo "[3/6] データベースを初期化（必要な場合）..."
if [ ! -f "chat.db" ]; then
    python3 scripts/init_database.py 2>/dev/null || echo "データベース初期化スキップ"
fi

echo "[4/6] PM2の状態を確認..."
if pm2 describe tmhk-chat > /dev/null 2>&1; then
    echo "[5/6] アプリケーションを再起動..."
    pm2 restart tmhk-chat
else
    echo "[5/6] アプリケーションを初回起動..."
    pm2 start app.py --name tmhk-chat --interpreter python3
    pm2 save
fi

echo "[6/6] ステータスを確認..."
pm2 status

echo ""
echo "=== デプロイ完了 ==="
echo "アプリケーションURL: http://52.69.241.31:5000"
echo ""
ENDSSH

if errorlevel 1 (
    echo.
    echo [!] デプロイ中にエラーが発生しました
    echo.
    echo ログを確認する場合:
    echo ssh -i "%PEM_FILE%" %SERVER% "pm2 logs tmhk-chat --lines 50"
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo デプロイ成功！
echo ========================================
echo.
echo アプリケーションURL: http://52.69.241.31:5000
echo.
echo ログを確認する場合:
echo ssh -i "%PEM_FILE%" %SERVER% "pm2 logs tmhk-chat --lines 50"
echo.
echo ステータスを確認する場合:
echo ssh -i "%PEM_FILE%" %SERVER% "pm2 status"
echo.
pause
