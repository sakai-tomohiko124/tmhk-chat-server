@echo off
REM TMHKchat セットアップスクリプト (Windows版)
REM このスクリプトは開発環境を自動的にセットアップします

echo =========================================
echo   TMHKchat セットアップスクリプト
echo =========================================
echo.

REM Pythonバージョンチェック
echo [1/8] Pythonバージョンを確認中...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo エラー: Pythonがインストールされていません
    echo https://www.python.org/downloads/ からPython 3.12以上をインストールしてください
    pause
    exit /b 1
)

python --version
echo.

REM 仮想環境の作成
echo [2/8] 仮想環境を作成中...
if not exist "venv" (
    python -m venv venv
    echo ✓ 仮想環境を作成しました
) else (
    echo ✓ 仮想環境は既に存在します
)
echo.

REM 仮想環境の有効化
echo [3/8] 仮想環境を有効化中...
call venv\Scripts\activate.bat
echo ✓ 仮想環境を有効化しました
echo.

REM pipのアップグレード
echo [4/8] pipをアップグレード中...
python -m pip install --upgrade pip >nul 2>&1
echo ✓ pipをアップグレードしました
echo.

REM 依存パッケージのインストール
echo [5/8] 依存パッケージをインストール中...
echo   これには数分かかる場合があります...
pip install -r requirements.txt
echo ✓ 依存パッケージをインストールしました
echo.

REM 環境変数ファイルの設定
echo [6/8] 環境変数ファイルを設定中...
if not exist ".env" (
    copy .env.example .env >nul
    echo ✓ .env ファイルを作成しました
    echo   注意: .env ファイルを編集して、適切な値を設定してください
) else (
    echo ✓ .env ファイルは既に存在します
)
echo.

REM 必要なディレクトリの作成
echo [7/8] 必要なディレクトリを作成中...
if not exist "static\assets\uploads" mkdir static\assets\uploads
if not exist "static\assets\images" mkdir static\assets\images
if not exist "logs" mkdir logs
if not exist "templates\tmhk" mkdir templates\tmhk

REM .gitkeepファイルを作成
type nul > static\assets\uploads\.gitkeep
type nul > static\assets\images\.gitkeep
type nul > logs\.gitkeep

echo ✓ ディレクトリを作成しました
echo.

REM データベースの初期化
echo [8/8] データベースを初期化中...
if not exist "chat.db" (
    python -c "from app import init_db; init_db()" 2>nul
    if exist "chat.db" (
        echo ✓ データベースを初期化しました
    ) else (
        echo   注意: データベースの初期化に失敗しました
        echo   app.py の init_db^(^) 関数を確認してください
    )
) else (
    echo ✓ データベースは既に存在します
)
echo.

REM セットアップ完了
echo =========================================
echo   セットアップが完了しました！
echo =========================================
echo.
echo 次のステップ:
echo   1. .env ファイルを編集して適切な値を設定
echo   2. アプリケーションを起動:
echo      ^> venv\Scripts\activate
echo      ^> python app.py
echo.
echo   3. ブラウザで http://localhost:5000 にアクセス
echo.
echo 管理者アカウントを作成する場合:
echo   ^> python scripts\create_admin.py
echo.
echo =========================================
echo.
pause
