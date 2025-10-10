#!/bin/bash

###############################################################################
# ARE - AWS EC2 Deployment Script
# このスクリプトはサーバー上で実行して、GitHubから最新版をデプロイします
###############################################################################

set -e  # エラーが発生したら即座に終了

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# プロジェクトディレクトリ
PROJECT_DIR="/home/ubuntu/are-backend/ARE"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="/home/ubuntu/are-backend/venv"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ARE Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. GitHubから最新版を取得
echo -e "${YELLOW}[1/6] Fetching latest code from GitHub...${NC}"
cd "$PROJECT_DIR"
git fetch origin
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# 2. Python仮想環境を有効化
echo -e "${YELLOW}[2/6] Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# 3. 依存関係を更新
echo -e "${YELLOW}[3/6] Installing/updating dependencies...${NC}"
cd "$BACKEND_DIR"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# 4. データベースマイグレーション
echo -e "${YELLOW}[4/6] Running database migrations...${NC}"
export FLASK_APP=wsgi.py
flask db upgrade
echo -e "${GREEN}✓ Database migrated${NC}"
echo ""

# 5. 静的ファイルの収集（必要な場合）
echo -e "${YELLOW}[5/6] Collecting static files...${NC}"
# もし静的ファイルの収集が必要な場合はここに追加
echo -e "${GREEN}✓ Static files ready${NC}"
echo ""

# 6. PM2でアプリを再起動
echo -e "${YELLOW}[6/6] Restarting application...${NC}"
pm2 restart are-backend
echo -e "${GREEN}✓ Application restarted${NC}"
echo ""

# デプロイ完了
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Check status:"
echo "  pm2 list"
echo "  pm2 logs are-backend"
echo ""
echo "App URLs:"
echo "  HTTP:  http://$(curl -s ifconfig.me)"
echo "  HTTPS: https://your-domain.ddns.net"
echo ""
