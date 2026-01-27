/**
 * RPG脱出ゲーム - メインゲームロジック
 * 古代神殿からの脱出
 */

// ================================================================================
// グローバル変数
// ================================================================================

let currentStage = 1;
let playerData = null;
let inventory = [];
let gameProgress = [];

// ================================================================================
// 初期化
// ================================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadPlayerStatus();
    loadInventory();
    loadGameProgress();
    
    // イベントリスナーの設定
    document.getElementById('submitAnswerBtn')?.addEventListener('click', submitAnswer);
    document.getElementById('hintBtn')?.addEventListener('click', showHint);
    document.getElementById('logoutBtn')?.addEventListener('click', logout);
});

// ================================================================================
// プレイヤー情報の読み込み
// ================================================================================

async function loadPlayerStatus() {
    try {
        const response = await fetch('/api/player/status');
        const data = await response.json();
        
        if (data.success) {
            playerData = data.player;
            currentStage = playerData.current_stage;
            updatePlayerStatusDisplay();
        }
    } catch (error) {
        console.error('プレイヤー情報の読み込みエラー:', error);
    }
}

function updatePlayerStatusDisplay() {
    if (!playerData) return;
    
    document.getElementById('player-name').textContent = playerData.username;
    document.getElementById('player-hp').textContent = `${playerData.hp}/100`;
    document.getElementById('player-intelligence').textContent = playerData.intelligence;
    document.getElementById('player-exp').textContent = `${playerData.experience} XP`;
    document.getElementById('player-stage').textContent = `${currentStage} of 4`;
    
    // HPバーの更新
    const hpBar = document.getElementById('hp-bar');
    if (hpBar) {
        hpBar.style.width = `${playerData.hp}%`;
        hpBar.textContent = `${playerData.hp}%`;
        hpBar.style.background = playerData.hp > 50 ? 'linear-gradient(90deg, #4caf50, #45a049)' : 'linear-gradient(90deg, #ff6b6b, #ff4757)';
    }
}

// ================================================================================
// インベントリ管理
// ================================================================================

async function loadInventory() {
    try {
        const response = await fetch('/api/player/inventory');
        const data = await response.json();
        
        if (data.success) {
            inventory = data.items;
            updateInventoryDisplay();
        }
    } catch (error) {
        console.error('インベントリの読み込みエラー:', error);
    }
}

function updateInventoryDisplay() {
    const inventoryList = document.getElementById('inventory-items');
    if (!inventoryList) return;
    
    if (inventory.length === 0) {
        inventoryList.innerHTML = '<div class="empty-inventory">No items collected yet</div>';
        return;
    }
    
    inventoryList.innerHTML = inventory.map(item => `
        <div class="inventory-item">
            <div class="item-icon">📦</div>
            <div class="item-info">
                <div class="item-name">${item.item_name}</div>
                <div class="item-description">${item.item_description}</div>
            </div>
        </div>
    `).join('');
}

// ================================================================================
// ゲーム進行状況
// ================================================================================

async function loadGameProgress() {
    try {
        const response = await fetch('/api/game/progress');
        const data = await response.json();
        
        if (data.success) {
            gameProgress = data.progress;
            loadCurrentStage();
        }
    } catch (error) {
        console.error('進行状況の読み込みエラー:', error);
    }
}

async function loadCurrentStage() {
    const stageInfo = gameProgress.find(p => p.stage_id === currentStage);
    
    if (!stageInfo) {
        console.error('ステージ情報が見つかりません');
        return;
    }
    
    // ステージUIの更新
    const stageTitle = document.getElementById('stage-title');
    if (stageTitle) {
        stageTitle.textContent = stageInfo.title;
    }
    
    // パズルエリアの表示
    displayPuzzle(currentStage, stageInfo);
}

// ================================================================================
// パズル表示
// ================================================================================

function displayPuzzle(stageId, stageInfo) {
    const puzzleArea = document.getElementById('puzzle-area');
    if (!puzzleArea) return;
    
    switch(stageId) {
        case 1:
            // ステージ1: 古代文字解読
            puzzleArea.innerHTML = `
                <div class="puzzle-stage-1">
                    <h3>🗿 壁に刻まれた古代文字 🗿</h3>
                    <div class="ancient-text">
                        <p class="ancient-symbols">⬆️ 🌅 ☀️ 🌄 ➡️</p>
                        <p class="hint-text">太陽が昇る方向を示している...</p>
                    </div>
                    <div class="answer-input">
                        <label>答えを入力してください:</label>
                        <input type="text" id="answerInput" placeholder="ひらがなで入力">
                    </div>
                </div>
            `;
            break;
            
        case 2:
            // ステージ2: 本の選択
            puzzleArea.innerHTML = `
                <div class="puzzle-stage-2">
                    <h3>📚 図書館の謎 📚</h3>
                    <p>本棚に4冊の本があります。正しい順序で選んでください。</p>
                    <div class="books-container">
                        <div class="book red" onclick="selectBook('赤')">赤の書</div>
                        <div class="book blue" onclick="selectBook('青')">青の書</div>
                        <div class="book green" onclick="selectBook('緑')">緑の書</div>
                        <div class="book yellow" onclick="selectBook('黄')">黄の書</div>
                    </div>
                    <div class="selected-books">
                        <p>選択した順序: <span id="bookSelection">未選択</span></p>
                        <button onclick="clearBookSelection()">リセット</button>
                    </div>
                </div>
            `;
            break;
            
        case 3:
            // ステージ3: 数字パズル
            puzzleArea.innerHTML = `
                <div class="puzzle-stage-3">
                    <h3>🔢 宝物庫の暗号 🔢</h3>
                    <div class="number-puzzle">
                        <p>部屋の四隅に数字が刻まれています:</p>
                        <div class="corners">
                            <div class="corner">北東: 7</div>
                            <div class="corner">北西: 3</div>
                            <div class="corner">南東: 9</div>
                            <div class="corner">南西: 2</div>
                        </div>
                        <p class="hint-text">これらの数字を正しい順序で並べよ...</p>
                    </div>
                    <div class="answer-input">
                        <label>4桁の数字を入力:</label>
                        <input type="text" id="answerInput" placeholder="0000" maxlength="4">
                    </div>
                </div>
            `;
            break;
            
        case 4:
            // ステージ4: 最終問題
            puzzleArea.innerHTML = `
                <div class="puzzle-stage-4">
                    <h3>✨ 最終の間 - 真実の扉 ✨</h3>
                    <div class="final-puzzle">
                        <p>これまでの冒険で得た知識を思い出せ...</p>
                        <p class="clue">最初の部屋で見つけたもの + 「永遠の」</p>
                        <div class="mystical-symbols">
                            <span>🌟</span>
                            <span>💎</span>
                            <span>🔮</span>
                        </div>
                    </div>
                    <div class="answer-input">
                        <label>最終的な答え:</label>
                        <input type="text" id="answerInput" placeholder="ひらがなで入力">
                    </div>
                </div>
            `;
            break;
    }
}

// ================================================================================
// 本選択（ステージ2専用）
// ================================================================================

let selectedBooks = [];

function selectBook(color) {
    if (selectedBooks.length < 4) {
        selectedBooks.push(color);
        document.getElementById('bookSelection').textContent = selectedBooks.join(' → ');
    }
}

function clearBookSelection() {
    selectedBooks = [];
    document.getElementById('bookSelection').textContent = '未選択';
}

// ================================================================================
// 答えの提出
// ================================================================================

async function submitAnswer() {
    let answer;
    
    if (currentStage === 2) {
        // ステージ2は本の選択
        answer = selectedBooks;
        if (answer.length !== 4) {
            showMessage('4冊全て選択してください', 'error');
            return;
        }
    } else {
        // その他のステージはテキスト入力
        const answerInput = document.getElementById('answerInput');
        if (!answerInput) return;
        
        answer = answerInput.value.trim();
        if (!answer) {
            showMessage('答えを入力してください', 'error');
            return;
        }
    }
    
    try {
        const response = await fetch('/api/puzzle/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                stage_id: currentStage,
                answer: answer
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.correct) {
            showMessage('🎉 正解です！', 'success');
            
            // 報酬アイテムの表示
            if (data.reward) {
                showRewardModal(data.reward);
            }
            
            // 次のステージへ
            setTimeout(() => {
                if (currentStage < 4) {
                    currentStage++;
                    loadPlayerStatus();
                    loadInventory();
                    loadGameProgress();
                } else {
                    // ゲームクリア
                    window.location.href = '/game/complete';
                }
            }, 2000);
        } else {
            showMessage('❌ ' + data.message, 'error');
        }
    } catch (error) {
        console.error('答えの提出エラー:', error);
        showMessage('エラーが発生しました', 'error');
    }
}

// ================================================================================
// ヒント表示
// ================================================================================

async function showHint() {
    try {
        const response = await fetch(`/api/puzzle/hint/${currentStage}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showHintModal(data.hint, data.hints_used);
        }
    } catch (error) {
        console.error('ヒント取得エラー:', error);
    }
}

function showHintModal(hint, hintsUsed) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>💡 ヒント ${hintsUsed}</h3>
            <p>${hint}</p>
            <button onclick="this.closest('.modal').remove()">閉じる</button>
        </div>
    `;
    document.body.appendChild(modal);
    
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

// ================================================================================
// 報酬表示
// ================================================================================

function showRewardModal(reward) {
    const modal = document.createElement('div');
    modal.className = 'modal reward-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>🎁 アイテムを入手しました！</h3>
            <div class="reward-item">
                <div class="reward-icon">📦</div>
                <div class="reward-name">${reward.name}</div>
                <div class="reward-description">${reward.description}</div>
            </div>
            <button onclick="this.closest('.modal').remove()">続ける</button>
        </div>
    `;
    document.body.appendChild(modal);
    
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

// ================================================================================
// メッセージ表示
// ================================================================================

function showMessage(text, type) {
    const messageDiv = document.getElementById('gameMessage');
    if (!messageDiv) return;
    
    messageDiv.textContent = text;
    messageDiv.className = 'message show ' + type;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
        messageDiv.className = 'message';
        messageDiv.style.display = 'none';
    }, 3000);
}

// ================================================================================
// ログアウト
// ================================================================================

function logout() {
    if (confirm('ゲームを終了しますか？（進行状況は自動保存されています）')) {
        window.location.href = '/logout';
    }
}

// ================================================================================
// ユーティリティ関数
// ================================================================================

function saveGame() {
    fetch('/api/game/save', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('ゲームを保存しました', 'success');
        }
    });
}

// 定期的な自動保存（5分ごと）
setInterval(saveGame, 5 * 60 * 1000);
