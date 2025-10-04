// エラーハンドリング強化
(function() {
    'use strict';
    
    // グローバルエラーハンドラー
    window.addEventListener('error', function(event) {
        console.error('JavaScript Error:', {
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            error: event.error
        });
        
        // 重要なエラーをサーバーに報告
        if (event.error && event.error.stack) {
            fetch('/api/log-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    message: event.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    stack: event.error.stack
                })
            }).catch(err => console.log('Error reporting failed:', err));
        }
    });
    
    // Promise rejection エラーハンドラー
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled Promise Rejection:', event.reason);
        event.preventDefault();
    });
    
    // CSRF トークン取得関数
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
    
    // 安全なHTTP リクエスト関数
    window.safeRequest = function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        };
        
        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };
        
        return fetch(url, mergedOptions)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('Request failed:', error);
                throw error;
            });
    };
})();

document.addEventListener('DOMContentLoaded', function() {
    const socket = io();

    // ===== 禁止語違反オーバーレイ生成 =====
    const violationOverlay = document.createElement('div');
    violationOverlay.id = 'forbiddenOverlay';
    Object.assign(violationOverlay.style, {
        position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
        background: 'rgba(0,0,0,0.85)', color: '#fff', zIndex: 10000,
        display: 'none', justifyContent: 'center', alignItems: 'center', flexDirection: 'column',
        textAlign: 'center', padding: '20px', animation: 'screenFlash 0.6s linear infinite'
    });
    violationOverlay.innerHTML = `
        <h2 style="font-weight:700;margin-bottom:1rem;">⚠ 警告 ⚠</h2>
        <p id="violationMessage" style="max-width:600px;margin:0 auto 1.2rem;line-height:1.5"></p>
        <button id="apologyBtn" class="btn btn-warning btn-lg mb-3">ごめんなさい</button>
        <small class="text-muted d-block" style="opacity:.7;">※ これは脅しや請求ではありません。ページを閉じれば解除されます。</small>
    `;
    document.body.appendChild(violationOverlay);
    const apologyBtn = violationOverlay.querySelector('#apologyBtn');
    apologyBtn.addEventListener('click', ()=>{
        violationOverlay.style.display='none';
        document.body.classList.remove('forbidden-flash');
    });
    const styleEl = document.createElement('style');
    styleEl.textContent = `@keyframes screenFlash {0%,100%{background:rgba(100,0,0,0.9);}50%{background:rgba(180,0,0,0.6);} } .forbidden-flash{animation:screenFlash 0.8s linear infinite;}`;
    document.head.appendChild(styleEl);

    socket.on('forbidden_violation', data => {
        const msgEl = document.getElementById('violationMessage');
        msgEl.textContent = data.message || '不適切な語が検出されました。';
        violationOverlay.style.display='flex';
        document.body.classList.add('forbidden-flash');
    });

    let idleTimer;
    const idleTimeout = 300000; // 5分 (300,000ミリ秒)
    let currentUserStatus = 'online';

    // ユーザーが放置状態から復帰したか、または放置状態になったことを検知してサーバーに通知する関数
    function resetIdleTimer() {
        clearTimeout(idleTimer);

        // もしステータスが'away'（黄色）だったら、'online'（緑色）に戻す
        if (currentUserStatus === 'away') {
            currentUserStatus = 'online';
            socket.emit('update_user_status', { status: 'online' });
            if(localCurrentUserId) {
                updateStatusIndicator(localCurrentUserId, 'online');
            }
        }

        // 新しいタイマーをセット。このタイマーが完了すると放置状態になる
        idleTimer = setTimeout(() => {
            currentUserStatus = 'away';
            socket.emit('update_user_status', { status: 'away' });
            if(localCurrentUserId) {
                updateStatusIndicator(localCurrentUserId, 'away');
            }
        }, idleTimeout);
    }

    // ページ上で何か操作があったらタイマーをリセットする
    window.onload = resetIdleTimer;
    document.onmousemove = resetIdleTimer;
    document.onkeypress = resetIdleTimer;
    document.onclick = resetIdleTimer;
    
    // ログイン中のユーザーIDをHTMLから取得
    const localCurrentUserId = typeof currentUserId !== 'undefined' ? currentUserId : null;

    function updateStatusIndicator(userId, status) {
        const elements = document.querySelectorAll(`[data-user-id="${userId}"]`);
        elements.forEach(el => {
            el.classList.remove('status-online', 'status-away', 'status-offline');
            if (status) {
                el.classList.add(`status-${status}`);
            } else {
                el.classList.add('status-offline'); // デフォルトはオフライン
            }
        });
    }

    socket.on('status_changed', function(data) {
        updateStatusIndicator(data.user_id, data.status);
    });

    // 管理者: 全ユーザ状態受信
    socket.on('admin_all_user_statuses', function(data){
        if(!data || !data.statuses) return;
        for(const uid in data.statuses){
            updateStatusIndicator(uid, data.statuses[uid]);
        }
        console.log('Admin received all user statuses');
    });

    socket.on('initial_friend_statuses', function(data) {
        for (const userId in data.statuses) {
            updateStatusIndicator(userId, data.statuses[userId]);
        }
    });

    socket.on('connect', () => {
        console.log('Connected to server with SocketIO.');
    });

    socket.on('friend_request_rejected', function(data) {
        alert(data.rejector_username + 'さんに友達リクエストを拒否されました。');
    });

    socket.on('friend_accepted_notification', function(data) {
        if (confirm(data.acceptor_username + 'さんに友達リクエストが承認されました！ページをリロードして友達リストを更新します。')) {
            location.reload();
        }
    });

    socket.on('friend_request_received', function(data) {
        // 'friends_page_url'変数は、main_app.html内の<script>で定義されていることを前提とする
        if (confirm(data.sender_username + 'さんから友達リクエストが届きました。友達管理ページに移動しますか？')) {
            if (typeof friends_page_url !== 'undefined') {
                window.location.href = friends_page_url;
            } else {
                console.error('friends_page_url is not defined.');
            }
        }
    });

    const navButtons = document.querySelectorAll('.nav-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const headerTitle = document.getElementById('header-title');
    const tabTitles = {'home-tab': 'ホーム', 'talk-tab': 'トーク', 'timeline-tab': 'タイムライン', 'other-tab': 'その他'};

    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(targetTab).classList.add('active');
            headerTitle.textContent = tabTitles[targetTab] || 'TMHKchat';
        });
    });

    const talkFilterSelect = document.getElementById('talk-filter-select');
    if (talkFilterSelect) {
        talkFilterSelect.addEventListener('change', function() {
            const selectedFilter = this.value;
            window.location.href = `/app?talk_filter=${selectedFilter}`;
        });
    }
});

// サーバーシャットダウン関数は、HTMLから呼び出されるようにグローバルスコープに配置
function shutdownServer() {
    if (confirm('本当にサーバーをシャットダウンして終了しますか？')) {
        fetch('/shutdown', {
            method: 'POST'
        }).then(response => {
            // レスポンスを受け取った後、少し待ってからアラートとタブを閉じる
            setTimeout(() => {
                window.alert('サーバーがシャットダウンされました。このタブを閉じます。');
                window.close(); // ブラウザの設定によっては閉じられない場合があります
            }, 500); // 0.5秒待つ
        }).catch(error => {
            console.error('Shutdown error:', error);
            window.alert('サーバーのシャットダウンに失敗しました。');
        });
    }
}