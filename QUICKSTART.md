# 🚀 TMHKchat クイックスタートガイド

このガイドでは、TMHKchatを**5分で起動**する方法を説明します。

## ⚡ 超高速セットアップ

### Windows の場合

1. **リポジトリをクローン**
```cmd
git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
cd tmhk-chat-server
```

2. **自動セットアップを実行**
```cmd
setup.bat
```

3. **アプリケーションを起動**
```cmd
venv\Scripts\activate
python app.py
```

4. **ブラウザでアクセス**
```
http://localhost:5000
```

### Mac / Linux の場合

1. **リポジトリをクローン**
```bash
git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
cd tmhk-chat-server
```

2. **自動セットアップを実行**
```bash
chmod +x setup.sh
./setup.sh
```

3. **アプリケーションを起動**
```bash
source venv/bin/activate
python app.py
```

4. **ブラウザでアクセス**
```
http://localhost:5000
```

---

## 🎯 Makefileを使う方法（推奨）

Makefileを使うと、さらに簡単にコマンドを実行できます。

### 初回セットアップ

```bash
make setup
```

### 開発サーバーを起動

```bash
make dev
```

### 管理者アカウントを作成

```bash
make create-admin
```

### すべてのコマンドを確認

```bash
make help
```

---

## 📋 よく使うコマンド一覧

| コマンド | 説明 |
|---------|------|
| `make setup` | 初回セットアップ |
| `make dev` | 開発サーバー起動 |
| `make test` | テスト実行 |
| `make clean` | キャッシュ削除 |
| `make create-admin` | 管理者作成 |
| `make git-commit` | Git コミット（インタラクティブ） |
| `make git-push` | GitHub にプッシュ |
| `make update` | 最新コードを取得 |

---

## 🔧 環境変数の設定

`.env.example` を `.env` にコピーして編集します：

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

最低限必要な設定：

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_PATH=chat.db
```

AI機能を使う場合（オプション）：

```env
OPENAI_API_KEY=sk-your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
```

---

## 🎮 初回ログイン

### 1. 通常ユーザーとしてログイン

ブラウザで `http://localhost:5000` にアクセスし、好きなユーザー名を入力。

### 2. 管理者アカウントを作成

```bash
# Windows
venv\Scripts\activate
python scripts\create_admin.py

# Mac/Linux
source venv/bin/activate
python scripts/create_admin.py
```

入力例：
```
管理者ユーザー名: admin
管理者パスワード: your-password
```

---

## 🐛 トラブルシューティング

### Python が見つからない

```bash
# Pythonをインストール
# https://www.python.org/downloads/
# Python 3.12以上が必要
python --version
```

### パッケージインストールエラー

```bash
# pipをアップグレード
python -m pip install --upgrade pip

# 再インストール
pip install -r requirements.txt
```

### データベースエラー

```bash
# データベースを再初期化
make db-reset

# または手動で
rm chat.db
python -c "from app import init_db; init_db()"
```

### ポートが使用中

別のポートで起動：

```python
# app.py の最後を編集
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
```

---

## 📚 次のステップ

- [README.md](README.md) - 詳細なドキュメント
- [DEVELOPMENT_MANUAL.md](DEVELOPMENT_MANUAL.md) - 開発・運用マニュアル
- [README_FRONTEND_INTEGRATION.md](README_FRONTEND_INTEGRATION.md) - フロントエンド統合ガイド

---

## 🎉 完了！

これで TMHKchat が起動しました！

- **チャット**: リアルタイムメッセージング
- **ゲーム**: ミニゲームで遊ぶ
- **AI**: AIチャットボットと会話
- **プロフィール**: 自分のプロフィールをカスタマイズ

楽しんでください！ 🚀
