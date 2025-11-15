# TMHKchat フロントエンド統合ガイド

## 概要

このドキュメントは、TMHKchatアプリケーションのフロントエンド統合を説明します。すべてのコンポーネントは**JSXを使わず**、純粋なHTML、CSS、JavaScriptで実装されています。

## ディレクトリ構造

```
/workspaces/tmhk-chat-server/
├── static/
│   ├── css/
│   │   ├── main_app.css      # メインアプリケーションスタイル
│   │   ├── loading.css        # ローディング画面スタイル
│   │   └── style.css          # グローバルスタイル
│   ├── js/
│   │   ├── main_app.js        # メインアプリケーションロジック
│   │   ├── chat-socket.js     # Socket.IO統合
│   │   └── components/
│   │       └── achievement.js # アチーブメント管理
│   └── assets/
│       ├── uploads/           # ユーザーアップロードファイル
│       └── images/            # 画像アセット
└── templates/
    ├── tmhk/                  # TMHKchat専用テンプレート
    ├── index.html             # ログインページ
    ├── chat.html              # メインチャットUI
    ├── chat_room.html         # チャットルームUI
    └── profile.html           # プロフィールページ
```

## CSSファイル

### 1. style.css (グローバルスタイル)

**用途**: アプリケーション全体の基本スタイル、CSS変数、ユーティリティクラス

**主な機能**:
- CSS変数定義 (色、サイズ、トランジション)
- リセットスタイル
- タイポグラフィ
- グリッドシステム (12カラム)
- フォームコントロール
- ボタンスタイル
- アラート
- カード
- レスポンシブデザイン

**使用例**:
```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
  <div class="container">
    <div class="row">
      <div class="col-6">
        <div class="card">
          <div class="card-header">タイトル</div>
          <div class="card-body">コンテンツ</div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
```

### 2. main_app.css (メインアプリケーション)

**用途**: メインアプリケーションの特定のコンポーネントスタイル

**主な機能**:
- タブナビゲーション
- モーダルダイアログ
- カードコンポーネント
- ボタンバリエーション
- グラスモーフィズムエフェクト

**使用例**:
```html
<link rel="stylesheet" href="/static/css/main_app.css">

<div class="nav-tabs">
  <button class="nav-tab active">チャット</button>
  <button class="nav-tab">友達</button>
  <button class="nav-tab">設定</button>
</div>

<div class="tab-content">
  <div class="tab-pane active">チャット内容</div>
  <div class="tab-pane">友達リスト</div>
  <div class="tab-pane">設定画面</div>
</div>
```

### 3. loading.css (ローディング画面)

**用途**: アプリケーション起動時のローディング画面

**主な機能**:
- ローディングスピナー
- プログレスバー
- パーティクルアニメーション
- フェードアウトトランジション

**使用例**:
```html
<link rel="stylesheet" href="/static/css/loading.css">

<div class="loading-container">
  <div class="loading-logo">TMHKChat</div>
  <div class="loading-spinner">
    <div class="spinner-circle"></div>
  </div>
  <div class="loading-text">読み込み中<span class="loading-dots"></span></div>
  <div class="loading-progress">
    <div class="loading-progress-bar"></div>
  </div>
  <div class="particles">
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
  </div>
</div>

<script>
  // ローディング完了後にフェードアウト
  window.addEventListener('load', () => {
    setTimeout(() => {
      document.querySelector('.loading-container').classList.add('fade-out');
    }, 1000);
  });
</script>
```

## JavaScriptファイル

### 1. main_app.js (メインアプリケーションロジック)

**用途**: アプリケーション全体で使用する共通機能

**主なクラス**:

#### TabManager
タブナビゲーションの管理

```javascript
// 自動初期化 (data属性を使用)
// HTML:
<button class="nav-tab">タブ1</button>
<div class="tab-pane">内容1</div>

// 手動初期化:
const tabManager = new TMHKChat.TabManager('.nav-tab', '.tab-pane');
tabManager.switchTab(0); // 最初のタブに切り替え
tabManager.restoreTab(); // 保存されたタブを復元
```

#### ModalManager
モーダルダイアログの管理

```javascript
// HTML:
<button data-modal="myModal">モーダルを開く</button>
<div id="myModal" class="modal">
  <div class="modal-content">
    <button class="modal-close">×</button>
    <div class="modal-body">内容</div>
  </div>
</div>

// JS (自動初期化):
const modalManager = new TMHKChat.ModalManager();
// 手動操作:
modalManager.open('myModal');
modalManager.close('myModal');
```

#### Toast
トースト通知の表示

```javascript
// グローバルインスタンスを使用
window.toast.show('成功しました', 'success', 3000);
window.toast.show('エラーが発生しました', 'error', 5000);
window.toast.show('警告メッセージ', 'warning');
window.toast.show('情報メッセージ', 'info');
```

#### FormValidator
フォームバリデーション

```javascript
// HTML:
<form id="myForm" data-validate>
  <input type="text" name="username" required minlength="3" maxlength="20">
  <input type="email" name="email" required>
  <button type="submit">送信</button>
</form>

// JS (自動初期化):
// data-validate属性があれば自動で初期化されます
```

#### StorageManager
LocalStorageの操作

```javascript
// データ保存
TMHKChat.StorageManager.set('userData', { name: 'Taro', age: 25 });

// データ取得
const user = TMHKChat.StorageManager.get('userData');

// データ削除
TMHKChat.StorageManager.remove('userData');

// すべて削除
TMHKChat.StorageManager.clear();
```

#### Utils
ユーティリティ関数

```javascript
const Utils = TMHKChat.Utils;

// デバウンス (連続実行を防ぐ)
const debouncedSearch = Utils.debounce((query) => {
  console.log('検索:', query);
}, 300);

// スロットル (実行頻度を制限)
const throttledScroll = Utils.throttle(() => {
  console.log('スクロール中');
}, 100);

// 日時フォーマット
const formatted = Utils.formatDate(new Date(), 'YYYY-MM-DD HH:mm:ss');

// HTMLエスケープ
const safe = Utils.escapeHtml('<script>alert("XSS")</script>');

// クリップボードにコピー
Utils.copyToClipboard('コピーするテキスト')
  .then(() => console.log('コピー成功'))
  .catch(err => console.error('コピー失敗', err));
```

### 2. chat-socket.js (Socket.IO統合)

**用途**: リアルタイムチャット機能の実装

**主なクラス**:

#### ChatSocket
Socket.IO接続とメッセージング

```javascript
// 初期化
const chatSocket = new ChatSocket({
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5
});

// ルームに参加
chatSocket.joinRoom('general', { username: 'Taro' });

// メッセージ送信
chatSocket.sendMessage('こんにちは', 'general');

// ファイル送信
const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  chatSocket.sendFile(file, 'general', (progress) => {
    console.log(`アップロード中: ${progress}%`);
  });
});

// タイピング通知
chatSocket.sendTyping(true, 'general', 'Taro');

// メッセージ受信
chatSocket.onMessage((message) => {
  console.log('新しいメッセージ:', message);
});

// オフラインメッセージ受信
chatSocket.onOfflineMessages((messages) => {
  messages.forEach(msg => console.log('オフラインメッセージ:', msg));
});

// タイピング通知受信
chatSocket.onTyping((data) => {
  console.log(`${data.username} が入力中...`);
});

// ユーザーリスト更新
chatSocket.onUserListUpdate((users) => {
  console.log('オンラインユーザー:', users);
});

// 既読マーク
chatSocket.markAsRead('general');

// 切断
chatSocket.disconnect();
```

#### ChatUI
チャットUI管理

```javascript
// 初期化
const chatUI = new ChatUI('chat-container');

// メッセージ表示
chatUI.renderMessage({
  username: 'Taro',
  message: 'こんにちは',
  timestamp: new Date().toISOString()
}, false, true); // isMine=false, safe=true

// ファイル表示
chatUI.renderMessage({
  username: 'Hanako',
  file_path: 'image.jpg',
  file_type: 'image',
  timestamp: new Date().toISOString()
}, false, true);

// タイピング表示
chatUI.showTypingIndicator('Taro');

// タイピング非表示
chatUI.hideTypingIndicator();

// 最下部にスクロール
chatUI.scrollToBottom();
```

**統合例**:
```javascript
// チャット完全実装
const chatSocket = new ChatSocket();
const chatUI = new ChatUI('chat-window');
const currentRoom = 'general';
const currentUser = 'Taro';

// ルーム参加
chatSocket.joinRoom(currentRoom, { username: currentUser });

// メッセージ受信時
chatSocket.onMessage((message) => {
  const isMine = message.username === currentUser;
  chatUI.renderMessage(message, isMine, message.safe !== false);
});

// メッセージ送信フォーム
document.getElementById('message-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('message-input');
  const message = input.value.trim();
  
  if (message) {
    chatSocket.sendMessage(message, currentRoom);
    input.value = '';
  }
});

// タイピング通知
let typingTimeout;
document.getElementById('message-input').addEventListener('input', () => {
  chatSocket.sendTyping(true, currentRoom, currentUser);
  
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    chatSocket.sendTyping(false, currentRoom, currentUser);
  }, 2000);
});
```

### 3. achievement.js (アチーブメント管理)

**用途**: ユーザーアチーブメント(実績)システム

**使用方法**:

```javascript
// 初期化 (自動: #achievement-container が存在する場合)
// 手動初期化:
const achievement = new Achievement('achievement-container', {
  autoSave: true,
  storageKey: 'user_achievements',
  showNotifications: true
});

// アチーブメント解除
achievement.unlock('first_message');
achievement.unlock('ten_messages');

// 解除状態確認
const isUnlocked = achievement.isUnlocked('first_message'); // true/false

// 進捗取得
const progress = achievement.getProgress();
console.log(progress);
// {
//   total: 12,
//   unlocked: 3,
//   percentage: 25,
//   points: 80
// }

// リセット
achievement.reset();
```

**HTML構造**:
```html
<link rel="stylesheet" href="/static/css/style.css">
<link rel="stylesheet" href="/static/css/main_app.css">
<script src="/static/js/main_app.js"></script>
<script src="/static/js/components/achievement.js"></script>

<div id="achievement-container"></div>
```

**デフォルトアチーブメント一覧**:

| ID | タイトル | 説明 | ポイント | カテゴリ |
|----|---------|------|---------|---------|
| first_message | 初めてのメッセージ | 初めてのメッセージを送信 | 10 | basic |
| ten_messages | おしゃべり好き | 10件のメッセージを送信 | 50 | basic |
| first_friend | 初めての友達 | 初めて友達を追加 | 20 | social |
| five_friends | 人気者 | 5人の友達を追加 | 100 | social |
| first_group | グループリーダー | 初めてグループを作成 | 30 | group |
| photo_upload | フォトグラファー | 初めて写真をアップロード | 15 | media |
| video_upload | ビデオクリエイター | 初めて動画をアップロード | 25 | media |
| profile_complete | プロフィール完成 | プロフィールを完全に入力 | 40 | profile |
| night_owl | 夜更かし | 深夜0時以降にメッセージ送信 | 5 | special |
| early_bird | 早起き | 午前5時前にメッセージ送信 | 5 | special |
| week_streak | 継続は力なり | 7日連続でログイン | 75 | streak |
| game_master | ゲームマスター | ミニゲームで初勝利 | 50 | game |

## 完全な統合例

### チャットアプリケーション

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TMHKChat</title>
  
  <!-- CSS -->
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="stylesheet" href="/static/css/main_app.css">
  
  <!-- Socket.IO -->
  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
</head>
<body>
  <!-- タブナビゲーション -->
  <div class="nav-tabs">
    <button class="nav-tab active">チャット</button>
    <button class="nav-tab">友達</button>
    <button class="nav-tab">アチーブメント</button>
  </div>

  <!-- タブコンテンツ -->
  <div class="tab-content">
    <!-- チャットタブ -->
    <div class="tab-pane active">
      <div id="chat-window" class="chat-messages"></div>
      <div id="typing-indicator"></div>
      <form id="message-form">
        <input type="text" id="message-input" placeholder="メッセージを入力..." autocomplete="off">
        <button type="submit">送信</button>
      </form>
    </div>

    <!-- 友達タブ -->
    <div class="tab-pane">
      <div id="friends-list"></div>
    </div>

    <!-- アチーブメントタブ -->
    <div class="tab-pane">
      <div id="achievement-container"></div>
    </div>
  </div>

  <!-- JavaScript -->
  <script src="/static/js/main_app.js"></script>
  <script src="/static/js/chat-socket.js"></script>
  <script src="/static/js/components/achievement.js"></script>
  
  <script>
    // 初期化
    const chatSocket = new ChatSocket();
    const chatUI = new ChatUI('chat-window');
    const currentRoom = 'general';
    const currentUser = 'Taro'; // ログインユーザー名

    // ルーム参加
    chatSocket.joinRoom(currentRoom, { username: currentUser });

    // メッセージ受信
    chatSocket.onMessage((message) => {
      chatUI.renderMessage(message, message.username === currentUser, message.safe !== false);
      
      // アチーブメント解除
      if (window.achievementManager && message.username === currentUser) {
        window.achievementManager.unlock('first_message');
      }
    });

    // メッセージ送信
    document.getElementById('message-form').addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('message-input');
      const message = input.value.trim();
      
      if (message) {
        chatSocket.sendMessage(message, currentRoom);
        input.value = '';
      }
    });

    // タイピング通知
    let typingTimeout;
    document.getElementById('message-input').addEventListener('input', () => {
      chatSocket.sendTyping(true, currentRoom, currentUser);
      clearTimeout(typingTimeout);
      typingTimeout = setTimeout(() => {
        chatSocket.sendTyping(false, currentRoom, currentUser);
      }, 2000);
    });

    chatSocket.onTyping((data) => {
      chatUI.showTypingIndicator(data.username);
      setTimeout(() => chatUI.hideTypingIndicator(), 3000);
    });
  </script>
</body>
</html>
```

## 既存テンプレートとの統合

既存のテンプレート (`templates/chat.html`, `templates/profile.html` など) に新しいコンポーネントを統合する場合:

1. **CSSを追加**:
```html
<link rel="stylesheet" href="/static/css/style.css">
<link rel="stylesheet" href="/static/css/main_app.css">
```

2. **JSを追加**:
```html
<script src="/static/js/main_app.js"></script>
<script src="/static/js/chat-socket.js"></script>
```

3. **既存のSocket.IO接続を置き換え** (オプション):
```javascript
// 既存コード:
// const socket = io();

// 新しいコード:
const chatSocket = new ChatSocket();
const socket = chatSocket.socket; // 互換性のため
```

## ブラウザ互換性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 注意事項

1. すべてのJavaScriptファイルは純粋なVanilla JSで書かれており、JSXやReactは使用していません
2. Socket.IOクライアントライブラリ (v4.x) が必要です
3. LocalStorageを使用しているため、プライベートブラウジングモードでは一部機能が制限されます
4. ファイルアップロードは既存のFlaskエンドポイント (`/upload_chunk`) と統合されています

## トラブルシューティング

### Socket.IO接続エラー
```javascript
chatSocket.on('error', (error) => {
  console.error('Socket error:', error);
  window.toast.show('接続エラーが発生しました', 'error');
});
```

### LocalStorage容量エラー
```javascript
try {
  TMHKChat.StorageManager.set('key', largeData);
} catch (error) {
  console.error('Storage error:', error);
  window.toast.show('データ保存に失敗しました', 'error');
}
```

## まとめ

このフロントエンド統合により、以下が実現できます:

- ✅ JSXを使わない純粋なHTML/CSS/JavaScript実装
- ✅ リアルタイムチャット機能
- ✅ アチーブメントシステム
- ✅ モーダル、タブ、トースト通知などのUIコンポーネント
- ✅ フォームバリデーション
- ✅ LocalStorage管理
- ✅ レスポンシブデザイン
- ✅ Socket.IO統合

すべてのコンポーネントは独立して使用でき、既存のFlaskアプリケーションに簡単に統合できます。
