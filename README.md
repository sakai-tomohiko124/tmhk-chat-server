# そういう時は、AREだ！ — RPG謎解き（Python標準HTTP + Vanilla JS）

ブラウザで遊べる、章立てのRPG風「リアル謎解き」サイトです。
UI（HTML/CSS/JavaScript）で進行・演出・セーブ/ロードを行い、Python（標準ライブラリのHTTPサーバー）で答え判定とヒントを返します。

## 起動

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

起動後、http://localhost:5000 を開きます。（`PORT` 環境変数で変更可）

## ゲーム仕様

- タイトル：そういう時は、AREだ！
- 主人公：はるや／ももね（＋参加者10名規模）
- 進行：プロローグ参加 → 第1話〜第5話（Q1〜Q10）
- レベル：Lv1から開始、最大Lv100（正解・タイムボーナスでEXP獲得）
- セーブ：ブラウザのlocalStorage（画面右上の「セーブ/ロード」）

## 構成

- [app.py](app.py) : Python標準HTTPサーバー（`/` と `/api/*` と `/static/*`）
- [index.html](index.html) : 画面UI
- [static/css/game.css](static/css/game.css) : RPG風デザイン
- [static/js/game.js](static/js/game.js) : 章立て/タイマー/レベル/進行ロジック

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
