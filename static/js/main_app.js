/*
 * TMHKchat メインアプリケーション用JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    let idleTimer;
    const idleTimeout = 300000; // 5分
    let currentUserStatus = 'online';

    // ログイン中のユーザーIDをHTMLから取得
    // main_app.html内の <script> タグで 'currentUserId' 変数が定義されていることを前提とする
    const localCurrentUserId = typeof currentUserId !== 'undefined' ? currentUserId : null;

    function resetIdleTimer() {
        clearTimeout(idleTimer);
        if (currentUserStatus === 'away') {
            currentUserStatus = 'online';
            socket.emit('update_user_status', { status: 'online' });
            if(localCurrentUserId) {
                updateStatusIndicator(localCurrentUserId, 'online');
            }
        }
        idleTimer = setTimeout(() => {
            currentUserStatus = 'away';
            socket.emit('update_user_status', { status: 'away' });
            if(localCurrentUserId) {
                updateStatusIndicator(localCurrentUserId, 'away');
            }
        }, idleTimeout);
    }

    window.onload = resetIdleTimer;
    document.onmousemove = resetIdleTimer;
    document.onkeypress = resetIdleTimer;
    document.onclick = resetIdleTimer;

    function updateStatusIndicator(userId, status) {
        const elements = document.querySelectorAll(`[data-user-id="${userId}"]`);
        elements.forEach(el => {
            el.classList.remove('status-online', 'status-away', 'status-offline');
            if (status) {
                el.classList.add(`status-${status}`);
            }
        });
    }

    socket.on('status_changed', function(data) {
        updateStatusIndicator(data.user_id, data.status);
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