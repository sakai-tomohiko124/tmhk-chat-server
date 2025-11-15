#!/bin/bash

################################################################################
# No-IP Dynamic DNS Setup Script for TMHKchat
# 
# このスクリプトはNo-IP 2.1.9をAWS EC2サーバーにインストール・設定します。
# 
# 前提条件:
#   - No-IPアカウント登録済み (https://www.noip.com/)
#   - ホスト名作成済み (例: tmhkchat.ddns.net)
#   - AWS EC2インスタンスがパブリックIPを持つ (52.69.241.31)
#
# 実行方法:
#   sudo bash scripts/setup_noip.sh
#
# 設定後の確認:
#   sudo /usr/local/bin/noip2 -S
#
################################################################################

set -e  # エラー時に停止

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# rootチェック
if [ "$EUID" -ne 0 ]; then 
    log_error "このスクリプトはroot権限で実行してください"
    log_info "実行方法: sudo bash scripts/setup_noip.sh"
    exit 1
fi

echo "=================================="
echo "  No-IP 2.1.9 セットアップ"
echo "=================================="
echo ""

# ステップ1: 必要なパッケージのインストール
log_info "[1/7] 必要なパッケージをインストール中..."
apt-get update -qq
apt-get install -y -qq build-essential wget make gcc > /dev/null 2>&1
log_success "パッケージインストール完了"

# ステップ2: No-IPクライアントのダウンロード
log_info "[2/7] No-IP 2.1.9 クライアントをダウンロード中..."
cd /tmp
if [ -f "noip-duc-linux.tar.gz" ]; then
    rm noip-duc-linux.tar.gz
fi
wget -q http://www.noip.com/client/linux/noip-duc-linux.tar.gz
log_success "ダウンロード完了"

# ステップ3: 解凍
log_info "[3/7] アーカイブを解凍中..."
tar xzf noip-duc-linux.tar.gz
cd noip-2.1.9-1
log_success "解凍完了"

# ステップ4: コンパイル
log_info "[4/7] No-IPクライアントをコンパイル中..."
make > /dev/null 2>&1
log_success "コンパイル完了"

# ステップ5: インストール
log_info "[5/7] No-IPクライアントをインストール中..."
make install > /dev/null 2>&1
log_success "インストール完了: /usr/local/bin/noip2"

# ステップ6: 設定ファイルの作成
log_info "[6/7] No-IP設定を開始します"
echo ""
log_warning "以下の情報を入力してください:"
echo "  - No-IPアカウントのメールアドレス"
echo "  - No-IPアカウントのパスワード"
echo "  - 更新するホスト名を選択 (例: tmhkchat.ddns.net)"
echo "  - 更新間隔 (推奨: 30分 = デフォルト)"
echo ""

# 設定実行
/usr/local/bin/noip2 -C

log_success "設定ファイル作成完了: /usr/local/etc/no-ip2.conf"

# ステップ7: systemdサービスの作成
log_info "[7/7] systemdサービスを作成中..."

cat > /etc/systemd/system/noip2.service << 'EOF'
[Unit]
Description=No-IP Dynamic DNS Update Client
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/noip2
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

# サービスの有効化と起動
systemctl daemon-reload
systemctl enable noip2.service
systemctl start noip2.service

log_success "systemdサービス作成・起動完了"

# クリーンアップ
cd /tmp
rm -rf noip-2.1.9-1 noip-duc-linux.tar.gz

echo ""
echo "=================================="
echo "  セットアップ完了"
echo "=================================="
echo ""
log_success "No-IPクライアントが正常にインストール・起動されました"
echo ""
echo "確認コマンド:"
echo "  サービス状態:  sudo systemctl status noip2"
echo "  No-IP状態:     sudo /usr/local/bin/noip2 -S"
echo "  ログ確認:      sudo journalctl -u noip2 -f"
echo ""
echo "管理コマンド:"
echo "  再起動:        sudo systemctl restart noip2"
echo "  停止:          sudo systemctl stop noip2"
echo "  設定変更:      sudo /usr/local/bin/noip2 -C"
echo ""
echo "IP更新の確認:"
echo "  https://www.noip.com/members/dns/ でホスト名のIPアドレスを確認"
echo "  現在のパブリックIP: $(curl -s ifconfig.me)"
echo ""
log_warning "注意: No-IPの無料アカウントは30日ごとに確認が必要です"
echo ""
