// チャット機能のJavaScript

let socket;
let currentUserId;
let currentRoomId;
let typingTimeout;

// 初期化
document.addEventListener('DOMContentLoaded', function() {
    // URLパラメータから部屋IDとユーザーIDを取得
    const params = new URLSearchParams(window.location.search);
    currentRoomId = params.get('room_id') || 'general';
    currentUserId = localStorage.getItem('userId') || '1';
    
    initializeSocket();
    loadStamps();
});

// Socket.IO初期化
function initializeSocket() {
    socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
    });

    socket.on('connect', () => {
        console.log('Socket接続確立');
        socket.emit('join_room', {
            room_id: currentRoomId,
            user_id: currentUserId
        });
    });

    socket.on('disconnect', () => {
        console.log('Socket切断');
    });

    socket.on('new_message', (data) => {
        displayMessage(data);
    });

    socket.on('typing', (data) => {
        if (data.user_id !== currentUserId) {
            showTypingIndicator(data.username);
        }
    });

    socket.on('stop_typing', () => {
        hideTypingIndicator();
    });

    socket.on('user_online', (data) => {
        updateOnlineStatus(true);
    });

    socket.on('user_offline', (data) => {
        updateOnlineStatus(false);
    });
}

// メッセージ送信
function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();
    
    if (!content) return;
    
    const message = {
        room_id: currentRoomId,
        user_id: currentUserId,
        content: content,
        timestamp: new Date().toISOString()
    };

    socket.emit('send_message', message);
    
    // 自分のメッセージを即座に表示
    displayMessage({
        ...message,
        is_sent: true
    });
    
    input.value = '';
    autoResizeTextarea(input);
}

// メッセージ表示
function displayMessage(data) {
    const messagesArea = document.getElementById('messagesArea');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${data.is_sent || data.user_id === currentUserId ? 'sent' : 'received'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = data.content;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = formatTime(data.timestamp);
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    messagesArea.appendChild(messageDiv);
    
    // 最下部にスクロール
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

// タイピング通知
function handleTyping() {
    socket.emit('typing', {
        room_id: currentRoomId,
        user_id: currentUserId
    });

    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        socket.emit('stop_typing', {
            room_id: currentRoomId,
            user_id: currentUserId
        });
    }, 1000);
}

// タイピングインジケーター表示
function showTypingIndicator(username) {
    const indicator = document.getElementById('typingIndicator');
    const text = indicator.querySelector('.typing-text');
    text.textContent = `${username || 'ユーザー'}が入力中`;
    indicator.style.display = 'block';
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'none';
}

// オンラインステータス更新
function updateOnlineStatus(isOnline) {
    const status = document.getElementById('onlineStatus');
    status.textContent = isOnline ? 'オンライン' : 'オフライン';
    status.style.color = isOnline ? '#44b700' : '#999';
}

// キーボードイベント処理
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// テキストエリア自動リサイズ
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

document.getElementById('messageInput').addEventListener('input', function() {
    autoResizeTextarea(this);
});

// 時刻フォーマット
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 添付メニュー
function showAttachmentMenu() {
    const menu = document.getElementById('attachmentMenu');
    menu.style.display = menu.style.display === 'none' ? 'flex' : 'none';
}

function toggleChatMenu() {
    // チャットメニュー実装（後で追加）
    alert('チャットメニュー（開発中）');
}

// 画像選択
function selectImage() {
    document.getElementById('imageInput').click();
    showAttachmentMenu();
}

function selectFile() {
    document.getElementById('fileInput').click();
    showAttachmentMenu();
}

function uploadImage(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append('image', input.files[0]);
        formData.append('room_id', currentRoomId);
        formData.append('user_id', currentUserId);

        fetch('/api/upload_image', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                socket.emit('send_message', {
                    room_id: currentRoomId,
                    user_id: currentUserId,
                    content: `[画像: ${data.filename}]`,
                    message_type: 'image',
                    timestamp: new Date().toISOString()
                });
            }
        })
        .catch(error => console.error('画像アップロードエラー:', error));
    }
}

function uploadFile(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append('file', input.files[0]);
        formData.append('room_id', currentRoomId);
        formData.append('user_id', currentUserId);

        fetch('/api/upload_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                socket.emit('send_message', {
                    room_id: currentRoomId,
                    user_id: currentUserId,
                    content: `[ファイル: ${data.filename}]`,
                    message_type: 'file',
                    timestamp: new Date().toISOString()
                });
            }
        })
        .catch(error => console.error('ファイルアップロードエラー:', error));
    }
}

// スタンプ機能
function showStampPicker() {
    const picker = document.getElementById('stampPicker');
    picker.style.display = 'flex';
    showAttachmentMenu();
}

function closeStampPicker() {
    const picker = document.getElementById('stampPicker');
    picker.style.display = 'none';
}

function loadStamps() {
    fetch('/api/stamps')
        .then(response => response.json())
        .then(data => {
            displayStampCategories(data.categories);
            displayStamps(data.stamps);
        })
        .catch(error => console.error('スタンプ読み込みエラー:', error));
}

function displayStampCategories(categories) {
    const container = document.getElementById('stampCategories');
    categories.forEach(category => {
        const btn = document.createElement('button');
        btn.textContent = category;
        btn.onclick = () => filterStampsByCategory(category);
        container.appendChild(btn);
    });
}

function displayStamps(stamps) {
    const grid = document.getElementById('stampGrid');
    grid.innerHTML = '';
    
    stamps.forEach(stamp => {
        const item = document.createElement('div');
        item.className = 'stamp-item';
        item.onclick = () => sendStamp(stamp.id);
        
        const img = document.createElement('img');
        img.src = `/static/stamps/${stamp.filename}`;
        img.alt = stamp.category;
        
        item.appendChild(img);
        grid.appendChild(item);
    });
}

function filterStampsByCategory(category) {
    fetch(`/api/stamps?category=${category}`)
        .then(response => response.json())
        .then(data => {
            displayStamps(data.stamps);
        });
}

function sendStamp(stampId) {
    socket.emit('send_message', {
        room_id: currentRoomId,
        user_id: currentUserId,
        content: `[スタンプ: ${stampId}]`,
        message_type: 'stamp',
        timestamp: new Date().toISOString()
    });
    closeStampPicker();
}
