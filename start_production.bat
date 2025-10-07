@echo off
echo TMHKchat Server - 本番環境起動スクリプト
echo =============================================

REM 環境変数の設定
if "%SECRET_KEY%"=="" (
    echo 警告: SECRET_KEYが設定されていません。セキュリティキーを生成中...
    set SECRET_KEY=tmhkchat_production_key_%RANDOM%%RANDOM%%RANDOM%
)

if "%FLASK_ENV%"=="" (
    set FLASK_ENV=production
)

if "%HOST%"=="" (
    set HOST=0.0.0.0
)

if "%PORT%"=="" (
    set PORT=5000
)

echo 環境設定:
echo - FLASK_ENV: %FLASK_ENV%
echo - HOST: %HOST%
echo - PORT: %PORT%
echo =============================================

REM Pythonの確認
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo エラー: Pythonが見つかりません。Pythonをインストールしてください。
    pause
    exit /b 1
)

REM 必要なパッケージの確認
echo 依存関係を確認中...
python -c "import flask, flask_socketio, sqlite3, requests, bs4" >nul 2>&1
if %errorlevel% neq 0 (
    echo 警告: 必要なパッケージが不足している可能性があります。
    echo requirements.txtからインストールを試行します...
    pip install -r requirements.txt
)

REM 健全性チェックの実行
if exist health_check.py (
    echo 起動前健全性チェックを実行中...
    python health_check.py
    if %errorlevel% neq 0 (
        echo 警告: 健全性チェックで問題が検出されました。
        echo 続行しますか？ [Y/N]
        set /p choice=
        if /i not "%choice%"=="Y" exit /b 1
    )
)

REM サーバーの起動
echo TMHKchat Serverを起動中...
echo Ctrl+C で停止
echo =============================================

if exist production_server.py (
    echo 本番環境用スクリプトで起動中...
    python production_server.py
) else (
    echo 本番環境用スクリプトが見つかりません。通常のスクリプトで起動中...
    python abcd.py
)

if %errorlevel% neq 0 (
    echo エラー: サーバーの起動に失敗しました。
    echo ログを確認してください。
    pause
)

echo サーバーが停止しました。
pause