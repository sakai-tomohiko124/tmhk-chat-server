# TMHKchat Server

リアルタイムチャットアプリケーション with AIアシスタント

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Flask](https://img.shields.io/badge/flask-latest-green.svg)

## 🚀 特徴

- **リアルタイムチャット**: Socket.IOによる即座のメッセージ配信
- **AIアシスタント**: 自動応答機能付きのインテリジェントボット
- **ユーザー管理**: 登録・ログイン・ランキングシステム
- **情報ウィジェット**: 天気予報・電車遅延情報をリアルタイム表示
- **SNS連携**: YouTube、Gmail、Instagram、LINE、TikTok、Twitterへのクイックアクセス
- **管理者機能**: ユーザー管理・チャット監視・手動/自動応答切り替え
- **レスポンシブデザイン**: モバイル・デスクトップ対応

## 🛠️ 技術スタック

### バックエンド
- **Python 3.13**
- **Flask**: Webフレームワーク
- **Flask-SocketIO**: リアルタイム通信
- **SQLite**: データベース
- **BeautifulSoup4**: Webスクレイピング
- **Requests**: HTTP通信

### フロントエンド
- **HTML5/CSS3**: 基本構造・スタイリング
- **JavaScript (ES6+)**: インタラクティブ機能
- **Socket.IO Client**: リアルタイム通信
- **GSAP**: アニメーション
- **Three.js**: パーティクルエフェクト

### インフラ
- **AWS EC2**: サーバーホスティング
- **PM2**: プロセス管理
- **Git/GitHub**: バージョン管理

## 📁 プロジェクト構造

```
tmhk-chat-server/
├── abcd.py                 # メインアプリケーション
├── abc.sql                 # データベーススキーマ
├── qa_data.json           # AI応答データ
├── requirements.txt       # Python依存関係
├── DEVELOPMENT_MANUAL.md  # 開発・運用マニュアル
├── templates/             # HTMLテンプレート
│   ├── base.html         # ベーステンプレート
│   ├── chat.html         # チャット画面
│   ├── login.html        # ログイン画面
│   ├── register.html     # 登録画面
│   ├── admin.html        # 管理者画面
│   ├── loading.html      # ローディング画面
│   └── terms.html        # 利用規約画面
└── static/               # 静的ファイル
    └── (CSSやJavaScriptファイル)
```

## 🚀 セットアップ

### 1. 環境準備
```bash
# リポジトリをクローン
git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
cd tmhk-chat-server

# 仮想環境作成・アクティベート
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 依存関係インストール
pip install -r requirements.txt
```

### 2. データベース初期化
```bash
python abcd.py
```

### 3. 開発サーバー起動
```bash
python abcd.py
```

アプリケーションは `http://localhost:5000` で利用できます。

## 🔧 設定

### 環境変数
以下の環境変数を設定することを推奨します：
```bash
export SECRET_KEY="your-secret-key-here"
export FLASK_ENV="production"  # 本番環境
```

### 管理者アカウント
- **ユーザー名**: `skytomo124`
- **パスワード**: `skytomo124`

## 📊 API エンドポイント

### チャット機能
- `GET /chat` - チャット画面
- `POST /send_message` - メッセージ送信

### 認証
- `GET /login` - ログイン画面
- `POST /login` - ログイン処理
- `GET /register` - 登録画面
- `POST /register` - 登録処理

### 情報API
- `GET /api/weather` - 天気予報取得
- `GET /api/train_delay` - 電車遅延情報取得

### 管理者機能
- `GET /admin` - 管理者ダッシュボード
- `GET /admin/chat/<user_id>` - 個別ユーザーチャット

## 🎨 主要機能

### 1. リアルタイムチャット
- Socket.IOによる双方向通信
- メッセージの即座配信
- オンライン状態表示

### 2. AIアシスタント
- キーワードベースの自動応答
- 管理者による手動/自動切り替え
- 学習可能な応答システム

### 3. 情報ウィジェット
- 気象庁APIからの天気予報
- Yahoo!乗換案内からの電車遅延情報
- 5分間隔の自動更新

### 4. ユーザー管理
- 安全な認証システム
- 所持金（円）ベースのランキング
- 招待コードシステム
- メッセージ送信で1000円獲得
- NG_WORDS検知でペナルティ（全所持金没収）

### 5. メッセージ管理
- メッセージ編集機能（自分のメッセージのみ）
- メッセージ完全削除機能（相手にも削除が反映）
- 管理者による既読管理
- リアルタイム同期

### 6. 外部サービス連携
- YouTube、Gmail、Instagram、LINE、TikTok
- 小説（青空文庫）、天気予報（気象庁）
- 交通機関（Yahoo!路線）、自然災害情報
- ワンクリックアクセス

## 🔒 セキュリティ

- パスワードベース認証
- セッション管理
- XSS/CSRF対策
- SQLインジェクション対策
- 入力値検証
- 完全無料アプリ（金銭要求なし）

## 📱 レスポンシブデザイン

- モバイルファースト設計
- タブレット・デスクトップ対応
- 流動的なレイアウト
- タッチ操作最適化

## 🚀 デプロイ

詳細なデプロイ手順は [DEVELOPMENT_MANUAL.md](./DEVELOPMENT_MANUAL.md) を参照してください。

### 本番環境
- **サーバー**: AWS EC2 (Ubuntu)
- **プロセス管理**: PM2
- **Webサーバー**: Flask開発サーバー
- **データベース**: SQLite

## 🤝 貢献

1. プロジェクトをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 👨‍💻 開発者

**坂井友彦** - [sakai-tomohiko124](https://github.com/sakai-tomohiko124)

## 📞 サポート

問題や質問がある場合は、以下の方法でお気軽にお問い合わせください：
- GitHub Issues
- Email: サポートアドレス（必要に応じて追加）

---

**最終更新**: 2025年10月6日