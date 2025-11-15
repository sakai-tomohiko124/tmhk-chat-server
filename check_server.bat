@echo off
echo ========================================
echo サーバー接続診断ツール
echo ========================================
echo.

set SERVER_IP=52.69.241.31
set PEM_FILE=tmhk-chat.pem

echo [1/5] PEM鍵ファイルの確認...
if exist "%PEM_FILE%" (
    echo [OK] PEM鍵ファイルが見つかりました: %PEM_FILE%
) else if exist "C:\Users\skyto\ARE\tmhk-chat.pem" (
    echo [OK] PEM鍵ファイルが見つかりました: C:\Users\skyto\ARE\tmhk-chat.pem
    set PEM_FILE=C:\Users\skyto\ARE\tmhk-chat.pem
) else (
    echo [!] PEM鍵ファイルが見つかりません
    echo 以下の場所を確認してください:
    echo - %CD%\tmhk-chat.pem
    echo - C:\Users\skyto\ARE\tmhk-chat.pem
    pause
    exit /b 1
)
echo.

echo [2/5] サーバーへのPing確認...
ping -n 1 %SERVER_IP% >nul 2>&1
if errorlevel 1 (
    echo [!] サーバーに到達できません（Pingタイムアウト）
    echo.
    echo 考えられる原因:
    echo - EC2インスタンスが停止している
    echo - ネットワーク接続の問題
    echo - セキュリティグループでICMPが許可されていない
    echo.
    echo 次のステップ:
    echo 1. AWSコンソールでEC2インスタンスの状態を確認
    echo 2. https://console.aws.amazon.com/ec2/
) else (
    echo [OK] サーバーに到達できます
)
echo.

echo [3/5] ポート22（SSH）の接続確認...
powershell -Command "Test-NetConnection %SERVER_IP% -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if errorlevel 1 (
    echo [!] ポート22に接続できません
    echo.
    echo 考えられる原因:
    echo - EC2インスタンスが停止している
    echo - セキュリティグループでポート22が開放されていない
    echo - ファイアウォールがSSHをブロックしている
    echo.
    echo 確認事項:
    echo 1. AWSコンソール → EC2 → セキュリティグループ
    echo 2. インバウンドルール:
    echo    - タイプ: SSH
    echo    - ポート: 22
    echo    - ソース: 0.0.0.0/0 または あなたのIP
) else (
    echo [OK] ポート22が開いています
)
echo.

echo [4/5] ポート5000（アプリ）の接続確認...
powershell -Command "Test-NetConnection %SERVER_IP% -Port 5000 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if errorlevel 1 (
    echo [!] ポート5000に接続できません
    echo （アプリが起動していない可能性があります）
) else (
    echo [OK] ポート5000が開いています
)
echo.

echo [5/5] SSH接続テスト（タイムアウト: 10分）...
echo 接続を試行しています...
ssh -i "%PEM_FILE%" -o ConnectTimeout=600 -o ServerAliveInterval=60 -o BatchMode=yes %SERVER_IP% "echo 'SSH接続成功'" 2>nul
if errorlevel 1 (
    echo [!] SSH接続に失敗しました
    echo.
    echo 詳細ログを確認する場合:
    echo ssh -vvv -i "%PEM_FILE%" ubuntu@%SERVER_IP%
    echo.
    echo 手動で接続する場合:
    echo ssh -i "%PEM_FILE%" ubuntu@%SERVER_IP%
) else (
    echo [OK] SSH接続成功！
    echo.
    echo サーバーは正常に動作しています。
    echo デプロイを実行できます: DEPLOY_NOW.bat
)
echo.

echo ========================================
echo 診断完了
echo ========================================
echo.

echo AWSコンソールでEC2を確認:
echo https://console.aws.amazon.com/ec2/
echo.

pause
