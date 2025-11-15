# AWS EC2サーバーへのデプロイ手順

## 前提条件
- tmhk-chat.pem ファイルが現在のディレクトリにあること
- GitHubリポジトリへのプッシュ権限があること
- サーバーにSSH接続できること

## 自動デプロイ（推奨）

```cmd
deploy_to_aws.bat
```

このバッチファイルが以下を自動実行します：
1. GitHubへプッシュ
2. サーバーでgit pull
3. 依存パッケージの更新
4. PM2でアプリケーションを再起動

## 手動デプロイ

### 1. GitHubにプッシュ
```cmd
git push origin main
```

### 2. サーバーに接続
```cmd
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31
```

### 3. サーバー側の操作
```bash
cd /home/ubuntu/tmhk-chat-server

# 最新のコードを取得
git pull origin main

# 依存パッケージの更新（必要な場合）
pip3 install -r requirements.txt

# PM2でアプリケーションを再起動
pm2 restart tmhk-chat

# ステータス確認
pm2 status
pm2 logs tmhk-chat --lines 50
```

## PM2コマンド一覧

### アプリケーションの管理
```bash
pm2 start app.py --name tmhk-chat --interpreter python3  # 初回起動
pm2 restart tmhk-chat                                     # 再起動
pm2 stop tmhk-chat                                        # 停止
pm2 delete tmhk-chat                                      # 削除
```

### ログ確認
```bash
pm2 logs tmhk-chat           # リアルタイムログ表示
pm2 logs tmhk-chat --lines 100  # 直近100行表示
pm2 flush tmhk-chat          # ログクリア
```

### ステータス確認
```bash
pm2 status                   # 全プロセスのステータス
pm2 info tmhk-chat           # 詳細情報
pm2 monit                    # モニタリング画面
```

### 自動起動設定
```bash
pm2 startup                  # システム起動時に自動起動
pm2 save                     # 現在の設定を保存
```

## トラブルシューティング

### ポートが使用中の場合
```bash
sudo lsof -i :5000           # ポート5000を使用しているプロセスを確認
sudo kill -9 <PID>           # プロセスを強制終了
```

### Pythonパッケージエラー
```bash
pip3 install --upgrade pip
pip3 install -r requirements.txt --force-reinstall
```

### データベースエラー
```bash
# データベースを再初期化
python3 scripts/init_database.py
```

### PM2が見つからない場合
```bash
npm install -g pm2
```

## アプリケーションURL
- **メインアプリ**: http://52.69.241.31:5000
- **ログインページ**: http://52.69.241.31:5000/
- **AIチャット**: http://52.69.241.31:5000/chat

## サーバー情報
- **IPアドレス**: 52.69.241.31
- **ユーザー**: ubuntu
- **SSH鍵**: tmhk-chat.pem
- **アプリディレクトリ**: /home/ubuntu/tmhk-chat-server
- **ポート**: 5000

## デプロイ後の確認
1. ブラウザでアプリケーションにアクセス
2. ログイン機能のテスト
3. AIチャット機能のテスト
4. サイドメニューの動作確認
5. PM2ログで エラーがないか確認

```bash
pm2 logs tmhk-chat --lines 100
```
