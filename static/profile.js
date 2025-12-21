// プロフィール機能のJavaScript

let currentUserId;

document.addEventListener('DOMContentLoaded', function() {
    currentUserId = localStorage.getItem('userId') || '1';
    loadProfile();
});

// プロフィール情報の読み込み
function loadProfile() {
    fetch(`/api/profile/${currentUserId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayProfile(data.profile);
            }
        })
        .catch(error => console.error('プロフィール読み込みエラー:', error));
}

// プロフィール情報の表示
function displayProfile(profile) {
    document.getElementById('username').textContent = profile.username || 'ユーザー名';
    document.getElementById('statusMessage').textContent = profile.status_message || 'ステータスメッセージ';
    document.getElementById('bio').textContent = profile.bio || '自己紹介文がありません';
    document.getElementById('birthday').textContent = profile.birthday || '未設定';
    document.getElementById('email').textContent = profile.email || '未設定';
    
    if (profile.profile_image) {
        document.getElementById('avatarImage').src = `/static/uploads/${profile.profile_image}`;
    }
    
    if (profile.background_image) {
        document.getElementById('coverImage').src = `/static/uploads/${profile.background_image}`;
    }
    
    // 統計情報の読み込み
    loadStats();
}

// 統計情報の読み込み
function loadStats() {
    fetch(`/api/profile/${currentUserId}/stats`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('friendCount').textContent = data.stats.friends || 0;
                document.getElementById('roomCount').textContent = data.stats.rooms || 0;
            }
        })
        .catch(error => console.error('統計情報読み込みエラー:', error));
}

// プロフィール編集
function editProfile() {
    const modal = document.getElementById('editModal');
    
    // 現在の値をフォームに設定
    document.getElementById('editUsername').value = document.getElementById('username').textContent;
    document.getElementById('editStatusMessage').value = document.getElementById('statusMessage').textContent;
    document.getElementById('editBio').value = document.getElementById('bio').textContent !== '自己紹介文がありません' 
        ? document.getElementById('bio').textContent : '';
    document.getElementById('editBirthday').value = document.getElementById('birthday').textContent !== '未設定' 
        ? document.getElementById('birthday').textContent : '';
    document.getElementById('editEmail').value = document.getElementById('email').textContent !== '未設定' 
        ? document.getElementById('email').textContent : '';
    
    modal.style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// フォーム送信
document.getElementById('editForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = {
        username: document.getElementById('editUsername').value,
        status_message: document.getElementById('editStatusMessage').value,
        bio: document.getElementById('editBio').value,
        birthday: document.getElementById('editBirthday').value,
        email: document.getElementById('editEmail').value
    };
    
    fetch(`/api/profile/${currentUserId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayProfile(data.profile);
            closeEditModal();
            alert('プロフィールを更新しました');
        } else {
            alert('エラー: ' + data.message);
        }
    })
    .catch(error => {
        console.error('プロフィール更新エラー:', error);
        alert('プロフィールの更新に失敗しました');
    });
});

// アバター画像選択
function selectAvatarImage() {
    document.getElementById('avatarInput').click();
}

function uploadAvatar(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append('image', input.files[0]);
        
        fetch(`/api/profile/${currentUserId}/avatar`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('avatarImage').src = `/static/uploads/${data.filename}?t=${Date.now()}`;
                alert('アバターを更新しました');
            }
        })
        .catch(error => console.error('アバターアップロードエラー:', error));
    }
}

// カバー画像選択
function selectCoverImage() {
    document.getElementById('coverInput').click();
}

function uploadCover(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append('image', input.files[0]);
        
        fetch(`/api/profile/${currentUserId}/cover`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('coverImage').src = `/static/uploads/${data.filename}?t=${Date.now()}`;
                alert('カバー画像を更新しました');
            }
        })
        .catch(error => console.error('カバー画像アップロードエラー:', error));
    }
}

// プライバシー設定
function showPrivacySettings() {
    fetch(`/api/profile/${currentUserId}/privacy`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('showTyping').checked = data.settings.show_typing;
                document.getElementById('showOnlineStatus').checked = data.settings.show_online_status;
                document.getElementById('privacyModal').style.display = 'flex';
            }
        })
        .catch(error => console.error('プライバシー設定読み込みエラー:', error));
}

function closePrivacyModal() {
    document.getElementById('privacyModal').style.display = 'none';
}

function savePrivacySettings() {
    const settings = {
        show_typing: document.getElementById('showTyping').checked,
        show_online_status: document.getElementById('showOnlineStatus').checked
    };
    
    fetch(`/api/profile/${currentUserId}/privacy`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closePrivacyModal();
            alert('プライバシー設定を更新しました');
        }
    })
    .catch(error => console.error('プライバシー設定更新エラー:', error));
}

// 位置情報共有
function shareLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
                
                fetch(`/api/profile/${currentUserId}/location`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(location)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(`位置情報を共有しました\n緯度: ${location.latitude.toFixed(6)}\n経度: ${location.longitude.toFixed(6)}`);
                    }
                })
                .catch(error => console.error('位置情報送信エラー:', error));
            },
            (error) => {
                alert('位置情報の取得に失敗しました: ' + error.message);
            }
        );
    } else {
        alert('このブラウザは位置情報に対応していません');
    }
}
