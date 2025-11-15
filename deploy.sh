#!/bin/bash

# TMHKchat デプロイスクリプト (AWS/Linux用)
# このスクリプトは本番環境へのデプロイを自動化します

set -e

echo "========================================="
echo "  TMHKchat デプロイスクリプト"
echo "========================================="
echo ""

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 設定
PROJECT_DIR="/home/ubuntu/tmhk-chat-server"
VENV_DIR="$PROJECT_DIR/venv"
APP_NAME="tmhk-chat"

# 現在のディレクトリに移動
cd $PROJECT_DIR

# Gitから最新コードを取得
echo -e "${YELLOW}[1/6]${NC} GitHubから最新コードを取得中..."
git fetch origin
git pull origin main
echo -e "${GREEN}✓ 最新コードを取得しました${NC}"
echo ""

# 仮想環境を有効化
echo -e "${YELLOW}[2/6]${NC} 仮想環境を有効化中..."
source $VENV_DIR/bin/activate
echo -e "${GREEN}✓ 仮想環境を有効化しました${NC}"
echo ""

# 依存パッケージを更新
echo -e "${YELLOW}[3/6]${NC} 依存パッケージを更新中..."
pip install -r requirements.txt --upgrade
echo -e "${GREEN}✓ 依存パッケージを更新しました${NC}"
echo ""

# データベースのバックアップ
echo -e "${YELLOW}[4/6]${NC} データベースをバックアップ中..."
if [ -f "chat.db" ]; then
    BACKUP_FILE="chat_backup_$(date +%Y%m%d_%H%M%S).db"
    cp chat.db $BACKUP_FILE
    echo -e "${GREEN}✓ バックアップを作成しました: $BACKUP_FILE${NC}"
else
    echo -e "${YELLOW}  データベースファイルが見つかりません${NC}"
fi
echo ""

# 静的ファイルの収集（必要に応じて）
echo -e "${YELLOW}[5/6]${NC} 静的ファイルを準備中..."
# webpack等のビルドが必要な場合はここに追加
echo -e "${GREEN}✓ 静的ファイルの準備完了${NC}"
echo ""

# アプリケーションを再起動
echo -e "${YELLOW}[6/6]${NC} アプリケーションを再起動中..."
pm2 restart $APP_NAME

# 起動確認
sleep 2
pm2 status $APP_NAME

echo ""
echo "========================================="
echo -e "${GREEN}  デプロイが完了しました！${NC}"
echo "========================================="
echo ""
echo "アプリケーションの状態:"
pm2 list
echo ""
echo "ログを確認する場合:"
echo "  $ pm2 logs $APP_NAME"
echo ""
echo "========================================="
