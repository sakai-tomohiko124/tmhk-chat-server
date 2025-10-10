# ARE - 実践的プロジェクト構造

## 📁 完全ディレクトリ構造

```
ARE/
├── backend/                          # Python Flask バックエンド
│   ├── app/                          # メインアプリケーション
│   │   ├── __init__.py               # Flaskアプリ初期化
│   │   ├── config.py                 # 環境別設定（開発・本番）
│   │   ├── extensions.py             # Flask拡張機能（SQLAlchemy, Redis, etc）
│   │   │
│   │   ├── models/                   # データベースモデル
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # ユーザーモデル
│   │   │   ├── message.py            # メッセージモデル
│   │   │   ├── room.py               # チャットルームモデル
│   │   │   ├── friend.py             # 友達関係モデル
│   │   │   ├── media.py              # メディアファイルモデル
│   │   │   ├── call.py               # 通話履歴モデル
│   │   │   ├── story.py              # ストーリーモデル
│   │   │   ├── game.py               # ゲームデータモデル
│   │   │   ├── workspace.py          # ワークスペースモデル
│   │   │   └── notification.py       # 通知モデル
│   │   │
│   │   ├── routes/                   # APIルート（機能別）
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # 認証API（登録・ログイン）
│   │   │   ├── chat.py               # チャットAPI（メッセージ送受信）
│   │   │   ├── friends.py            # 友達管理API
│   │   │   ├── media.py              # メディアアップロード・取得
│   │   │   ├── call.py               # 通話API（WebRTC signaling）
│   │   │   ├── stories.py            # ストーリーAPI
│   │   │   ├── games.py              # ゲームAPI
│   │   │   ├── ai.py                 # AI機能API（Grok統合）
│   │   │   ├── workspace.py          # ワークスペースAPI
│   │   │   ├── user.py               # ユーザープロフィールAPI
│   │   │   └── notification.py       # 通知API
│   │   │
│   │   ├── websocket/                # WebSocket処理
│   │   │   ├── __init__.py
│   │   │   ├── chat.py               # チャットWebSocket
│   │   │   ├── call.py               # 通話WebSocket
│   │   │   ├── presence.py           # オンライン状態管理
│   │   │   └── events.py             # イベントハンドラー
│   │   │
│   │   ├── services/                 # ビジネスロジック
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py       # 認証サービス
│   │   │   ├── chat_service.py       # チャットロジック
│   │   │   ├── media_service.py      # メディア処理
│   │   │   ├── call_service.py       # 通話管理
│   │   │   ├── ai_service.py         # AI統合（Grok API）
│   │   │   ├── storage_service.py    # ファイルストレージ（S3/Supabase）
│   │   │   ├── notification_service.py # 通知配信
│   │   │   ├── encryption_service.py # 暗号化サービス
│   │   │   └── game_service.py       # ゲームロジック
│   │   │
│   │   ├── utils/                    # ユーティリティ
│   │   │   ├── __init__.py
│   │   │   ├── decorators.py         # デコレーター（認証チェック等）
│   │   │   ├── validators.py         # バリデーション
│   │   │   ├── helpers.py            # ヘルパー関数
│   │   │   ├── constants.py          # 定数定義
│   │   │   └── exceptions.py         # カスタム例外
│   │   │
│   │   └── tasks/                    # 非同期タスク（Celery）
│   │       ├── __init__.py
│   │       ├── media_tasks.py        # メディア処理タスク
│   │       ├── notification_tasks.py # 通知送信タスク
│   │       └── cleanup_tasks.py      # クリーンアップタスク
│   │
│   ├── migrations/                   # データベースマイグレーション（Alembic）
│   │   ├── versions/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── script.py.mako
│   │
│   ├── tests/                        # テストコード
│   │   ├── __init__.py
│   │   ├── conftest.py               # pytest設定
│   │   ├── test_auth.py              # 認証テスト
│   │   ├── test_chat.py              # チャットテスト
│   │   ├── test_models.py            # モデルテスト
│   │   └── test_websocket.py         # WebSocketテスト
│   │
│   ├── scripts/                      # 運用スクリプト
│   │   ├── init_db.py                # DB初期化
│   │   ├── seed_data.py              # テストデータ投入
│   │   └── deploy.sh                 # デプロイスクリプト
│   │
│   ├── requirements.txt              # Python依存関係
│   ├── requirements-dev.txt          # 開発用依存関係
│   ├── wsgi.py                       # WSGIエントリーポイント
│   ├── celery_worker.py              # Celeryワーカー
│   └── run.py                        # 開発サーバー起動
│
├── frontend/                         # React フロントエンド
│   ├── public/                       # 静的ファイル
│   │   ├── index.html                # HTMLテンプレート
│   │   ├── manifest.json             # PWA設定
│   │   ├── robots.txt
│   │   ├── favicon.ico
│   │   └── assets/                   # 画像・アイコン・音声
│   │       ├── icons/                # アイコン
│   │       ├── images/               # 画像
│   │       ├── sounds/               # 通知音等
│   │       └── fonts/                # カスタムフォント
│   │
│   ├── src/                          # ソースコード
│   │   ├── main.tsx                  # Reactエントリーポイント
│   │   ├── App.tsx                   # ルートコンポーネント
│   │   ├── vite-env.d.ts             # TypeScript型定義
│   │   │
│   │   ├── components/               # 再利用可能コンポーネント
│   │   │   ├── common/               # 共通コンポーネント
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Avatar.tsx
│   │   │   │   ├── Loading.tsx
│   │   │   │   └── ErrorBoundary.tsx
│   │   │   │
│   │   │   ├── chat/                 # チャット関連
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── MessageItem.tsx
│   │   │   │   ├── ChatInput.tsx
│   │   │   │   ├── EmojiPicker.tsx
│   │   │   │   ├── FileUpload.tsx
│   │   │   │   └── TypingIndicator.tsx
│   │   │   │
│   │   │   ├── call/                 # 通話関連
│   │   │   │   ├── VideoCall.tsx
│   │   │   │   ├── AudioCall.tsx
│   │   │   │   ├── CallControls.tsx
│   │   │   │   ├── ParticipantGrid.tsx
│   │   │   │   └── ScreenShare.tsx
│   │   │   │
│   │   │   ├── friends/              # 友達管理
│   │   │   │   ├── FriendList.tsx
│   │   │   │   ├── FriendCard.tsx
│   │   │   │   ├── FriendRequest.tsx
│   │   │   │   └── QRScanner.tsx
│   │   │   │
│   │   │   ├── stories/              # ストーリー
│   │   │   │   ├── StoryViewer.tsx
│   │   │   │   ├── StoryCreator.tsx
│   │   │   │   └── StoryList.tsx
│   │   │   │
│   │   │   ├── games/                # ゲーム
│   │   │   │   ├── GameList.tsx
│   │   │   │   ├── Daifugo.tsx       # トモヒロウ（大富豪）
│   │   │   │   ├── OldMaid.tsx       # ババ抜き
│   │   │   │   ├── Memory.tsx        # 神経衰弱
│   │   │   │   └── Amidakuji.tsx     # あみだくじ
│   │   │   │
│   │   │   ├── ai/                   # AI機能
│   │   │   │   ├── AIChat.tsx
│   │   │   │   ├── Translation.tsx
│   │   │   │   └── SmartReply.tsx
│   │   │   │
│   │   │   └── workspace/            # ワークスペース
│   │   │       ├── TaskBoard.tsx
│   │   │       ├── Calendar.tsx
│   │   │       └── FileManager.tsx
│   │   │
│   │   ├── pages/                    # ページコンポーネント
│   │   │   ├── HomePage.tsx          # ホーム画面
│   │   │   ├── LoginPage.tsx         # ログイン
│   │   │   ├── RegisterPage.tsx      # 登録
│   │   │   ├── ChatPage.tsx          # チャット画面
│   │   │   ├── FriendsPage.tsx       # 友達管理
│   │   │   ├── ProfilePage.tsx       # プロフィール
│   │   │   ├── SettingsPage.tsx      # 設定
│   │   │   ├── StoriesPage.tsx       # ストーリー
│   │   │   ├── GamesPage.tsx         # ゲーム
│   │   │   ├── AIPage.tsx            # AIチャット
│   │   │   └── WorkspacePage.tsx     # ワークスペース
│   │   │
│   │   ├── layouts/                  # レイアウト
│   │   │   ├── MainLayout.tsx        # メインレイアウト
│   │   │   ├── AuthLayout.tsx        # 認証レイアウト
│   │   │   └── WorkspaceLayout.tsx   # ワークスペースレイアウト
│   │   │
│   │   ├── hooks/                    # カスタムフック
│   │   │   ├── useAuth.ts            # 認証フック
│   │   │   ├── useWebSocket.ts       # WebSocketフック
│   │   │   ├── useChat.ts            # チャットフック
│   │   │   ├── useCall.ts            # 通話フック
│   │   │   ├── useMediaUpload.ts     # メディアアップロード
│   │   │   └── useNotification.ts    # 通知フック
│   │   │
│   │   ├── services/                 # APIサービス
│   │   │   ├── api.ts                # Axiosインスタンス
│   │   │   ├── authService.ts        # 認証API
│   │   │   ├── chatService.ts        # チャットAPI
│   │   │   ├── friendService.ts      # 友達API
│   │   │   ├── mediaService.ts       # メディアAPI
│   │   │   ├── callService.ts        # 通話API
│   │   │   ├── storyService.ts       # ストーリーAPI
│   │   │   ├── gameService.ts        # ゲームAPI
│   │   │   └── aiService.ts          # AI API
│   │   │
│   │   ├── store/                    # 状態管理（Zustand）
│   │   │   ├── authStore.ts          # 認証状態
│   │   │   ├── chatStore.ts          # チャット状態
│   │   │   ├── friendStore.ts        # 友達状態
│   │   │   ├── callStore.ts          # 通話状態
│   │   │   └── uiStore.ts            # UI状態
│   │   │
│   │   ├── types/                    # TypeScript型定義
│   │   │   ├── index.ts
│   │   │   ├── user.ts
│   │   │   ├── message.ts
│   │   │   ├── room.ts
│   │   │   ├── call.ts
│   │   │   └── api.ts
│   │   │
│   │   ├── utils/                    # ユーティリティ
│   │   │   ├── constants.ts          # 定数
│   │   │   ├── helpers.ts            # ヘルパー関数
│   │   │   ├── validators.ts         # バリデーション
│   │   │   └── encryption.ts         # 暗号化ユーティリティ
│   │   │
│   │   └── styles/                   # スタイル
│   │       ├── index.css             # グローバルスタイル
│   │       ├── tailwind.css          # TailwindCSS
│   │       └── themes.css            # テーマ設定
│   │
│   ├── package.json                  # Node.js依存関係
│   ├── package-lock.json
│   ├── tsconfig.json                 # TypeScript設定
│   ├── tsconfig.node.json
│   ├── vite.config.ts                # Vite設定
│   ├── tailwind.config.js            # TailwindCSS設定
│   ├── postcss.config.js             # PostCSS設定
│   └── .env.example                  # 環境変数テンプレート
│
├── deployment/                       # デプロイ設定
│   ├── aws/                          # AWS EC2デプロイ
│   │   ├── nginx.conf                # Nginx設定
│   │   ├── gunicorn.conf.py          # Gunicorn設定
│   │   ├── supervisor.conf           # Supervisor設定
│   │   ├── deploy.sh                 # デプロイスクリプト
│   │   ├── setup_ec2.sh              # EC2初期セットアップ
│   │   └── ssl_setup.sh              # SSL証明書設定
│   │
│   ├── render/                       # Render.comデプロイ
│   │   ├── render.yaml               # Render設定
│   │   ├── build.sh                  # ビルドスクリプト
│   │   └── start.sh                  # 起動スクリプト
│   │
│   ├── docker/                       # Docker設定（オプション）
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── docker-compose.yml
│   │
│   └── systemd/                      # Systemdサービス設定
│       ├── are-backend.service
│       ├── are-celery.service
│       └── are-redis.service
│
├── docs/                             # ドキュメント
│   ├── API.md                        # API仕様書
│   ├── DATABASE.md                   # データベース設計
│   ├── DEPLOYMENT.md                 # デプロイガイド
│   ├── FEATURES.md                   # 機能一覧（124機能詳細）
│   ├── ARCHITECTURE.md               # アーキテクチャ設計
│   └── CONTRIBUTING.md               # 貢献ガイド
│
├── database/                         # データベース関連
│   ├── schema/                       # スキーマ定義
│   │   ├── users.sql
│   │   ├── messages.sql
│   │   ├── rooms.sql
│   │   └── full_schema.sql
│   │
│   └── seeds/                        # シードデータ
│       ├── test_users.sql
│       └── sample_data.sql
│
├── .env.example                      # 環境変数テンプレート
├── .gitignore                        # Git除外設定
├── README.md                         # プロジェクト説明
├── PROJECT_STRUCTURE.md              # このファイル
├── LICENSE                           # ライセンス
└── CHANGELOG.md                      # 変更履歴
```

## 🔧 技術詳細

### バックエンド構成
```python
Flask 3.0+
├── Flask-SQLAlchemy      # ORM
├── Flask-SocketIO        # WebSocket
├── Flask-CORS            # CORS対応
├── Flask-JWT-Extended    # JWT認証
├── Flask-Migrate         # DBマイグレーション
├── Celery                # 非同期タスク
├── Redis                 # キャッシュ・セッション
├── Gunicorn              # WSGIサーバー
└── PostgreSQL            # データベース
```

### フロントエンド構成
```typescript
React 18 + TypeScript
├── Vite                  # ビルドツール
├── TailwindCSS           # スタイリング
├── Zustand               # 状態管理
├── React Router          # ルーティング
├── Socket.io-client      # WebSocket
├── Axios                 # HTTP通信
├── WebRTC API            # 通話機能
└── PWA                   # オフライン対応
```

### 外部サービス
```
Supabase
├── Realtime              # WebSocketチャネル
├── Storage               # ファイルストレージ
├── Auth                  # 認証（オプション）
└── PostgreSQL            # データベース（予備）

Agora.io
├── Voice Call            # 音声通話
├── Video Call            # ビデオ通話
└── Recording             # 通話録音

Grok API
├── Chat                  # AIチャット
├── Translation           # 自動翻訳
└── Smart Reply           # スマート返信
```

## 📊 データベース設計

### 主要テーブル
- **users**: ユーザー情報
- **messages**: メッセージ
- **rooms**: チャットルーム
- **room_members**: ルームメンバー
- **friends**: 友達関係
- **friend_requests**: 友達リクエスト
- **media**: メディアファイル
- **calls**: 通話履歴
- **stories**: ストーリー投稿
- **story_views**: ストーリー閲覧履歴
- **games**: ゲームデータ
- **game_scores**: ゲームスコア
- **workspaces**: ワークスペース
- **tasks**: タスク
- **notifications**: 通知

## 🚀 デプロイフロー

### AWS EC2（本番環境）
1. EC2インスタンス起動
2. Nginx + Gunicorn設定
3. PostgreSQL RDS設定
4. S3バケット作成
5. CloudFront CDN設定
6. SSL証明書取得（Let's Encrypt）
7. バックエンドデプロイ
8. フロントエンドビルド＆S3アップロード

### Render.com（検証環境）
1. GitHubリポジトリ連携
2. Web Service作成（Flask）
3. PostgreSQL作成
4. 環境変数設定
5. 自動デプロイ設定

## 🔐 環境変数

### バックエンド (.env)
```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@host:5432/are_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-jwt-secret
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_S3_BUCKET=your-s3-bucket
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
AGORA_APP_ID=your-agora-app-id
AGORA_APP_CERTIFICATE=your-agora-cert
GROK_API_KEY=your-grok-api-key
```

### フロントエンド (.env)
```bash
VITE_API_URL=https://api.are-app.com
VITE_WS_URL=wss://api.are-app.com
VITE_AGORA_APP_ID=your-agora-app-id
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_KEY=your-supabase-anon-key
```

## 📝 次のステップ

1. ✅ プロジェクト構造設計完了
2. ⏳ バックエンド基本構造作成
3. ⏳ フロントエンド基本構造作成
4. ⏳ データベーススキーマ設計
5. ⏳ 認証システム実装
6. ⏳ チャット機能実装
7. ⏳ AWS EC2デプロイ設定
8. ⏳ Render.comデプロイ設定

---
**作成日**: 2025-10-10
**担当**: あかね（フルスタックエンジニアAI）
