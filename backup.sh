#!/bin/bash

# TMHKchat バックアップスクリプト
# このスクリプトはデータベースとアップロードファイルをバックアップします

set -e

echo "========================================="
echo "  TMHKchat バックアップスクリプト"
echo "========================================="
echo ""

# 設定
BACKUP_DIR="/home/ubuntu/backups"
PROJECT_DIR="/home/ubuntu/tmhk-chat-server"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# バックアップディレクトリの作成
echo -e "${YELLOW}[1/4]${NC} バックアップディレクトリを準備中..."
mkdir -p $BACKUP_DIR
echo -e "${GREEN}✓ ディレクトリ準備完了${NC}"
echo ""

# データベースのバックアップ
echo -e "${YELLOW}[2/4]${NC} データベースをバックアップ中..."
if [ -f "$PROJECT_DIR/chat.db" ]; then
    cp $PROJECT_DIR/chat.db $BACKUP_DIR/chat_$DATE.db
    DB_SIZE=$(du -h $BACKUP_DIR/chat_$DATE.db | cut -f1)
    echo -e "${GREEN}✓ データベースバックアップ完了 ($DB_SIZE)${NC}"
else
    echo -e "${YELLOW}  データベースファイルが見つかりません${NC}"
fi
echo ""

# アップロードファイルのバックアップ
echo -e "${YELLOW}[3/4]${NC} アップロードファイルをバックアップ中..."
if [ -d "$PROJECT_DIR/static/assets/uploads" ]; then
    tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C $PROJECT_DIR static/assets/uploads
    UPLOAD_SIZE=$(du -h $BACKUP_DIR/uploads_$DATE.tar.gz | cut -f1)
    echo -e "${GREEN}✓ アップロードファイルバックアップ完了 ($UPLOAD_SIZE)${NC}"
else
    echo -e "${YELLOW}  アップロードディレクトリが見つかりません${NC}"
fi
echo ""

# 古いバックアップの削除
echo -e "${YELLOW}[4/4]${NC} 古いバックアップを削除中 (${RETENTION_DAYS}日以前)..."
DELETED_DB=$(find $BACKUP_DIR -name "chat_*.db" -mtime +$RETENTION_DAYS -delete -print | wc -l)
DELETED_UPLOADS=$(find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
echo -e "${GREEN}✓ 削除されたバックアップ: データベース ${DELETED_DB}個, アップロード ${DELETED_UPLOADS}個${NC}"
echo ""

# バックアップ一覧
echo "========================================="
echo -e "${GREEN}  バックアップが完了しました！${NC}"
echo "========================================="
echo ""
echo "最新のバックアップ:"
ls -lh $BACKUP_DIR/*_$DATE.* 2>/dev/null || echo "  (なし)"
echo ""
echo "全バックアップファイル数:"
echo "  データベース: $(ls $BACKUP_DIR/chat_*.db 2>/dev/null | wc -l)個"
echo "  アップロード: $(ls $BACKUP_DIR/uploads_*.tar.gz 2>/dev/null | wc -l)個"
echo ""
echo "バックアップディレクトリの合計サイズ:"
du -sh $BACKUP_DIR
echo ""
echo "========================================="
