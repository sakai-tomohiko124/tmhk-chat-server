#!/bin/bash

###############################################################################
# ARE - AWS EC2 Initial Setup Script
# EC2インスタンス初回セットアップ用スクリプト
# 使い方: chmod +x setup_ec2.sh && ./setup_ec2.sh
###############################################################################

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ARE - AWS EC2 Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. システムパッケージの更新
echo -e "${YELLOW}[1/8] Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y
echo -e "${GREEN}✓ System updated${NC}"
echo ""

# 2. 必要なパッケージのインストール
echo -e "${YELLOW}[2/8] Installing required packages...${NC}"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    postgresql \
    postgresql-contrib \
    redis-server \
    curl \
    wget \
    build-essential \
    libpq-dev \
    python3-dev
echo -e "${GREEN}✓ Packages installed${NC}"
echo ""

# 3. Node.js & PM2のインストール
echo -e "${YELLOW}[3/8] Installing Node.js and PM2...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
echo -e "${GREEN}✓ Node.js and PM2 installed${NC}"
echo ""

# 4. Python仮想環境の作成
echo -e "${YELLOW}[4/8] Creating Python virtual environment...${NC}"
mkdir -p ~/are-backend
cd ~/are-backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
echo -e "${GREEN}✓ Virtual environment created${NC}"
echo ""

# 5. PostgreSQLの設定
echo -e "${YELLOW}[5/8] Configuring PostgreSQL...${NC}"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# データベースとユーザーの作成
sudo -u postgres psql << EOF
CREATE DATABASE are_production;
CREATE USER are_user WITH PASSWORD 'changeme_secure_password';
GRANT ALL PRIVILEGES ON DATABASE are_production TO are_user;
\q
EOF

echo -e "${GREEN}✓ PostgreSQL configured${NC}"
echo -e "${BLUE}⚠️  Please change the database password in .env file!${NC}"
echo ""

# 6. Redisの起動
echo -e "${YELLOW}[6/8] Starting Redis...${NC}"
sudo systemctl start redis-server
sudo systemctl enable redis-server
echo -e "${GREEN}✓ Redis started${NC}"
echo ""

# 7. GitHubからコードをクローン
echo -e "${YELLOW}[7/8] Cloning repository from GitHub...${NC}"
read -p "Enter your GitHub repository URL: " REPO_URL
cd ~/are-backend
git clone "$REPO_URL" ARE
cd ARE/backend
echo -e "${GREEN}✓ Repository cloned${NC}"
echo ""

# 8. 依存関係のインストール
echo -e "${YELLOW}[8/8] Installing Python dependencies...${NC}"
source ~/are-backend/venv/bin/activate
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# セットアップ完了
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ EC2 Setup Completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Edit .env file with your configuration:"
echo "   cd ~/are-backend/ARE/backend"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. Run database migrations:"
echo "   source ~/are-backend/venv/bin/activate"
echo "   export FLASK_APP=wsgi.py"
echo "   flask db init"
echo "   flask db migrate -m 'Initial migration'"
echo "   flask db upgrade"
echo ""
echo "3. Configure Nginx:"
echo "   sudo cp deployment/aws/nginx.conf /etc/nginx/sites-available/are"
echo "   sudo ln -s /etc/nginx/sites-available/are /etc/nginx/sites-enabled/"
echo "   sudo nginx -t"
echo "   sudo systemctl restart nginx"
echo ""
echo "4. Start application with PM2:"
echo "   cd ~/are-backend/ARE/backend"
echo "   pm2 start deployment/aws/ecosystem.config.js"
echo "   pm2 save"
echo "   pm2 startup"
echo ""
echo "5. Setup SSL with Let's Encrypt:"
echo "   sudo apt install certbot python3-certbot-nginx"
echo "   sudo certbot --nginx -d your-domain.com"
echo ""
echo -e "${GREEN}Happy deploying! 🚀${NC}"
