# トラブルシューティングガイド

## SSH接続エラー: "Connection timed out"

### 原因
サーバーに接続できない場合、以下の理由が考えられます：

1. **EC2インスタンスが停止している**
2. **セキュリティグループの設定が不適切**
3. **ネットワークの問題**

### 解決方法

#### 1. AWSコンソールでEC2インスタンスの状態を確認

1. [AWSコンソール](https://console.aws.amazon.com/)にログイン
2. EC2ダッシュボードを開く
3. インスタンスのステータスを確認
   - **停止中** → インスタンスを起動
   - **実行中** → 次のステップへ

#### 2. セキュリティグループの設定を確認

1. EC2インスタンスを選択
2. 「セキュリティ」タブをクリック
3. セキュリティグループをクリック
4. 「インバウンドルール」を確認

**必要なルール:**
```
タイプ: SSH
プロトコル: TCP
ポート範囲: 22
ソース: 0.0.0.0/0 または あなたのIPアドレス

タイプ: カスタムTCP
プロトコル: TCP
ポート範囲: 5000
ソース: 0.0.0.0/0
```

#### 3. IPアドレスが変わっていないか確認

EC2インスタンスを再起動するとパブリックIPアドレスが変わる場合があります。

1. EC2ダッシュボードでインスタンスの「パブリックIPv4アドレス」を確認
2. 現在のIPアドレス: `52.69.241.31`
3. 異なる場合は、すべてのスクリプト・設定ファイルのIPアドレスを更新

#### 4. SSH鍵ファイルのパスを確認

```cmd
dir "C:\Users\skyto\ARE\tmhk-chat.pem"
```

ファイルが見つからない場合:
- AWSコンソールから鍵ペアを再ダウンロード
- または新しい鍵ペアを作成してEC2インスタンスに関連付け

#### 5. 接続診断

**サーバーへのPing確認:**
```bash
ping 52.69.241.31
```

**ポート22の接続確認:**
```bash
# Windows (PowerShell)
Test-NetConnection 52.69.241.31 -Port 22

# Git Bash / Linux
nc -zv 52.69.241.31 22
# または
telnet 52.69.241.31 22
```

**タイムアウトを延長してSSH接続:**
```bash
ssh -i "tmhk-chat.pem" -o ConnectTimeout=600 -o ServerAliveInterval=60 ubuntu@52.69.241.31
```

**詳細ログを確認:**
```bash
ssh -vvv -i "tmhk-chat.pem" ubuntu@52.69.241.31
```

## デプロイエラー

### エラー: "git: command not found"

**解決方法:**
```bash
sudo apt update
sudo apt install -y git
```

### エラー: "pip3: command not found"

**解決方法:**
```bash
sudo apt update
sudo apt install -y python3-pip
```

### エラー: "pm2: command not found"

**解決方法:**
```bash
# Node.jsとnpmをインストール
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# PM2をグローバルインストール
sudo npm install -g pm2
```

### エラー: "Address already in use"（ポート5000が使用中）

**解決方法:**
```bash
# ポートを使用しているプロセスを確認
sudo lsof -i :5000

# プロセスを停止
pm2 stop tmhk-chat

# または強制終了
sudo kill -9 <PID>

# アプリを再起動
pm2 restart tmhk-chat
```

### エラー: "ModuleNotFoundError: No module named 'flask'"

**解決方法:**
```bash
cd /home/ubuntu/tmhk-chat-server
pip3 install -r requirements.txt --force-reinstall
```

## アプリケーションエラー

### アプリが起動しない

**確認手順:**
```bash
# PM2のステータスを確認
pm2 status

# ログを確認
pm2 logs tmhk-chat --lines 100

# エラーログを確認
pm2 logs tmhk-chat --err --lines 50
```

### データベースエラー

**解決方法:**
```bash
cd /home/ubuntu/tmhk-chat-server

# データベースを削除（注意: データが消えます）
rm -f chat.db

# 再初期化
python3 scripts/init_database.py

# アプリを再起動
pm2 restart tmhk-chat
```

### 環境変数が設定されていない

**解決方法:**
```bash
cd /home/ubuntu/tmhk-chat-server

# .envファイルを作成
nano .env

# 以下を追加
GEMINI_API_KEY=your_api_key_here
OPENAI_API_KEY=your_api_key_here

# 保存: Ctrl+O, Enter, Ctrl+X

# アプリを再起動
pm2 restart tmhk-chat
```

## パフォーマンス問題

### アプリケーションが遅い

**解決方法:**

1. **リソース使用状況を確認**
```bash
# CPU・メモリ使用状況
pm2 monit

# システムリソース
top
```

2. **ログファイルをクリア**
```bash
pm2 flush
```

3. **PM2を最適化**
```bash
pm2 reload tmhk-chat
```

## ネットワーク問題

### ブラウザからアクセスできない

**確認項目:**

1. **アプリが実行中か確認**
```bash
pm2 status
```

2. **ポート5000が開いているか確認**
```bash
sudo netstat -tuln | grep 5000
```

3. **ファイアウォール設定を確認**
```bash
sudo ufw status
# 必要に応じて
sudo ufw allow 5000/tcp
```

4. **セキュリティグループを再確認**
   - AWSコンソールでポート5000のインバウンドルールを確認

## 緊急時の対処

### 完全な再インストール

```bash
# すべて停止・削除
pm2 stop tmhk-chat
pm2 delete tmhk-chat
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
pm2 startup
```

## サポート情報

### 有用なコマンド

```bash
# システム情報
uname -a
python3 --version
pip3 --version
pm2 --version

# ディスク使用量
df -h

# メモリ使用量
free -h

# 実行中のプロセス
ps aux | grep python

# ネットワーク接続
netstat -tuln

# 最近のログ
tail -f /var/log/syslog
```

### ログの場所

- **PM2ログ**: `~/.pm2/logs/`
- **アプリケーションログ**: `~/.pm2/logs/tmhk-chat-out.log`
- **エラーログ**: `~/.pm2/logs/tmhk-chat-error.log`
- **システムログ**: `/var/log/syslog`

### 問い合わせ前のチェックリスト

エラーを報告する前に、以下の情報を収集してください：

1. エラーメッセージの全文
2. PM2ステータス: `pm2 status`
3. 最新のログ: `pm2 logs tmhk-chat --lines 50`
4. システム情報: `uname -a && python3 --version`
5. 実行したコマンドの履歴
