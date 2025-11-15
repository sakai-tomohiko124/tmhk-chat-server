# TMHKchat - 統合機能ガイド

## 📚 目次

1. [AIボット機能](#aiボット機能)
2. [WebRTC音声/ビデオ通話](#webrtc音声ビデオ通話)
3. [外部データサービス](#外部データサービス)
4. [管理スクリプト](#管理スクリプト)

---

## 🤖 AIボット機能

### 概要
Google Gemini ProとOpenAI GPT-3.5の両方に対応した高度なAIチャットボット機能を提供します。

### 主な機能

#### 1. 基本チャット
- **会話履歴の保持**: ユーザーごとに会話コンテキストを維持
- **ストリーミング応答**: リアルタイムで応答を表示
- **マルチユーザー対応**: 各ユーザーの会話を個別管理

#### 2. 感情分析
```python
# メッセージの感情を分析
result = await ai_bot.analyze_sentiment("今日はとても楽しかったです！")
# => {'sentiment': 'positive', 'score': 0.9, 'emotions': ['喜び', '満足']}
```

#### 3. 会話提案
```python
# 文脈に基づいた返信候補を生成
suggestions = await ai_bot.get_conversation_suggestions("映画を観に行きました")
# => ["面白かったですか？", "どんな映画でしたか？", "また行きたいですか？"]
```

#### 4. コンテンツモデレーション
```python
# 不適切なコンテンツを自動検出
result = await ai_bot.moderate_content(message)
# => {'is_appropriate': False, 'reason': '暴力的表現', 'severity': 'high'}
```

### WebSocketイベント

**クライアント → サーバー:**
```javascript
// OpenAI GPTに送信
socket.emit('send_to_openai', {
    message: 'こんにちは',
    history: conversationHistory
});

// Google Gemini AIに送信
socket.emit('send_to_ai', {
    message: 'こんにちは'
});
```

**サーバー → クライアント:**
```javascript
// OpenAIからのストリーミングチャンク
socket.on('openai_chunk', (data) => {
    console.log(data.content);
});

// 応答完了
socket.on('openai_done', () => {
    console.log('AI response complete');
});
```

---

## 📞 WebRTC音声/ビデオ通話

### 概要
WebRTCを使用したリアルタイム音声/ビデオ通話機能を提供します。

### アーキテクチャ
```
Client A ←→ Signaling Server ←→ Client B
    ↓              ↓              ↓
   WebRTC Peer Connection (P2P)
```

### WebSocketイベント

#### 通話開始
```javascript
// 通話ルームに参加
socket.emit('join_call', {
    user_id: currentUserId,
    room_id: roomId
});

socket.on('call_joined', (data) => {
    console.log('Participants:', data.participants);
});
```

#### シグナリング
```javascript
// Offerの送信
socket.emit('rtc_offer', {
    target: targetUserId,
    sender: currentUserId,
    sdp: offerSDP
});

// Offerの受信
socket.on('rtc_offer', async (data) => {
    const answer = await createAnswer(data.sdp);
    socket.emit('rtc_answer', {
        target: data.sender,
        sender: currentUserId,
        sdp: answer
    });
});

// ICE Candidateの交換
socket.emit('ice_candidate', {
    target: targetUserId,
    sender: currentUserId,
    candidate: iceCandidate
});
```

#### 通話終了
```javascript
socket.emit('leave_call', {
    user_id: currentUserId
});
```

### クライアント実装例

```javascript
// WebRTC接続の初期化
const peerConnection = new RTCPeerConnection({
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
});

// ローカルストリームの取得
const stream = await navigator.mediaDevices.getUserMedia({
    video: true,
    audio: true
});

stream.getTracks().forEach(track => {
    peerConnection.addTrack(track, stream);
});

// リモートストリームの表示
peerConnection.ontrack = (event) => {
    remoteVideo.srcObject = event.streams[0];
};
```

---

## 🌐 外部データサービス

### 概要
天気予報、電車運行情報、災害情報などの外部データを取得・配信します。

### APIエンドポイント

#### 1. 天気予報
```bash
GET /api/external/weather?area=130000
```

**レスポンス:**
```json
{
    "area": "東京地方",
    "weather": "晴れ時々曇り",
    "temperature": {
        "min": "15",
        "max": "23"
    },
    "updated": "2025-11-14T10:00:00"
}
```

#### 2. 電車運行情報
```bash
GET /api/external/trains
```

**レスポンス:**
```json
[
    {
        "company": "JR東日本",
        "name": "山手線",
        "status": "平常運転",
        "updated": "2025-11-14T10:00:00"
    }
]
```

#### 3. 災害情報
```bash
GET /api/external/alerts
```

**レスポンス:**
```json
[
    {
        "title": "大雨警報",
        "content": "神奈川県に大雨警報が発表されています",
        "updated": "2025-11-14T09:30:00",
        "area": "神奈川県"
    }
]
```

### 自動更新機能

サーバー起動時に5分ごとに自動でデータを更新し、WebSocketでブロードキャストします：

```javascript
socket.on('external_data_update', (data) => {
    console.log('Weather:', data.weather);
    console.log('Trains:', data.trains);
    console.log('Alerts:', data.alerts);
});
```

---

## 🛠 管理スクリプト

### データベース確認
```bash
python scripts/check_db.py
```
データベース内のユーザー一覧を表示します。

### エンドポイントテスト
```bash
python scripts/test_endpoints.py
```
主要なエンドポイントの稼働状況を確認します。

### 管理者アカウント作成
```bash
python scripts/create_admin.py
```
`.env`の設定に基づいて管理者アカウントを作成します。

### ログインテスト
```bash
python scripts/test_login.py
```
管理者アカウントでのログイン動作をテストします。

---

## 🚀 セットアップ

### 1. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env`ファイルに以下を追加：
```env
# AI API Keys
GOOGLE_AI_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Redis
REDIS_URL=redis://localhost:6379

# Admin Account
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure_password
```

### 3. データベースの初期化
```bash
flask init-db
python scripts/create_admin.py
```

### 4. アプリの起動
```bash
python app.py
```

---

## 📊 システムアーキテクチャ

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ↓ WebSocket/HTTP
┌─────────────────────────┐
│   Flask Application     │
│  ┌──────────────────┐  │
│  │  SocketIO Server  │  │
│  ├──────────────────┤  │
│  │  AI Bot Service   │  │
│  ├──────────────────┤  │
│  │  RTC Signaling    │  │
│  ├──────────────────┤  │
│  │  External Data    │  │
│  └──────────────────┘  │
└────────┬────────────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌─────┐   ┌──────┐
│Redis│   │SQLite│
└─────┘   └──────┘
```

---

## 🔧 トラブルシューティング

### AIボットが応答しない
1. `.env`にAPIキーが正しく設定されているか確認
2. サーバーログでエラーメッセージを確認
3. APIの利用制限に達していないか確認

### WebRTC通話が接続できない
1. ブラウザがWebRTCに対応しているか確認
2. HTTPSまたはlocalhostで実行しているか確認
3. ファイアウォールの設定を確認

### 外部データが取得できない
1. インターネット接続を確認
2. APIエンドポイントが利用可能か確認
3. レート制限に達していないか確認

---

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。
