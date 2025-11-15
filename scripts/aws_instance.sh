#!/bin/bash

################################################################################
# AWS EC2 Instance Management Script for TMHKchat
# 
# このスクリプトはAWS EC2インスタンスの起動・停止・状態確認を行います。
# 
# 前提条件:
#   - AWS CLI v2がインストール済み
#   - AWS認証情報が設定済み (aws configure)
#   - EC2インスタンスID、リージョンが判明している
#
# 使用方法:
#   bash scripts/aws_instance.sh start    # インスタンス起動
#   bash scripts/aws_instance.sh stop     # インスタンス停止
#   bash scripts/aws_instance.sh status   # 状態確認
#   bash scripts/aws_instance.sh ip       # IPアドレス確認
#
################################################################################

set -e

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# AWS設定
AWS_REGION="${AWS_REGION:-ap-northeast-1}"  # 東京リージョン
INSTANCE_ID="${AWS_INSTANCE_ID:-}"          # 環境変数から取得
INSTANCE_NAME="tmhk-chat-server"
PUBLIC_IP="52.69.241.31"  # 既知のElastic IP

# AWS CLIの確認
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLIがインストールされていません"
        echo ""
        echo "インストール方法:"
        echo "  Ubuntu/Debian: curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip' && unzip awscliv2.zip && sudo ./aws/install"
        echo "  macOS: brew install awscli"
        echo "  Windows: https://aws.amazon.com/jp/cli/"
        echo ""
        exit 1
    fi
    
    # AWS認証確認
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS認証情報が設定されていません"
        echo ""
        echo "設定方法:"
        echo "  aws configure"
        echo ""
        echo "必要な情報:"
        echo "  - AWS Access Key ID"
        echo "  - AWS Secret Access Key"
        echo "  - Default region name: ap-northeast-1"
        echo "  - Default output format: json"
        echo ""
        exit 1
    fi
    
    log_success "AWS CLI確認完了"
}

# インスタンスIDの取得
get_instance_id() {
    if [ -n "$INSTANCE_ID" ]; then
        echo "$INSTANCE_ID"
        return
    fi
    
    log_info "インスタンスIDを検索中..."
    
    # タグ名から検索
    local id=$(aws ec2 describe-instances \
        --region "$AWS_REGION" \
        --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running,stopped" \
        --query "Reservations[0].Instances[0].InstanceId" \
        --output text)
    
    if [ "$id" != "None" ] && [ -n "$id" ]; then
        echo "$id"
        return
    fi
    
    # パブリックIPから検索
    id=$(aws ec2 describe-instances \
        --region "$AWS_REGION" \
        --filters "Name=ip-address,Values=$PUBLIC_IP" \
        --query "Reservations[0].Instances[0].InstanceId" \
        --output text)
    
    if [ "$id" != "None" ] && [ -n "$id" ]; then
        echo "$id"
        return
    fi
    
    log_error "インスタンスIDが見つかりません"
    log_warning "環境変数 AWS_INSTANCE_ID を設定するか、スクリプト内で直接指定してください"
    echo ""
    echo "例: export AWS_INSTANCE_ID=i-0123456789abcdef0"
    echo ""
    exit 1
}

# インスタンスの状態確認
get_instance_state() {
    local id=$1
    aws ec2 describe-instances \
        --region "$AWS_REGION" \
        --instance-ids "$id" \
        --query "Reservations[0].Instances[0].State.Name" \
        --output text
}

# インスタンスのIPアドレス取得
get_instance_ip() {
    local id=$1
    local ip=$(aws ec2 describe-instances \
        --region "$AWS_REGION" \
        --instance-ids "$id" \
        --query "Reservations[0].Instances[0].PublicIpAddress" \
        --output text)
    
    if [ "$ip" = "None" ] || [ -z "$ip" ]; then
        echo "未割り当て"
    else
        echo "$ip"
    fi
}

# インスタンス起動
start_instance() {
    local id=$1
    local state=$(get_instance_state "$id")
    
    echo "=================================="
    echo "  EC2インスタンス起動"
    echo "=================================="
    echo ""
    log_info "インスタンスID: $id"
    log_info "現在の状態: $state"
    echo ""
    
    if [ "$state" = "running" ]; then
        log_warning "インスタンスは既に起動しています"
        local ip=$(get_instance_ip "$id")
        echo ""
        echo "パブリックIP: $ip"
        echo "SSH接続: ssh -i tmhk-chat.pem ubuntu@$ip"
        echo ""
        return
    fi
    
    log_info "インスタンスを起動中..."
    aws ec2 start-instances --region "$AWS_REGION" --instance-ids "$id" > /dev/null
    
    log_info "起動を待機中..."
    aws ec2 wait instance-running --region "$AWS_REGION" --instance-ids "$id"
    
    local ip=$(get_instance_ip "$id")
    
    log_success "インスタンスが起動しました"
    echo ""
    echo "パブリックIP: $ip"
    echo "SSH接続: ssh -i tmhk-chat.pem ubuntu@$ip"
    echo ""
    log_warning "SSH接続まで2-3分待つことを推奨します"
    echo ""
}

# インスタンス停止
stop_instance() {
    local id=$1
    local state=$(get_instance_state "$id")
    
    echo "=================================="
    echo "  EC2インスタンス停止"
    echo "=================================="
    echo ""
    log_info "インスタンスID: $id"
    log_info "現在の状態: $state"
    echo ""
    
    if [ "$state" = "stopped" ]; then
        log_warning "インスタンスは既に停止しています"
        return
    fi
    
    log_warning "インスタンスを停止しますか? (y/N): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "キャンセルしました"
        return
    fi
    
    log_info "インスタンスを停止中..."
    aws ec2 stop-instances --region "$AWS_REGION" --instance-ids "$id" > /dev/null
    
    log_info "停止を待機中..."
    aws ec2 wait instance-stopped --region "$AWS_REGION" --instance-ids "$id"
    
    log_success "インスタンスが停止しました"
    echo ""
}

# インスタンス状態表示
show_status() {
    local id=$1
    local state=$(get_instance_state "$id")
    local ip=$(get_instance_ip "$id")
    
    echo "=================================="
    echo "  EC2インスタンス状態"
    echo "=================================="
    echo ""
    echo "インスタンスID: $id"
    echo "リージョン:     $AWS_REGION"
    echo "状態:           $state"
    echo "パブリックIP:   $ip"
    echo ""
    
    if [ "$state" = "running" ]; then
        echo "SSH接続:"
        echo "  ssh -i tmhk-chat.pem ubuntu@$ip"
        echo ""
        echo "アプリケーション:"
        echo "  http://$ip:5000"
        echo ""
    fi
}

# メイン処理
main() {
    local command=${1:-status}
    
    check_aws_cli
    
    local instance_id=$(get_instance_id)
    
    case "$command" in
        start)
            start_instance "$instance_id"
            ;;
        stop)
            stop_instance "$instance_id"
            ;;
        status)
            show_status "$instance_id"
            ;;
        ip)
            local ip=$(get_instance_ip "$instance_id")
            echo "$ip"
            ;;
        *)
            log_error "不明なコマンド: $command"
            echo ""
            echo "使用方法:"
            echo "  $0 start    # インスタンス起動"
            echo "  $0 stop     # インスタンス停止"
            echo "  $0 status   # 状態確認"
            echo "  $0 ip       # IPアドレス確認"
            echo ""
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
