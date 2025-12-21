# TMHKchat - リアルタイムチャットアプリケーション

TMHKchatは、Flask、Socket.IO、SQLiteを使用したリアルタイムチャットアプリケーションです。グループチャット、個人チャット、AIボット、ミニゲーム、アチーブメントシステムなどの機能を備えています。

## 🚀 クイックスタート

### 必要なもの
- Python 3.12+
- pip (Pythonパッケージマネージャー)
- Git

### ローカル開発環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
cd tmhk-chat-server

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt

# データベースを初期化
python -c "from app import init_db; init_db()"

# アプリケーションを起動
python app.py
```

アプリケーションは http://localhost:5000 で起動します。

## 📁 プロジェクト構造

```
tmhk-chat-server/
├── app.py                      # メインアプリケーション
├── wsgi.py                     # Gunicorn用WSGIエントリーポイント
├── requirements.txt            # Pythonパッケージ依存関係
├── data.sql                    # データベーススキーマ
├── package.json                # Node.js依存関係
├── webpack.config.js           # Webpackビルド設定
├── services/                   # バックエンドサービス
│   ├── ai_bot.py              # AIチャットボット
│   ├── avatar_generator.py    # アバター生成
│   ├── external_data.py       # 外部データ取得
│   ├── profile_manager.py     # プロフィール管理
│   ├── security.py            # セキュリティ・暗号化
│   └── stamp_manager.py       # スタンプ管理
├── templates/                  # HTMLテンプレート
│   ├── index.html             # ログインページ
│   ├── chat.html              # メインチャットUI
│   ├── profile.html           # プロフィールページ
│   ├── admin.html             # 管理者パネル
│   └── tmhk/                  # TMHKchat専用テンプレート
├── static/                     # 静的ファイル
│   ├── css/                   # スタイルシート
│   ├── js/                    # JavaScriptファイル
│   └── assets/                # 画像・アップロードファイル
└── scripts/                    # ユーティリティスクリプト
    ├── check_db.py            # データベース確認
    ├── create_admin.py        # 管理者作成
    └── test_endpoints.py      # エンドポイントテスト
```

## 🎯 主な機能

### チャット機能
- ✅ リアルタイムグループチャット
- ✅ 1対1のプライベートチャット
- ✅ メッセージ暗号化
- ✅ ファイル送信（画像、動画、PDF）
- ✅ タイピングインジケーター
- ✅ 既読管理
- ✅ オフラインメッセージ

### ソーシャル機能
- ✅ 友達管理（フォロー/アンフォロー）
- ✅ ユーザープロフィール
- ✅ アバター自動生成
- ✅ プロフィール画像アップロード
- ✅ 位置情報共有

### AI・外部連携
- ✅ AIチャットボット（OpenAI GPT / Google Gemini）
- ✅ 天気情報取得
- ✅ 列車運行情報取得

### ゲーム機能
- ✅ あみだくじ
- ✅ 大富豪
- ✅ 神経衰弱
- ✅ ババ抜き

### その他
- ✅ アチーブメントシステム
- ✅ スタンプ機能
- ✅ 管理者パネル
- ✅ セキュリティフィルター

## 🛠️ 技術スタック

### バックエンド
- **Flask 3.1.2** - Webフレームワーク
- **Flask-SocketIO 5.5.1** - WebSocket通信
- **SQLite** - データベース
- **Gunicorn** - WSGIサーバー
- **Pillow 11.3.0** - 画像処理（アバター生成）
- **Cryptography 44.0.0** - メッセージ暗号化

### フロントエンド
- **Vanilla JavaScript** - JSXなしの純粋なJavaScript
- **Socket.IO Client 4.x** - リアルタイム通信
- **Bootstrap Icons** - アイコン
- **カスタムCSS** - グラスモーフィズムデザイン

### AI・外部API
- **OpenAI API** - GPTチャットボット
- **Google Gemini API** - 代替AIボット
- **気象庁API** - 天気情報
- **鉄道運行情報API** - 列車情報

## 📚 ドキュメント

- [フロントエンド統合ガイド](README_FRONTEND_INTEGRATION.md) - CSS/JSコンポーネントの使用方法
- [機能詳細](README_FEATURES.md) - 各機能の詳細説明
- [スクレイパー](README_SCRAPERS.md) - 外部データ取得の詳細
- [AI機能](README_AI.md) - AIチャットボットの設定
- [実装レポート](IMPLEMENTATION_REPORT.md) - 開発履歴
- [開発・運用マニュアル](DEVELOPMENT_MANUAL.md) - デプロイ手順

## 🔧 開発ワークフロー

### 1. コードを修正

```bash
# 作業ディレクトリに移動
cd ~/Documents/server  # Windows
# または
cd ~/tmhk-chat-server  # Linux/Mac

# ファイルを編集
# - app.py: メインロジック
# - templates/: HTMLテンプレート
# - static/: CSS/JavaScript
# - requirements.txt: 新しいライブラリを追加した場合
```

### 2. Gitにコミット

```bash
# 変更を確認
git status

# すべての変更をステージング
git add .

# コミット
git commit -m "機能追加: ○○の実装"

# GitHubにプッシュ
git push origin main
```

### 3. サーバーにデプロイ（AWS）

```bash
# サーバーに接続
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31

# プロジェクトディレクトリに移動
cd ~/tmhk-chat-server

# 最新コードを取得
git pull origin main

# 依存関係を更新（requirements.txtを変更した場合）
source venv/bin/activate
pip install -r requirements.txt

# アプリケーションを再起動
pm2 restart tmhk-chat
```

## 🔍 トラブルシューティング

### アプリケーションの状態確認

```bash
# PM2のステータス確認
pm2 list

# ログを確認
pm2 logs tmhk-chat

# ログ表示を停止: Ctrl + C
```

### PM2起動コマンド

```bash
# ディレクトリに移動
cd /home/ubuntu/tmhk-chat-server

# PM2で起動
pm2 start ./venv/bin/gunicorn \
  --name tmhk-chat \
  --interpreter ./venv/bin/python \
  -- --workers 3 --bind unix:chat.sock -m 007 app:app

# 自動起動を有効化
pm2 save
pm2 startup
```

### よくある問題

#### 1. データベースエラー
```bash
# データベースを再初期化
python scripts/check_db.py
```

#### 2. ポート競合
```bash
# プロセスを確認
pm2 list
pm2 stop tmhk-chat
pm2 start tmhk-chat
```

#### 3. パッケージエラー
```bash
# 仮想環境を再作成
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate  # または venv\Scripts\activate
pip install -r requirements.txt
```

## 🔐 環境変数

以下の環境変数を設定してください（`.env`ファイルまたはシステム環境変数）:

```bash
# セキュリティ
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# OpenAI API（オプション）
OPENAI_API_KEY=your-openai-api-key

# Google Gemini API（オプション）
GEMINI_API_KEY=your-gemini-api-key

# データベース
DATABASE_PATH=chat.db

# サーバー設定
FLASK_ENV=production
```

## 🧪 テスト

```bash
# エンドポイントテスト
python scripts/test_endpoints.py

# ログインテスト
python scripts/test_login.py

# データベース確認
python scripts/check_db.py
```

## 📊 管理者機能

### 管理者アカウントの作成

```bash
python scripts/create_admin.py
```

### 管理者パネル

管理者アカウントでログイン後、`/admin`にアクセスすると以下の操作が可能です:

- ユーザー管理（削除、権限変更）
- メッセージ管理（削除、フィルタリング）
- システム統計の確認
- データベースバックアップ

## 🚀 本番環境デプロイ

### Nginx設定例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://unix:/home/ubuntu/tmhk-chat-server/chat.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /socket.io {
        proxy_pass http://unix:/home/ubuntu/tmhk-chat-server/chat.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### SSL/TLS設定（Let's Encrypt）

```bash
# Certbotをインストール
sudo apt-get install certbot python3-certbot-nginx

# SSL証明書を取得
sudo certbot --nginx -d your-domain.com
```

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 👤 作者

- **sakai-tomohiko124**
- GitHub: [@sakai-tomohiko124](https://github.com/sakai-tomohiko124)

## 🔗 リンク

- [リポジトリ](https://github.com/sakai-tomohiko124/tmhk-chat-server)
- [Issues](https://github.com/sakai-tomohiko124/tmhk-chat-server/issues)
- [プルリクエスト](https://github.com/sakai-tomohiko124/tmhk-chat-server/pulls)

## 📞 サポート

問題が発生した場合は、[Issues](https://github.com/sakai-tomohiko124/tmhk-chat-server/issues)で報告してください。

---

**注意**: 本番環境では、必ず環境変数やシークレットキーを適切に設定し、セキュリティ対策を講じてください。
