# TMHKchat 本番環境デプロイメントガイド

## 概要

このガイドでは、TMHKchatを本番環境（AWS EC2: 52.69.241.31）にデプロイする手順を説明します。

**実施日**: 2025年9月28日  
**対象環境**: AWS EC2 (Ubuntu)  
**サーバーIP**: 52.69.241.31  
**プロセス管理**: PM2  
**ダイナミックDNS**: No-IP

---

## 📋 デプロイ前チェックリスト

### ローカル環境（GitHub Codespaces）

- [ ] すべてのコード変更が完了している
- [ ] `.env.example`に必要な環境変数が記載されている
- [ ] `requirements.txt`が最新である
- [ ] `ecosystem.config.js`（PM2設定）が作成されている
- [ ] `scripts/setup_noip.sh`（No-IP設定スクリプト）が作成されている
- [ ] `scripts/aws_instance.sh`（AWS管理スクリプト）が作成されている
- [ ] Git作業ツリーがクリーンである

### AWS環境

- [ ] SSH鍵 `tmhk-chat.pem` が利用可能
- [ ] EC2インスタンスが起動している
- [ ] セキュリティグループで以下のポートが開放されている:
  - SSH (22)
  - HTTP (80)
  - HTTPS (443)
  - Application (5000) - オプション

### 必要な認証情報

- [ ] GitHubアカウントの認証情報
- [ ] AWS CLI認証情報（AWS Access Key ID & Secret）
- [ ] No-IPアカウント情報（メールアドレス & パスワード）
- [ ] OpenAI APIキー（.envに記載）
- [ ] Google Gemini APIキー（.envに記載）

---

## 🚀 デプロイ手順

### Phase 1: GitHub への変更のプッシュ

#### 1.1 Git の状態を確認

```bash
cd /workspaces/tmhk-chat-server
git status
```

#### 1.2 変更をステージング

```bash
git add .
```

#### 1.3 変更をコミット

```bash
git commit -m "Production setup: PM2 config, No-IP setup, AWS management scripts"
```

#### 1.4 GitHub へ強制プッシュ（必要な場合）

```bash
# 通常のプッシュ
git push origin main

# 強制プッシュ（リモートとの競合がある場合のみ）
git push -f origin main
```

**警告**: 強制プッシュは他の開発者の作業を上書きする可能性があります。チーム開発の場合は慎重に実行してください。

---

### Phase 2: AWS EC2 インスタンスの起動

#### 2.1 AWS CLI のインストール（未インストールの場合）

```bash
# Ubuntu/Debian
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 確認
aws --version
```

#### 2.2 AWS 認証情報の設定

```bash
aws configure
```

以下を入力:
- AWS Access Key ID: `[あなたのアクセスキー]`
- AWS Secret Access Key: `[あなたのシークレットキー]`
- Default region name: `ap-northeast-1`
- Default output format: `json`

#### 2.3 環境変数の設定（インスタンスIDがわかる場合）

```bash
export AWS_INSTANCE_ID=i-xxxxxxxxxxxxxxxxx  # 実際のIDに置き換え
```

#### 2.4 インスタンスの起動

```bash
bash scripts/aws_instance.sh start
```

または直接AWS CLIを使用:

```bash
aws ec2 start-instances --region ap-northeast-1 --instance-ids i-xxxxxxxxxxxxxxxxx
aws ec2 wait instance-running --region ap-northeast-1 --instance-ids i-xxxxxxxxxxxxxxxxx
```

#### 2.5 起動確認

```bash
bash scripts/aws_instance.sh status
```

---

### Phase 3: サーバーへの SSH 接続

#### 3.1 SSH鍵の権限設定

```bash
chmod 400 tmhk-chat.pem
```

#### 3.2 SSH接続

```bash
ssh -i tmhk-chat.pem ubuntu@52.69.241.31
```

**接続できない場合**:
- インスタンスが完全に起動するまで2-3分待つ
- セキュリティグループでポート22が開放されているか確認
- SSH鍵ファイルのパスが正しいか確認

---

### Phase 4: サーバー側での初期セットアップ（初回のみ）

#### 4.1 システムパッケージの更新

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### 4.2 必要なパッケージのインストール

```bash
sudo apt-get install -y python3 python3-pip python3-venv git nginx
```

#### 4.3 Node.js と PM2 のインストール

```bash
# Node.js v20.x をインストール
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# PM2 をグローバルインストール
sudo npm install -g pm2

# PM2 の自動起動設定
pm2 startup systemd
# 表示されたコマンドを実行（sudo env PATH=...）
```

#### 4.4 プロジェクトのクローン

```bash
cd /home/ubuntu
git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
cd tmhk-chat-server
```

#### 4.5 Python仮想環境のセットアップ

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4.6 環境変数ファイルの作成

```bash
cp .env.example .env
nano .env
```

以下の重要な変数を設定:
```env
FLASK_ENV=production
SECRET_KEY=[ランダムな文字列を生成]
DATABASE_URL=sqlite:///chat.db
OPENAI_API_KEY=[あなたのOpenAI APIキー]
GEMINI_API_KEY=[あなたのGemini APIキー]
```

SECRET_KEYの生成:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

#### 4.7 ディレクトリ構造の作成

```bash
mkdir -p static/assets/uploads
mkdir -p static/assets/images
mkdir -p logs
```

#### 4.8 データベースの初期化

```bash
python3 -c "from app import db; db.create_all()"
```

または:
```bash
python3 scripts/check_db.py
```

---

### Phase 5: No-IP のセットアップ

#### 5.1 No-IP アカウントの準備

1. https://www.noip.com/ でアカウント作成（未作成の場合）
2. ダッシュボードでホスト名を作成（例: `tmhkchat.ddns.net`）
3. IPアドレスを `52.69.241.31` に設定

#### 5.2 No-IP クライアントのインストール

```bash
sudo bash scripts/setup_noip.sh
```

インタラクティブな設定画面で以下を入力:
- No-IPメールアドレス
- No-IPパスワード
- 更新するホスト名を選択
- 更新間隔（デフォルト: 30分）

#### 5.3 No-IP サービスの確認

```bash
# サービス状態確認
sudo systemctl status noip2

# No-IP クライアントの状態確認
sudo /usr/local/bin/noip2 -S

# ログ確認
sudo journalctl -u noip2 -f
```

---

### Phase 6: PM2 でのアプリケーション起動

#### 6.1 PM2設定ファイルの確認

```bash
cat ecosystem.config.js
```

#### 6.2 アプリケーションの起動

```bash
pm2 start ecosystem.config.js --env production
```

#### 6.3 PM2 の状態確認

```bash
pm2 status
pm2 logs tmhk-chat
pm2 monit
```

#### 6.4 PM2 の自動起動設定を保存

```bash
pm2 save
```

---

### Phase 7: Nginx のセットアップ（リバースプロキシ）

#### 7.1 Nginx設定ファイルの作成

```bash
sudo nano /etc/nginx/sites-available/tmhkchat
```

以下の内容を貼り付け:

```nginx
server {
    listen 80;
    server_name 52.69.241.31 tmhkchat.ddns.net;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/tmhk-chat-server/chat.sock;
    }

    location /socket.io {
        include proxy_params;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_pass http://unix:/home/ubuntu/tmhk-chat-server/chat.sock/socket.io;
    }

    location /static {
        alias /home/ubuntu/tmhk-chat-server/static;
        expires 30d;
    }

    client_max_body_size 10M;
}
```

#### 7.2 設定の有効化

```bash
sudo ln -s /etc/nginx/sites-available/tmhkchat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 7.3 Nginx の自動起動設定

```bash
sudo systemctl enable nginx
```

---

### Phase 8: ファイアウォール設定（UFW）

#### 8.1 UFW の有効化

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

#### 8.2 状態確認

```bash
sudo ufw status
```

---

## 🔄 デプロイ後の更新手順

コードを更新する場合は以下の手順を実施します:

### ローカル環境

```bash
# 1. コード変更後、コミット＆プッシュ
git add .
git commit -m "Update: [変更内容]"
git push origin main
```

### サーバー環境

```bash
# 2. サーバーにSSH接続
ssh -i tmhk-chat.pem ubuntu@52.69.241.31

# 3. デプロイスクリプトを実行
cd /home/ubuntu/tmhk-chat-server
bash deploy.sh
```

または手動で:

```bash
# プロジェクトディレクトリへ移動
cd /home/ubuntu/tmhk-chat-server

# 最新コードを取得
git pull origin main

# 仮想環境を有効化
source venv/bin/activate

# パッケージを更新（requirements.txtが変更された場合）
pip install -r requirements.txt

# PM2でアプリケーションを再起動
pm2 restart tmhk-chat

# ログを確認
pm2 logs tmhk-chat
```

---

## 🔍 トラブルシューティング

### アプリケーションが起動しない

```bash
# PM2ログを確認
pm2 logs tmhk-chat --lines 100

# エラーログを確認
tail -f logs/error.log

# Gunicornのログを確認
tail -f logs/access.log
```

### データベースエラー

```bash
# データベースの存在確認
ls -la chat.db

# データベースの再作成
python3 scripts/check_db.py
```

### ソケットファイルが見つからない

```bash
# ソケットファイルの確認
ls -la chat.sock

# PM2を再起動
pm2 restart tmhk-chat

# 権限を確認
chmod 666 chat.sock
```

### Nginx エラー

```bash
# Nginx設定のテスト
sudo nginx -t

# Nginxエラーログ
sudo tail -f /var/log/nginx/error.log

# Nginx再起動
sudo systemctl restart nginx
```

### No-IP が更新されない

```bash
# No-IP状態確認
sudo /usr/local/bin/noip2 -S

# サービス再起動
sudo systemctl restart noip2

# ログ確認
sudo journalctl -u noip2 -f
```

### AWS インスタンスに接続できない

```bash
# インスタンスが起動しているか確認
bash scripts/aws_instance.sh status

# セキュリティグループを確認（AWSコンソール）
# ポート22（SSH）が0.0.0.0/0で開放されているか確認
```

---

## 📊 監視とメンテナンス

### PM2 監視

```bash
# リアルタイム監視
pm2 monit

# メモリ・CPU使用状況
pm2 list

# 詳細情報
pm2 show tmhk-chat
```

### ログローテーション

```bash
# PM2のログローテーション設定
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

### 定期バックアップ

```bash
# バックアップスクリプトを実行
bash backup.sh

# cronで自動化（毎日午前3時）
crontab -e
# 以下を追加:
0 3 * * * /home/ubuntu/tmhk-chat-server/backup.sh
```

---

## 🔒 セキュリティベストプラクティス

1. **SSH鍵の管理**
   - `tmhk-chat.pem` は厳重に管理（GitHub等にアップロードしない）
   - 権限を400に設定: `chmod 400 tmhk-chat.pem`

2. **環境変数**
   - `.env` ファイルは絶対にGitにコミットしない
   - APIキーは定期的にローテーション

3. **ファイアウォール**
   - 不要なポートは閉じる
   - SSH接続は特定IPからのみ許可（推奨）

4. **定期更新**
   - システムパッケージの定期更新: `sudo apt-get update && sudo apt-get upgrade`
   - Pythonパッケージの更新: `pip list --outdated`

5. **HTTPS化（推奨）**
   - Let's Encrypt で無料SSL証明書を取得
   - Nginxで SSL/TLS を設定

---

## 📞 サポート

### 有用なコマンド一覧

```bash
# サーバー全体の状態確認
systemctl status nginx
systemctl status noip2
pm2 status

# ディスク使用状況
df -h

# メモリ使用状況
free -h

# プロセス確認
ps aux | grep python
ps aux | grep gunicorn

# ネットワーク接続確認
netstat -tulpn | grep :80
netstat -tulpn | grep :5000
```

### ドキュメント参照

- [README.md](./README.md) - プロジェクト全体概要
- [DEVELOPMENT_MANUAL.md](./DEVELOPMENT_MANUAL.md) - 開発・運用マニュアル
- [QUICKSTART.md](./QUICKSTART.md) - クイックスタートガイド

---

## ✅ デプロイ完了チェックリスト

- [ ] GitHubに最新コードがプッシュされている
- [ ] AWS EC2インスタンスが起動している
- [ ] サーバーにSSH接続できる
- [ ] Python仮想環境が作成されている
- [ ] 環境変数（.env）が設定されている
- [ ] データベースが初期化されている
- [ ] No-IPが正常に動作している（ホスト名でアクセス可能）
- [ ] PM2でアプリケーションが起動している
- [ ] Nginxが正常に動作している
- [ ] ブラウザで http://52.69.241.31 または http://tmhkchat.ddns.net にアクセスできる
- [ ] SocketIOのリアルタイム機能が動作している
- [ ] ログが正常に記録されている
- [ ] バックアップスクリプトが動作する

---

**最終更新**: 2025年9月28日  
**バージョン**: 1.0.0  
**担当者**: TMHKchat Development Team
