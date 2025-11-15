# 手動デプロイ手順

## 準備

SSH鍵ファイル `tmhk-chat.pem` を用意してください。
このファイルはAWS EC2インスタンス作成時にダウンロードしたものです。

## デプロイ手順

### 1. SSH鍵の権限設定（初回のみ）

Windows PowerShellで実行:
```powershell
# SSH鍵ファイルの場所に移動（例）
cd C:\Users\<ユーザー名>\Downloads

# 権限を確認
icacls tmhk-chat.pem
```

### 2. サーバーに接続

```cmd
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31
```

**接続できない場合のトラブルシューティング:**
- ファイアウォールで22番ポートが開いているか確認
- AWS EC2のセキュリティグループで22番ポートのインバウンドルールが設定されているか確認
- SSH鍵ファイルのパスが正しいか確認

### 3. サーバー側での操作

接続できたら、以下のコマンドを実行:

```bash
# ホームディレクトリに移動
cd ~

# リポジトリがなければクローン
if [ ! -d "tmhk-chat-server" ]; then
    git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
fi

# プロジェクトディレクトリに移動
cd tmhk-chat-server

# 最新のコードを取得（強制的に上書き）
git fetch origin
git reset --hard origin/main

# Pythonパッケージのインストール
pip3 install -r requirements.txt

# PM2でアプリケーションを管理
pm2 restart tmhk-chat 2>/dev/null || pm2 start app.py --name tmhk-chat --interpreter python3

# ステータス確認
pm2 status
pm2 logs tmhk-chat --lines 20
```

### 4. 動作確認

ブラウザで以下のURLにアクセス:
- http://52.69.241.31:5000

ログインして以下を確認:
- ✅ ログイン機能
- ✅ AIチャット機能
- ✅ サイドメニュー（ハンバーガーメニュー）の表示
- ✅ 天気情報ページ
- ✅ 電車情報ページ
- ✅ ゲームページ

## PM2コマンド

```bash
# ログをリアルタイムで監視
pm2 logs tmhk-chat

# プロセスの詳細情報
pm2 info tmhk-chat

# アプリケーションを停止
pm2 stop tmhk-chat

# アプリケーションを再起動
pm2 restart tmhk-chat

# アプリケーションを削除
pm2 delete tmhk-chat

# すべてのプロセスのステータス
pm2 status

# システム起動時の自動起動設定
pm2 startup
pm2 save
```

## エラー対処

### ポートが使用中
```bash
sudo lsof -i :5000
sudo kill -9 <PID>
pm2 restart tmhk-chat
```

### Pythonパッケージエラー
```bash
pip3 install --upgrade pip
pip3 install -r requirements.txt --force-reinstall
```

### データベースエラー
```bash
python3 scripts/init_database.py
```

### Git競合エラー
```bash
git fetch origin
git reset --hard origin/main
```

## ログ確認

```bash
# PM2ログ
pm2 logs tmhk-chat --lines 100

# Flaskアプリケーションのログ
tail -f ~/.pm2/logs/tmhk-chat-out.log
tail -f ~/.pm2/logs/tmhk-chat-error.log

# システムログ
sudo journalctl -u pm2-ubuntu -n 50
```

## セキュリティ設定

AWS EC2セキュリティグループで以下のポートを開放:
- **22** (SSH) - 自分のIPアドレスからのみ
- **5000** (Flask) - 0.0.0.0/0（全IPアドレス）

## 定期的なメンテナンス

```bash
# システムアップデート
sudo apt update && sudo apt upgrade -y

# PM2アップデート
npm install -g pm2@latest

# Pythonパッケージアップデート
pip3 list --outdated
pip3 install --upgrade <package_name>

# ログローテーション
pm2 flush
```

## バックアップ

```bash
# データベースバックアップ
sqlite3 chat.db ".backup chat_backup_$(date +%Y%m%d).db"

# プロジェクト全体のバックアップ
tar -czf tmhk-chat-backup-$(date +%Y%m%d).tar.gz tmhk-chat-server/
```

## GitHubからの最新コード取得

```bash
cd ~/tmhk-chat-server
git fetch origin
git reset --hard origin/main
pip3 install -r requirements.txt
pm2 restart tmhk-chat
```

## 完全な再インストール

```bash
# 既存のアプリケーションを停止・削除
pm2 stop tmhk-chat
pm2 delete tmhk-chat

# ディレクトリを削除
cd ~
rm -rf tmhk-chat-server

# 再度クローン
git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
cd tmhk-chat-server

# セットアップ
pip3 install -r requirements.txt
python3 scripts/init_database.py

# 起動
pm2 start app.py --name tmhk-chat --interpreter python3
pm2 save
```
