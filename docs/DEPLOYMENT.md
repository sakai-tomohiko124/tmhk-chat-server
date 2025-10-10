# ARE - デプロイガイド

## 🚀 AWS EC2 Ubuntu サーバーでのデプロイ手順

このガイドでは、AWS EC2 Ubuntuサーバーに**Python Flask + PostgreSQL**環境を構築し、**PM2**でプロセス管理、**No-IP**でHTTPS化する手順を説明します。

---

## 📋 前提条件

- AWS EC2インスタンス（Ubuntu 22.04 LTS推奨）
- SSH接続用の秘密鍵（`.pem`ファイル）
- GitHubリポジトリ
- ドメイン or No-IP無料ドメイン

---

## 🔧 1. Python venv仮想環境の構築

### 1.1 サーバーにSSH接続

```bash
# Windows（Git Bash / PowerShell）
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31

# Mac / Linux
chmod 400 tmhk-chat.pem
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31
```

### 1.2 システムパッケージの更新

```bash
# パッケージリストを更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージをインストール
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib redis-server
```

### 1.3 Python仮想環境の作成

```bash
# プロジェクトディレクトリに移動（なければ作成）
mkdir -p ~/are-backend
cd ~/are-backend

# Python仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 有効化の確認（(venv)が表示されればOK）
which python
# 出力例: /home/ubuntu/are-backend/venv/bin/python
```

### 1.4 GitHubからコードをクローン

```bash
# GitHubリポジトリをクローン
git clone https://github.com/YOUR_USERNAME/ARE.git
cd ARE/backend

# または、既存のコードがある場合
# （パソコンから手動でアップロードした場合など）
```

### 1.5 依存関係のインストール

```bash
# 仮想環境が有効になっていることを確認
source ~/are-backend/venv/bin/activate

# requirements.txtから依存関係をインストール
pip install --upgrade pip
pip install -r requirements.txt

# インストール確認
pip list
```

**requirements.txtの内容確認（設計書1.2章準拠）**:

```txt
# Flask Core
Flask==3.0.0
Flask-CORS==4.0.0
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
Flask-JWT-Extended==4.6.0

# WebSocket
Flask-SocketIO==5.3.6
python-socketio==5.11.0
gevent==24.2.1
gevent-websocket==0.10.1

# Database
psycopg2-binary==2.9.9
SQLAlchemy==2.0.23
alembic==1.13.1

# Redis & Caching
redis==5.0.1
Flask-Caching==2.1.0

# Authentication & Security
bcrypt==4.1.2
PyJWT==2.8.0
cryptography==41.0.7

# AWS SDK
boto3==1.34.11

# Supabase
supabase==2.3.0

# HTTP & API
requests==2.31.0

# WebRTC & Agora
agora-token-builder==1.0.0

# AI & ML
openai==1.7.0  # Grok API互換

# Data Validation
marshmallow==3.20.1
python-dotenv==1.0.0
pydantic==2.5.3

# Utils
python-dateutil==2.8.2
pytz==2023.3
Pillow==10.1.0

# Production Server
gunicorn==21.2.0
eventlet==0.35.1

# Monitoring & Logging
python-json-logger==2.0.7
```

---

## 🗄️ 2. PostgreSQLデータベースの設定

### 2.1 PostgreSQLの起動と確認

```bash
# PostgreSQLサービスの起動
sudo systemctl start postgresql
sudo systemctl enable postgresql

# ステータス確認
sudo systemctl status postgresql
```

### 2.2 データベースとユーザーの作成

```bash
# postgresユーザーに切り替え
sudo -i -u postgres

# PostgreSQL対話シェルに入る
psql

# データベース作成
CREATE DATABASE are_production;

# ユーザー作成とパスワード設定
CREATE USER are_user WITH PASSWORD 'your_secure_password_here';

# 権限付与
GRANT ALL PRIVILEGES ON DATABASE are_production TO are_user;

# 接続確認
\c are_production

# 終了
\q
exit
```

### 2.3 環境変数の設定

```bash
# .envファイルを作成
cd ~/are-backend/ARE/backend
nano .env
```

**.envファイルの内容**:

```bash
# Flask設定
FLASK_APP=wsgi.py
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this
DEBUG=False

# データベース設定（PostgreSQL）
DATABASE_URL=postgresql://are_user:your_secure_password_here@localhost:5432/are_production

# Redis設定
REDIS_URL=redis://localhost:6379/0

# JWT設定
JWT_SECRET_KEY=your-jwt-secret-key-change-this
JWT_ACCESS_TOKEN_EXPIRES=3600

# AWS設定（必要に応じて）
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=ap-northeast-1
AWS_S3_BUCKET=are-media-storage

# Supabase設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# Agora.io設定
AGORA_APP_ID=your-agora-app-id
AGORA_APP_CERTIFICATE=your-agora-cert

# Grok API設定
GROK_API_KEY=your-grok-api-key

# CORS設定
CORS_ORIGINS=https://your-domain.com,http://localhost:5173

# セキュリティ設定
SESSION_COOKIE_SECURE=True
BCRYPT_LOG_ROUNDS=12

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/are.log
```

保存して終了（Ctrl+X → Y → Enter）

### 2.4 データベースマイグレーション

```bash
# 仮想環境を有効化
source ~/are-backend/venv/bin/activate
cd ~/are-backend/ARE/backend

# マイグレーション初期化（初回のみ）
flask db init

# マイグレーションファイル生成
flask db migrate -m "Initial database schema"

# データベースに適用
flask db upgrade
```

---

## 🚀 3. Gunicorn + PM2でのプロセス管理

### 3.1 WSGIエントリーポイントの作成

```bash
cd ~/are-backend/ARE/backend
nano wsgi.py
```

**wsgi.pyの内容**:

```python
"""
ARE - WSGI Entry Point
"""

from app import create_app, socketio

app, socketio = create_app('production')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
```

### 3.2 Gunicorn設定ファイルの作成

```bash
nano gunicorn_config.py
```

**gunicorn_config.pyの内容**:

```python
"""
ARE - Gunicorn設定
"""

import multiprocessing

# サーバーソケット
bind = "0.0.0.0:5000"
backlog = 2048

# ワーカープロセス
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "eventlet"  # WebSocket対応
worker_connections = 1000
timeout = 120
keepalive = 5

# ロギング
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# プロセス命名
proc_name = "are-backend"

# デーモン化
daemon = False

# 再起動
reload = False
```

### 3.3 PM2のインストール（Node.js必要）

```bash
# Node.jsのインストール（まだの場合）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# PM2のインストール
sudo npm install -g pm2

# PM2の確認
pm2 --version
```

### 3.4 PM2設定ファイルの作成

```bash
cd ~/are-backend/ARE/backend
nano ecosystem.config.js
```

**ecosystem.config.jsの内容（Python用）**:

```javascript
module.exports = {
  apps: [
    {
      name: 'are-backend',
      script: '/home/ubuntu/are-backend/venv/bin/gunicorn',
      args: '-c gunicorn_config.py wsgi:app',
      cwd: '/home/ubuntu/are-backend/ARE/backend',
      interpreter: 'none',  // Python仮想環境を使うため
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      env: {
        FLASK_ENV: 'production',
        PORT: 5000
      },
      error_file: 'logs/pm2_error.log',
      out_file: 'logs/pm2_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
```

### 3.5 ログディレクトリの作成

```bash
mkdir -p ~/are-backend/ARE/backend/logs
```

### 3.6 PM2でアプリ起動

```bash
# PM2でアプリ起動
pm2 start ecosystem.config.js

# ステータス確認
pm2 list

# ログ確認
pm2 logs are-backend --lines 50

# 自動起動設定（サーバー再起動時も自動起動）
pm2 startup
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu
pm2 save
```

**PM2の便利コマンド**:

```bash
# アプリ再起動
pm2 restart are-backend

# アプリ停止
pm2 stop are-backend

# アプリ削除
pm2 delete are-backend

# すべてのアプリを再起動
pm2 restart all

# ログをリアルタイムで見る
pm2 logs are-backend --lines 100

# モニタリング
pm2 monit
```

---

## 🌐 4. Nginx + No-IPでHTTPS化

### 4.1 Nginxのインストールと設定

```bash
# Nginxの設定ファイルを作成
sudo nano /etc/nginx/sites-available/are
```

**Nginxの設定内容**:

```nginx
server {
    listen 80;
    server_name your-domain.ddns.net;  # No-IPドメイン

    # ログ設定
    access_log /var/log/nginx/are_access.log;
    error_log /var/log/nginx/are_error.log;

    # リバースプロキシ設定
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket対応
    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静的ファイル（必要に応じて）
    location /static {
        alias /home/ubuntu/are-backend/ARE/backend/static;
        expires 30d;
    }
}
```

```bash
# 設定を有効化
sudo ln -s /etc/nginx/sites-available/are /etc/nginx/sites-enabled/

# デフォルト設定を無効化（必要に応じて）
sudo rm /etc/nginx/sites-enabled/default

# 設定をテスト
sudo nginx -t

# Nginxを再起動
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 4.2 Let's Encrypt でSSL証明書取得（HTTPS化）

```bash
# Certbotのインストール
sudo apt install -y certbot python3-certbot-nginx

# SSL証明書の取得（自動Nginx設定）
sudo certbot --nginx -d your-domain.ddns.net

# 自動更新のテスト
sudo certbot renew --dry-run

# 自動更新のCron設定（証明書は90日で期限切れ）
sudo crontab -e
# 以下を追加
0 3 * * * certbot renew --quiet
```

### 4.3 No-IPの設定（DDNSクライアント）

```bash
# No-IPクライアントのダウンロード
cd /usr/local/src/
sudo wget http://www.noip.com/client/linux/noip-duc-linux.tar.gz
sudo tar xzf noip-duc-linux.tar.gz
cd noip-2.1.9-1/

# コンパイル
sudo make
sudo make install

# 設定（No-IPのメール・パスワードを入力）
sudo /usr/local/bin/noip2 -C

# 起動
sudo /usr/local/bin/noip2

# 自動起動設定
sudo nano /etc/systemd/system/noip2.service
```

**noip2.serviceの内容**:

```ini
[Unit]
Description=No-IP Dynamic DNS Update Client
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/noip2
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# サービス有効化
sudo systemctl daemon-reload
sudo systemctl enable noip2
sudo systemctl start noip2
sudo systemctl status noip2
```

---

## 🔄 5. GitHubからのデプロイ手順（日常作業）

### 5.1 パソコンで修正

```bash
# Windowsの場合（Git Bash）
cd ~/Documents/ARE

# ファイルを編集
# - backend/app/ 内のPythonファイル
# - frontend/src/ 内のReactファイル
```

### 5.2 GitHubにプッシュ

```bash
# 変更を確認
git status

# すべての変更を追加
git add .

# コミット
git commit -m "○○機能を追加"

# GitHubにプッシュ
git push origin main
```

### 5.3 サーバーに反映

```bash
# SSH接続
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31

# プロジェクトディレクトリに移動
cd ~/are-backend/ARE

# GitHubから最新版を取得
git pull origin main

# バックエンドの更新
cd backend

# 仮想環境を有効化
source ~/are-backend/venv/bin/activate

# 依存関係を更新（requirements.txtを変更した場合）
pip install -r requirements.txt

# データベースマイグレーション（モデルを変更した場合）
flask db migrate -m "Update database schema"
flask db upgrade

# PM2でアプリ再起動
pm2 restart are-backend

# ログ確認
pm2 logs are-backend --lines 50

# ステータス確認
pm2 list
```

---

## 🔍 6. トラブルシューティング

### PM2でアプリが起動しない

```bash
# ログを確認
pm2 logs are-backend --lines 100

# Pythonパスの確認
which python
source ~/are-backend/venv/bin/activate
which python

# 手動起動してエラー確認
cd ~/are-backend/ARE/backend
source ~/are-backend/venv/bin/activate
python wsgi.py
```

### データベース接続エラー

```bash
# PostgreSQLの起動確認
sudo systemctl status postgresql

# 接続テスト
psql -U are_user -d are_production -h localhost

# .envファイルのDATABASE_URL確認
cat .env | grep DATABASE_URL
```

### Nginxエラー

```bash
# Nginxの設定テスト
sudo nginx -t

# Nginxのログ確認
sudo tail -f /var/log/nginx/error.log

# ポート5000が起動しているか確認
sudo netstat -tulpn | grep 5000
```

### ポートが使用中

```bash
# ポート5000を使用しているプロセスを確認
sudo lsof -i :5000

# プロセスを強制終了
sudo kill -9 <PID>

# PM2でアプリを再起動
pm2 restart are-backend
```

---

## 📊 7. 監視とメンテナンス

### PM2モニタリング

```bash
# リアルタイム監視
pm2 monit

# ステータス確認
pm2 list

# メモリ使用量確認
pm2 show are-backend
```

### ログのローテーション

```bash
# PM2ログのローテーション設定
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

### ディスク容量の確認

```bash
# ディスク使用量
df -h

# ログファイルのサイズ
du -sh ~/are-backend/ARE/backend/logs/*
```

---

## 🎉 完成！

これで、AWS EC2 Ubuntu サーバーに**Python Flask + PostgreSQL + PM2 + Nginx + HTTPS（No-IP）**の完全な本番環境が構築できました！

**アクセス方法**:
- HTTP: `http://your-domain.ddns.net`
- HTTPS: `https://your-domain.ddns.net`
- API: `https://your-domain.ddns.net/api/v1/`

---

**次のステップ**:
1. フロントエンド（React）のデプロイ
2. 自動テストの設定
3. CI/CDパイプラインの構築
4. 監視ツール（Sentry等）の導入

頑張ってね、ともひこ！🚀
