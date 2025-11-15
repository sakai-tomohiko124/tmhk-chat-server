#!/bin/bash

# TMHKchat セットアップスクリプト
# このスクリプトは開発環境を自動的にセットアップします

set -e  # エラーが発生したら即座に終了

echo "========================================="
echo "  TMHKchat セットアップスクリプト"
echo "========================================="
echo ""

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Pythonバージョンチェック
echo -e "${YELLOW}[1/8]${NC} Pythonバージョンを確認中..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.12"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}エラー: Python $REQUIRED_VERSION 以上が必要です（現在: $PYTHON_VERSION）${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION 検出${NC}"
echo ""

# 仮想環境の作成
echo -e "${YELLOW}[2/8]${NC} 仮想環境を作成中..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ 仮想環境を作成しました${NC}"
else
    echo -e "${GREEN}✓ 仮想環境は既に存在します${NC}"
fi
echo ""

# 仮想環境の有効化
echo -e "${YELLOW}[3/8]${NC} 仮想環境を有効化中..."
source venv/bin/activate
echo -e "${GREEN}✓ 仮想環境を有効化しました${NC}"
echo ""

# pipのアップグレード
echo -e "${YELLOW}[4/8]${NC} pipをアップグレード中..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ pipをアップグレードしました${NC}"
echo ""

# 依存パッケージのインストール
echo -e "${YELLOW}[5/8]${NC} 依存パッケージをインストール中..."
pip install -r requirements.txt
echo -e "${GREEN}✓ 依存パッケージをインストールしました${NC}"
echo ""

# 環境変数ファイルの設定
echo -e "${YELLOW}[6/8]${NC} 環境変数ファイルを設定中..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ .env ファイルを作成しました${NC}"
    echo -e "${YELLOW}  注意: .env ファイルを編集して、適切な値を設定してください${NC}"
else
    echo -e "${GREEN}✓ .env ファイルは既に存在します${NC}"
fi
echo ""

# 必要なディレクトリの作成
echo -e "${YELLOW}[7/8]${NC} 必要なディレクトリを作成中..."
mkdir -p static/assets/uploads
mkdir -p static/assets/images
mkdir -p logs
mkdir -p templates/tmhk

# .gitkeepファイルを作成（空のディレクトリをGitで管理）
touch static/assets/uploads/.gitkeep
touch static/assets/images/.gitkeep
touch logs/.gitkeep

echo -e "${GREEN}✓ ディレクトリを作成しました${NC}"
echo ""

# データベースの初期化
echo -e "${YELLOW}[8/8]${NC} データベースを初期化中..."
if [ ! -f "chat.db" ]; then
    python3 -c "from app import init_db; init_db()" 2>/dev/null || {
        echo -e "${YELLOW}  注意: データベースの初期化に失敗しました${NC}"
        echo -e "${YELLOW}  app.py の init_db() 関数を確認してください${NC}"
    }
    if [ -f "chat.db" ]; then
        echo -e "${GREEN}✓ データベースを初期化しました${NC}"
    fi
else
    echo -e "${GREEN}✓ データベースは既に存在します${NC}"
fi
echo ""

# セットアップ完了
echo "========================================="
echo -e "${GREEN}  セットアップが完了しました！${NC}"
echo "========================================="
echo ""
echo "次のステップ:"
echo "  1. .env ファイルを編集して適切な値を設定"
echo "  2. アプリケーションを起動:"
echo "     $ source venv/bin/activate"
echo "     $ python app.py"
echo ""
echo "  3. ブラウザで http://localhost:5000 にアクセス"
echo ""
echo "管理者アカウントを作成する場合:"
echo "  $ python scripts/create_admin.py"
echo ""
echo "========================================="
