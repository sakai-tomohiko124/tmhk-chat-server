# 「TMHKchat」開発・運用マニュアル

**作成日**: 2025年9月28日  
**バージョン**: 1.0  
**更新日**: 2025年11月14日

---

## 📋 目次

1. [開発の流れ（一番よく使う手順）](#1-開発の流れ一番よく使う手順)
2. [サーバーの動作確認（様子がおかしいとき）](#2-サーバーの動作確認様子がおかしいとき)
3. [初回セットアップ手順](#3-初回セットアップ手順)
4. [環境別の設定](#4-環境別の設定)
5. [データベース管理](#5-データベース管理)
6. [バックアップとリストア](#6-バックアップとリストア)
7. [セキュリティ対策](#7-セキュリティ対策)
8. [パフォーマンス最適化](#8-パフォーマンス最適化)
9. [よくある質問（FAQ）](#9-よくある質問faq)

---

## 1. 開発の流れ（一番よく使う手順）

この手順は、パソコンで修正したプログラムを、インターネット上のサーバーに反映させるときに毎回使います。

### ステップ1: パソコンでプログラムを修正する

まず、自分のパソコンでプログラムの修正や機能追加を行います。

#### 作業フォルダを開く

**Windows**:
```
C:\Users\skyto\Documents\server
```

**Linux/Mac**:
```bash
~/tmhk-chat-server
```

#### ファイルを編集する

- **プログラム本体**: `app.py`
- **HTMLなど画面の見た目**: `templates` フォルダ内のファイル
- **CSS/JavaScript**: `static/css/`, `static/js/` 内のファイル
- **バックエンドサービス**: `services/` フォルダ内のファイル
- **使いたい部品（ライブラリ）を追加した場合**: `requirements.txt` に名前を追記

#### （もしあれば）不要なファイルを削除する

エクスプローラーやFinderでファイルを右クリックして削除するだけでOKです。

---

### ステップ2: 修正内容をGitHubに記録・保管する

次に、パソコンでの修正内容をGitHubにアップロードします。作業は **Git Bash** (Windows) または **ターミナル** (Mac/Linux) で行います。

#### 1. ターミナル（Git Bash）を開き、作業フォルダに移動する

**Windows (Git Bash)**:
```bash
cd ~/Documents/server
```

**Linux/Mac**:
```bash
cd ~/tmhk-chat-server
```

#### 2. 変更したファイルを確認する（任意）

```bash
git status
```

**表示例**:
```
modified:   app.py
modified:   templates/chat.html
new file:   static/js/new-feature.js
```

#### 3. 全ての変更を記録の対象にする

```bash
git add .
```

💡 **ヒント**: 特定のファイルだけを追加したい場合は、`git add ファイル名` を使います。

#### 4. 変更内容にメモ（コミットメッセージ）を付けて記録を確定する

```bash
git commit -m "○○の機能を追加"
```

**良いコミットメッセージの例**:
- ✅ `git commit -m "チャット画面にファイル送信機能を追加"`
- ✅ `git commit -m "プロフィール画像のアップロード処理を修正"`
- ✅ `git commit -m "バグ修正: メッセージ削除時のエラーを解消"`

**悪い例**:
- ❌ `git commit -m "修正"`
- ❌ `git commit -m "update"`
- ❌ `git commit -m "あああ"`

💡 **ヒント**: 「」の中身は、何を変更したか分かるように具体的に書くと後で見返したときに便利です。

#### 5. GitHubにアップロードする

```bash
git push origin main
```

**初回の場合**: GitHubの認証を求められることがあります。GitHubのユーザー名とパスワード（またはPersonal Access Token）を入力してください。

---

### ステップ3: サーバーに修正内容を反映させる

最後に、GitHubにアップロードした最新のプログラムを、AWSサーバーにダウンロードして動かします。

#### 1. サーバーに接続する（SSH接続）

**Windows (Git Bash) / Mac / Linux**:
```bash
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31
```

⚠️ **注意**: `tmhk-chat.pem` ファイルがあるフォルダで実行してください。

**PEMファイルの場所**:
- Windows: `C:\Users\skyto\.ssh\tmhk-chat.pem`
- Mac/Linux: `~/.ssh/tmhk-chat.pem`

**初回接続時のエラー対処**:
```bash
# Windowsの場合
chmod 400 tmhk-chat.pem

# Mac/Linuxの場合
chmod 400 ~/.ssh/tmhk-chat.pem
```

#### 2. 作業フォルダに移動する

```bash
cd ~/tmhk-chat-server
```

#### 3. GitHubから最新のプログラムをダウンロードする

```bash
git pull origin main
```

**表示例**:
```
remote: Counting objects: 5, done.
remote: Compressing objects: 100% (3/3), done.
Updating abc1234..def5678
Fast-forward
 app.py                | 10 +++++++++-
 templates/chat.html   |  5 +++++
 2 files changed, 14 insertions(+), 1 deletion(-)
```

#### 4. （もしあれば）新しい部品（ライブラリ）をインストールする

⚠️ **注意**: `requirements.txt` を変更した場合のみ、この手順が必要です。

```bash
# 仮想環境を有効化
source venv/bin/activate

# 新しいパッケージをインストール
pip install -r requirements.txt
```

**インストール確認**:
```bash
pip list
```

#### 5. アプリを再起動して、修正を反映させる

```bash
pm2 restart tmhk-chat
```

**成功時の表示例**:
```
[PM2] Applying action restartProcessId on app [tmhk-chat](ids: [ 0 ])
[PM2] [tmhk-chat](0) ✓
```

これで、Webサイトが新しいバージョンに更新されます。

#### 6. ブラウザで動作確認

```
http://52.69.241.31
```

または独自ドメインがある場合:
```
https://your-domain.com
```

---

## 2. サーバーの動作確認（様子がおかしいとき）

アプリがうまく動かない、エラーが出ているかもしれない、というときに使います。

### サーバーに接続後、アプリの状態を確認する

```bash
pm2 list
```

**表示例**:
```
┌─────┬──────────────┬─────────────┬─────────┬─────────┬──────────┐
│ id  │ name         │ namespace   │ version │ mode    │ pid      │
├─────┼──────────────┼─────────────┼─────────┼─────────┼──────────┤
│ 0   │ tmhk-chat    │ default     │ N/A     │ fork    │ 12345    │
└─────┴──────────────┴─────────────┴─────────┴─────────┴──────────┘
```

- `status` が `online` なら正常に動いています。
- `status` が `errored` や `stopped` になっていたら、何か問題が起きています。

### エラーの原因（ログ）を確認する

```bash
pm2 logs tmhk-chat
```

**ログ表示例**:
```
[TAILING] Tailing last 15 lines for [tmhk-chat] process
/home/ubuntu/.pm2/logs/tmhk-chat-out.log last 15 lines:
0|tmhk-cha | [2025-11-14 10:30:00] INFO: Starting application...
0|tmhk-cha | [2025-11-14 10:30:01] INFO: Database connected
0|tmhk-cha | [2025-11-14 10:30:02] ERROR: File not found: template.html
```

- エラーメッセージが表示されるので、その内容をヒントに原因を探ります。
- ログ表示を止めるときは `Ctrl + C` を押します。

### その他の便利なPM2コマンド

```bash
# 特定のプロセスを停止
pm2 stop tmhk-chat

# 特定のプロセスを開始
pm2 start tmhk-chat

# すべてのプロセスを再起動
pm2 restart all

# プロセスの詳細情報を表示
pm2 show tmhk-chat

# PM2の設定を保存（再起動時に自動起動）
pm2 save

# システム起動時の自動起動を設定
pm2 startup
```

---

## 3. 初回セットアップ手順

### 新しいサーバーに初めてデプロイする場合の手順

#### 1. サーバーにSSH接続

```bash
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31
```

#### 2. システムパッケージを更新

```bash
sudo apt update
sudo apt upgrade -y
```

#### 3. 必要なソフトウェアをインストール

```bash
# Python 3.12のインストール
sudo apt install python3.12 python3.12-venv python3-pip -y

# Gitのインストール
sudo apt install git -y

# Node.jsとnpmのインストール（PM2用）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# PM2のインストール
sudo npm install -g pm2
```

#### 4. プロジェクトをクローン

```bash
cd ~
git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
cd tmhk-chat-server
```

#### 5. 仮想環境を作成

```bash
python3.12 -m venv venv
source venv/bin/activate
```

#### 6. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

#### 7. データベースを初期化

```bash
python -c "from app import init_db; init_db()"
```

#### 8. 管理者アカウントを作成

```bash
python scripts/create_admin.py
```

**入力例**:
```
管理者ユーザー名: admin
管理者パスワード: your-secure-password
```

#### 9. PM2でアプリケーションを起動

```bash
# アプリケーションディレクトリに移動
cd /home/ubuntu/tmhk-chat-server

# PM2で起動
pm2 start ./venv/bin/gunicorn \
  --name tmhk-chat \
  --interpreter ./venv/bin/python \
  -- --workers 3 --bind unix:chat.sock -m 007 app:app

# 設定を保存
pm2 save

# システム起動時の自動起動を有効化
pm2 startup
```

#### 10. Nginxの設定（オプション）

```bash
# Nginxをインストール
sudo apt install nginx -y

# 設定ファイルを作成
sudo nano /etc/nginx/sites-available/tmhk-chat
```

**設定内容**:
```nginx
server {
    listen 80;
    server_name 52.69.241.31;  # または your-domain.com

    location / {
        proxy_pass http://unix:/home/ubuntu/tmhk-chat-server/chat.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://unix:/home/ubuntu/tmhk-chat-server/chat.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**設定を有効化**:
```bash
# シンボリックリンクを作成
sudo ln -s /etc/nginx/sites-available/tmhk-chat /etc/nginx/sites-enabled/

# デフォルト設定を削除
sudo rm /etc/nginx/sites-enabled/default

# 設定をテスト
sudo nginx -t

# Nginxを再起動
sudo systemctl restart nginx
```

---

## 4. 環境別の設定

### 開発環境（ローカルPC）

**.env ファイルの作成**:
```bash
# プロジェクトルートに .env ファイルを作成
SECRET_KEY=dev-secret-key
FLASK_ENV=development
DEBUG=True
DATABASE_PATH=chat_dev.db
```

**起動コマンド**:
```bash
python app.py
```

### ステージング環境

```bash
SECRET_KEY=staging-secret-key
FLASK_ENV=staging
DEBUG=False
DATABASE_PATH=chat_staging.db
```

### 本番環境（AWS）

```bash
SECRET_KEY=production-secret-key-change-this
FLASK_ENV=production
DEBUG=False
DATABASE_PATH=/var/lib/tmhk-chat/chat.db
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
```

---

## 5. データベース管理

### データベースのバックアップ

```bash
# 手動バックアップ
cp chat.db chat_backup_$(date +%Y%m%d_%H%M%S).db

# 定期的な自動バックアップ（cronに設定）
crontab -e
```

**cron設定例（毎日午前3時にバックアップ）**:
```cron
0 3 * * * cd /home/ubuntu/tmhk-chat-server && cp chat.db /home/ubuntu/backups/chat_$(date +\%Y\%m\%d).db
```

### データベースの確認

```bash
python scripts/check_db.py
```

### データベースのリストア

```bash
# アプリケーションを停止
pm2 stop tmhk-chat

# バックアップから復元
cp chat_backup_20251114_100000.db chat.db

# アプリケーションを再起動
pm2 restart tmhk-chat
```

---

## 6. バックアップとリストア

### 完全バックアップスクリプト

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/ubuntu/backups"
PROJECT_DIR="/home/ubuntu/tmhk-chat-server"
DATE=$(date +%Y%m%d_%H%M%S)

# バックアップディレクトリを作成
mkdir -p $BACKUP_DIR

# データベースをバックアップ
cp $PROJECT_DIR/chat.db $BACKUP_DIR/chat_$DATE.db

# アップロードファイルをバックアップ
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz $PROJECT_DIR/static/assets/uploads

# 古いバックアップを削除（30日以上前）
find $BACKUP_DIR -name "chat_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**実行権限を付与**:
```bash
chmod +x backup.sh
```

**cronで自動化**:
```cron
0 3 * * * /home/ubuntu/tmhk-chat-server/backup.sh >> /var/log/tmhk-backup.log 2>&1
```

---

## 7. セキュリティ対策

### 1. ファイアウォール設定

```bash
# UFWを有効化
sudo ufw enable

# SSH（ポート22）を許可
sudo ufw allow 22/tcp

# HTTP（ポート80）を許可
sudo ufw allow 80/tcp

# HTTPS（ポート443）を許可
sudo ufw allow 443/tcp

# 状態確認
sudo ufw status
```

### 2. SSL/TLS証明書の設定（Let's Encrypt）

```bash
# Certbotをインストール
sudo apt install certbot python3-certbot-nginx -y

# SSL証明書を取得
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 自動更新のテスト
sudo certbot renew --dry-run
```

### 3. セキュリティヘッダーの設定

**Nginx設定に追加**:
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

---

## 8. パフォーマンス最適化

### Gunicornワーカー数の調整

**推奨設定**: `(2 × CPU数) + 1`

```bash
# CPU数を確認
nproc

# 例: 2コアの場合、5ワーカー
pm2 start ./venv/bin/gunicorn \
  --name tmhk-chat \
  --interpreter ./venv/bin/python \
  -- --workers 5 --bind unix:chat.sock -m 007 app:app
```

### データベース最適化

```bash
# SQLiteの最適化
sqlite3 chat.db "VACUUM;"
sqlite3 chat.db "ANALYZE;"
```

### ログのローテーション

```bash
# /etc/logrotate.d/tmhk-chat を作成
sudo nano /etc/logrotate.d/tmhk-chat
```

**内容**:
```
/home/ubuntu/.pm2/logs/tmhk-chat*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        pm2 reloadLogs
    endscript
}
```

---

## 9. よくある質問（FAQ）

### Q1: `git push`時に認証エラーが出る

**A**: Personal Access Tokenを使用してください。

```bash
# GitHubでPersonal Access Tokenを作成
# Settings > Developer settings > Personal access tokens > Generate new token

# 認証情報を保存
git config --global credential.helper store

# 次回のpush時にトークンを入力
git push origin main
# Username: your-github-username
# Password: ghp_xxxxxxxxxxxxxxxxxxxx（トークン）
```

### Q2: PM2起動時に`EACCES`エラーが出る

**A**: Unixソケットのパーミッションを確認してください。

```bash
# ソケットファイルの権限を変更
chmod 666 chat.sock

# または、PM2の起動コマンドで明示的に指定
pm2 start ./venv/bin/gunicorn \
  --name tmhk-chat \
  --interpreter ./venv/bin/python \
  -- --workers 3 --bind unix:chat.sock --umask 007 app:app
```

### Q3: データベースが壊れた

**A**: バックアップから復元してください。

```bash
pm2 stop tmhk-chat
cp chat_backup_latest.db chat.db
pm2 restart tmhk-chat
```

### Q4: メモリ不足エラー

**A**: ワーカー数を減らすか、サーバーのメモリを増やしてください。

```bash
# ワーカー数を減らす
pm2 delete tmhk-chat
pm2 start ./venv/bin/gunicorn \
  --name tmhk-chat \
  --interpreter ./venv/bin/python \
  -- --workers 2 --bind unix:chat.sock -m 007 app:app
```

### Q5: Socket.IOが接続できない

**A**: Nginx設定を確認してください。

```bash
# Nginxのエラーログを確認
sudo tail -f /var/log/nginx/error.log

# 設定をテスト
sudo nginx -t

# Nginxを再起動
sudo systemctl restart nginx
```

---

## 📞 サポート・お問い合わせ

問題が解決しない場合は、以下の方法でサポートを受けられます:

1. **GitHubのIssues**: https://github.com/sakai-tomohiko124/tmhk-chat-server/issues
2. **ログファイルの確認**: `pm2 logs tmhk-chat`
3. **システムログの確認**: `/var/log/nginx/error.log`

---

**マニュアルの更新履歴**:
- 2025年9月28日: 初版作成
- 2025年11月14日: 詳細な手順とトラブルシューティングを追加
