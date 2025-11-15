class OldMaidGame {
    constructor() {
        this.container = null;
        this.players = [];
        this.deck = [];
        this.gameState = 'setup';
        this.currentPlayer = 0;
        this.gameLog = [];
        this.oldMaidCard = null;

        this.settings = {
            playerCount: 4,
            difficulty: 'normal',
            autoPlay: true,
            animationSpeed: 1000
        };
    }

    initialize(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found.`);
            return;
        }
        this._createUI();
        this._setupEventListeners();
    }
    
    startGame() {
        this.gameState = 'playing';
        this._initializeGameData();
        this._dealCards();
        this._removeInitialPairs();
        this.updateUI();
        this._startTurn();

        document.getElementById('start-game').disabled = true;
        document.getElementById('auto-play').disabled = false;
        document.getElementById('game-status').textContent = 'プレイ中';
        this._addLog('ゲームを開始しました！');
    }
    
    startNewGame() {
        this._closeResultsModal();
        this.resetGame();
        this.startGame();
    }
    
    resetGame() {
        this.gameState = 'setup';
        this.players = [];
        this.deck = [];
        this.currentPlayer = 0;
        this.gameLog = [];
        this.oldMaidCard = null;

        document.getElementById('players-layout').innerHTML = '';
        document.getElementById('discarded-pairs').innerHTML = '';
        document.getElementById('log-content').innerHTML = '';
        document.getElementById('card-selection').style.display = 'none';
        document.getElementById('action-message').textContent = 'ゲームを開始してください';
        document.getElementById('game-status').textContent = '準備中';
        document.getElementById('current-player-name').textContent = '-';
        document.getElementById('total-cards').textContent = '0';
        
        document.getElementById('start-game').disabled = false;
        document.getElementById('auto-play').disabled = true;
        document.getElementById('draw-card').disabled = true;
        
        this._closeResultsModal();
    }
    
    _startTurn() {
        if (this._checkGameEnd()) {
            this._endGame();
            return;
        }

        const currentPlayerObj = this.players[this.currentPlayer];
        if (currentPlayerObj.isFinished) {
            this._nextPlayer();
            return;
        }

        this._updateCurrentPlayerDisplay();

        if (currentPlayerObj.isHuman && !this.settings.autoPlay) {
            this._showHumanTurn();
        } else {
            setTimeout(() => this._executeCPUTurn(), this.settings.animationSpeed);
        }
    }

    _nextPlayer() {
        let attempts = 0;
        const playerCount = this.settings.playerCount;
        
        do {
            this.currentPlayer = (this.currentPlayer + 1) % playerCount;
            attempts++;
        } while (this.players[this.currentPlayer].isFinished && attempts < playerCount);

        if (attempts < playerCount) {
            setTimeout(() => this._startTurn(), this.settings.animationSpeed / 2);
        } else {
            this._endGame();
        }
    }

    _checkGameEnd() {
        const activePlayers = this.players.filter(p => !p.isFinished);
        return activePlayers.length <= 1;
    }

    _endGame() {
        this.gameState = 'finished';
        
        const remainingPlayer = this.players.find(p => !p.isFinished);
        if (remainingPlayer) {
            remainingPlayer.isFinished = true;
            remainingPlayer.rank = this.settings.playerCount;
            this._addLog(`${remainingPlayer.name}がババを持って最下位になりました...`);
        }

        this._showResultsModal();
        document.getElementById('game-status').textContent = 'ゲーム終了';
        document.getElementById('start-game').disabled = false;
        document.getElementById('auto-play').disabled = true;
    }

    _initializeGameData() {
        this._createDeck();
        this._shuffleDeck();
        this._initializePlayers();
        this.gameLog = [];
        this.currentPlayer = 0;
    }

    _createDeck() {
        this.deck = [];
        const suits = ['♠', '♥', '♦', '♣'];
        const values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
        
        for (const suit of suits) {
            for (const value of values) {
                this.deck.push({ suit, value, id: `${suit}${value}`, isOldMaid: false });
            }
        }

        const jokerIndex = Math.floor(Math.random() * this.deck.length);
        this.oldMaidCard = this.deck[jokerIndex];
        Object.assign(this.oldMaidCard, { suit: '★', value: 'JOKER', id: 'JOKER', isOldMaid: true });
    }

    _shuffleDeck() {
        for (let i = this.deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.deck[i], this.deck[j]] = [this.deck[j], this.deck[i]];
        }
    }

    _initializePlayers() {
        this.players = [];
        const playerNames = ['あなた', 'CPU1', 'CPU2', 'CPU3', 'CPU4', 'CPU5'];
        
        for (let i = 0; i < this.settings.playerCount; i++) {
            this.players.push({
                id: i,
                name: playerNames[i],
                cards: [],
                isHuman: i === 0,
                isFinished: false,
                rank: null,
                pairsDiscarded: 0
            });
        }
    }
    
    _dealCards() {
        let cardIndex = 0;
        while (cardIndex < this.deck.length) {
            for (const player of this.players) {
                if (cardIndex < this.deck.length) {
                    player.cards.push(this.deck[cardIndex++]);
                }
            }
        }
    }

    _removeInitialPairs() {
        this.players.forEach(player => this._removePairsFromHand(player));
    }
    
    _removePairsFromHand(player) {
        const cardCounts = player.cards.reduce((acc, card) => {
            if (!card.isOldMaid) {
                acc[card.value] = (acc[card.value] || 0) + 1;
            }
            return acc;
        }, {});

        const valuesToRemove = Object.keys(cardCounts).filter(value => cardCounts[value] >= 2);
        
        if (valuesToRemove.length === 0) return;

        const pairs = [];
        const remainingCards = [];
        
        for (const value of valuesToRemove) {
            const count = Math.floor(cardCounts[value] / 2);
            pairs.push(...Array(count * 2).fill(value));
        }

        const removedCards = [];
        player.cards.forEach(card => {
            const index = pairs.indexOf(card.value);
            if (!card.isOldMaid && index !== -1) {
                pairs.splice(index, 1);
                removedCards.push(card);
            } else {
                remainingCards.push(card);
            }
        });

        player.cards = remainingCards;
        
        if (removedCards.length > 0) {
            const pairCount = removedCards.length / 2;
            player.pairsDiscarded += pairCount;
            this._addLog(`${player.name}が${pairCount}ペアを捨てました`);
            this._animateDiscardPairs(removedCards);
        }
    }
    
    _drawCardFromPlayer(drawingPlayerId, targetPlayerId, cardIndex) {
        const drawingPlayer = this.players[drawingPlayerId];
        const targetPlayer = this.players[targetPlayerId];
        
        if (!targetPlayer || cardIndex >= targetPlayer.cards.length) return;

        const drawnCard = targetPlayer.cards.splice(cardIndex, 1)[0];
        drawingPlayer.cards.push(drawnCard);

        this._addLog(`${drawingPlayer.name}が${targetPlayer.name}からカードを引きました`);
        if (drawnCard.isOldMaid) {
            this._addLog(`${drawingPlayer.name}がババを引いてしまいました！`);
        }

        this._removePairsFromHand(drawingPlayer);

        if (drawingPlayer.cards.length === 0) this._finishPlayer(drawingPlayerId);
        if (targetPlayer.cards.length === 0) this._finishPlayer(targetPlayerId);

        this.updateUI();
        this._nextPlayer();
    }
    
    _finishPlayer(playerId) {
        const player = this.players[playerId];
        if (player.isFinished) return;
        
        player.isFinished = true;
        const finishedCount = this.players.filter(p => p.isFinished).length;
        player.rank = finishedCount;
        
        this._addLog(`${player.name}が${finishedCount}位でフィニッシュ！`);
    }

    _showHumanTurn() {
        const nextPlayer = this._getNextActivePlayer();
        if (!nextPlayer) {
            this._nextPlayer();
            return;
        }

        document.getElementById('action-message').textContent = `${nextPlayer.name}からカードを引いてください`;
        
        const opponentHand = document.getElementById('opponent-hand');
        opponentHand.innerHTML = nextPlayer.cards.map((_, index) => 
            `<div class="opponent-card" data-card-index="${index}" data-player-id="${nextPlayer.id}">
                <div class="card-back">?</div>
            </div>`
        ).join('');

        opponentHand.querySelectorAll('.opponent-card').forEach(cardElement => {
            cardElement.addEventListener('click', () => this._selectOpponentCard(cardElement));
        });

        document.getElementById('card-selection').style.display = 'block';
    }

    _selectOpponentCard(cardElement) {
        document.querySelectorAll('.opponent-card.selected').forEach(card => card.classList.remove('selected'));
        cardElement.classList.add('selected');
        document.getElementById('draw-card').disabled = false;
    }

    drawSelectedCard() {
        const selectedCard = document.querySelector('.opponent-card.selected');
        if (!selectedCard) return;

        const cardIndex = parseInt(selectedCard.dataset.cardIndex, 10);
        const playerId = parseInt(selectedCard.dataset.playerId, 10);
        
        this._drawCardFromPlayer(this.currentPlayer, playerId, cardIndex);
        
        document.getElementById('card-selection').style.display = 'none';
        document.getElementById('draw-card').disabled = true;
    }
    
    _executeCPUTurn() {
        const nextPlayer = this._getNextActivePlayer();
        if (!nextPlayer) {
            this._nextPlayer();
            return;
        }

        const cardIndex = this._getSmartCardChoice(nextPlayer);
        this._drawCardFromPlayer(this.currentPlayer, nextPlayer.id, cardIndex);
    }
    
    _getSmartCardChoice(targetPlayer) {
        if (this.settings.difficulty === 'easy') {
            return Math.floor(Math.random() * targetPlayer.cards.length);
        }
        
        if (this.settings.difficulty === 'hard') {
            const currentPlayerCards = this.players[this.currentPlayer].cards;
            const targetCards = targetPlayer.cards;
            
            const nonMatchingIndices = [];
            for (let i = 0; i < targetCards.length; i++) {
                const targetCard = targetCards[i];
                if (targetCard.isOldMaid) continue;
                
                const hasMatch = currentPlayerCards.some(c => !c.isOldMaid && c.value === targetCard.value);
                if (!hasMatch) {
                    nonMatchingIndices.push(i);
                }
            }

            if (nonMatchingIndices.length > 0) {
                return nonMatchingIndices[Math.floor(Math.random() * nonMatchingIndices.length)];
            }
        }

        return Math.floor(Math.random() * targetPlayer.cards.length);
    }
    
    _createUI() {
        this.container.innerHTML = `
            <div class="oldmaid-game">
                ${this._createHeaderHTML()}
                ${this._createSettingsHTML()}
                ${this._createGameAreaHTML()}
                ${this._createLogPanelHTML()}
                ${this._createResultsModalHTML()}
            </div>
        `;
    }

    _setupEventListeners() {
        document.getElementById('start-game').addEventListener('click', () => this.startGame());
        document.getElementById('auto-play').addEventListener('click', () => this.toggleAutoPlay());
        document.getElementById('reset-game').addEventListener('click', () => this.resetGame());
        document.getElementById('draw-card').addEventListener('click', () => this.drawSelectedCard());
        
        document.getElementById('play-again').addEventListener('click', () => this.startNewGame());
        document.getElementById('close-results').addEventListener('click', () => this._closeResultsModal());

        document.getElementById('player-count').addEventListener('change', (e) => {
            this.settings.playerCount = parseInt(e.target.value, 10);
        });
        document.getElementById('difficulty').addEventListener('change', (e) => {
            this.settings.difficulty = e.target.value;
        });
        document.getElementById('auto-play-setting').addEventListener('change', (e) => {
            this.settings.autoPlay = e.target.checked;
        });
        document.getElementById('animation-speed').addEventListener('input', (e) => {
            this.settings.animationSpeed = parseInt(e.target.value, 10);
            document.getElementById('speed-value').textContent = (this.settings.animationSpeed / 1000).toFixed(1) + '秒';
        });
    }
    
    updateUI() {
        this._updatePlayersLayout();
        this._updateCardCounts();
        this._updateCurrentPlayerDisplay();
    }

    _updatePlayersLayout() {
        const playersLayout = document.getElementById('players-layout');
        playersLayout.innerHTML = this.players.map(player => {
            const isCurrent = player.id === this.currentPlayer;
            const handHTML = player.isHuman
                ? player.cards.map(card => 
                    `<div class="player-card ${card.suit === '♥' || card.suit === '♦' ? 'red' : ''} ${card.isOldMaid ? 'old-maid' : ''}">
                        ${card.suit}${card.value}
                    </div>`
                  ).join('')
                : Array(player.cards.length).fill('<div class="player-card back"></div>').join('');
            
            return `
                <div class="player-display ${isCurrent ? 'current' : ''} ${player.isFinished ? 'finished' : ''}">
                    <div class="player-name">${player.name} ${player.rank ? `(${player.rank}位)` : ''}</div>
                    <div class="player-info">
                        <span>${player.cards.length}枚</span> | <span>${player.pairsDiscarded}ペア</span>
                    </div>
                    <div class="player-hand-display">${handHTML}</div>
                </div>`;
        }).join('');
    }

    _updateCardCounts() {
        const totalCards = this.players.reduce((sum, player) => sum + player.cards.length, 0);
        document.getElementById('total-cards').textContent = totalCards;
    }

    _updateCurrentPlayerDisplay() {
        const currentPlayerName = this.players[this.currentPlayer]?.name || '-';
        document.getElementById('current-player-name').textContent = currentPlayerName;
    }

    _animateDiscardPairs(pairs) {
        const discardPile = document.getElementById('discarded-pairs');
        pairs.forEach((card, index) => {
            setTimeout(() => {
                const cardElement = document.createElement('div');
                cardElement.className = `discarded-card ${card.suit === '♥' || card.suit === '♦' ? 'red' : ''}`;
                cardElement.textContent = `${card.suit}${card.value}`;
                discardPile.appendChild(cardElement);
            }, index * 100);
        });
    }

    _showResultsModal() {
        const sortedPlayers = [...this.players].sort((a, b) => (a.rank || Infinity) - (b.rank || Infinity));
        const winner = sortedPlayers[0];

        document.getElementById('game-results').innerHTML = `
            <div class="winner-announcement">
                <h4>🎉 ${winner.name}の勝利！ 🎉</h4>
                <p>おめでとうございます！</p>
            </div>
        `;
        
        document.getElementById('final-rankings').innerHTML = `
            <h4>最終順位</h4>
            <div class="rankings-list">
                ${sortedPlayers.map(player => `
                    <div class="rank-item ${player.rank === this.settings.playerCount ? 'loser' : ''}">
                        <span class="rank-number">${player.rank}位</span>
                        <span class="player-name">${player.name}</span>
                        <span class="pairs-count">${player.pairsDiscarded}ペア</span>
                        ${player.rank === this.settings.playerCount ? '<span class="old-maid-holder">ババ持ち</span>' : ''}
                    </div>
                `).join('')}
            </div>
        `;

        document.getElementById('results-modal').style.display = 'flex';
    }

    _closeResultsModal() {
        document.getElementById('results-modal').style.display = 'none';
    }

    _createHeaderHTML() {
        return `
            <div class="game-header">
                <h2>ババ抜き</h2>
                <div class="game-info">
                    <span class="current-turn">現在の順番: <span id="current-player-name">-</span></span>
                    <span class="remaining-cards">残りカード: <span id="total-cards">0</span>枚</span>
                    <span class="game-status" id="game-status">準備中</span>
                </div>
                <div class="game-controls">
                    <button id="start-game" class="btn btn-success">ゲーム開始</button>
                    <button id="auto-play" class="btn btn-secondary" disabled>自動実行</button>
                    <button id="reset-game" class="btn btn-outline">リセット</button>
                </div>
            </div>`;
    }

    _createSettingsHTML() {
        return `
            <div class="settings-panel">
                <div class="settings-row">
                    <label>プレイヤー数:
                        <select id="player-count">
                            <option value="3">3人</option>
                            <option value="4" selected>4人</option>
                            <option value="5">5人</option>
                            <option value="6">6人</option>
                        </select>
                    </label>
                    <label>難易度:
                        <select id="difficulty">
                            <option value="easy">簡単</option>
                            <option value="normal" selected>普通</option>
                            <option value="hard">難しい</option>
                        </select>
                    </label>
                    <label><input type="checkbox" id="auto-play-setting" checked> 自動実行</label>
                    <label>アニメーション速度:
                        <input type="range" id="animation-speed" min="200" max="2000" value="1000" step="200">
                        <span id="speed-value">1.0秒</span>
                    </label>
                </div>
            </div>`;
    }

    _createGameAreaHTML() {
        return `
            <div class="game-area">
                <div class="players-layout" id="players-layout"></div>
                <div class="center-area">
                    <div class="discard-pile" id="discard-pile">
                        <div class="pile-label">捨て札</div>
                        <div class="discarded-pairs" id="discarded-pairs"></div>
                    </div>
                    <div class="current-action" id="current-action">
                        <div class="action-message" id="action-message">ゲームを開始してください</div>
                        <div class="card-selection" id="card-selection" style="display: none;">
                            <div class="opponent-hand" id="opponent-hand"></div>
                            <button id="draw-card" class="btn btn-primary" disabled>カードを引く</button>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    _createLogPanelHTML() {
        return `
            <div class="game-log-panel">
                <h3>ゲームログ</h3>
                <div class="log-content" id="log-content"></div>
            </div>`;
    }

    _createResultsModalHTML() {
        return `
            <div class="results-modal" id="results-modal" style="display: none;">
                <div class="modal-content">
                    <h3>ゲーム終了</h3>
                    <div class="game-results" id="game-results"></div>
                    <div class="final-rankings" id="final-rankings"></div>
                    <div class="modal-actions">
                        <button id="play-again" class="btn btn-success">もう一度プレイ</button>
                        <button id="close-results" class="btn btn-secondary">閉じる</button>
                    </div>
                </div>
            </div>`;
    }

    toggleAutoPlay() {
        this.settings.autoPlay = !this.settings.autoPlay;
        const button = document.getElementById('auto-play');
        button.textContent = this.settings.autoPlay ? '手動実行に切替' : '自動実行に切替';
        button.classList.toggle('active', this.settings.autoPlay);

        if (!this.settings.autoPlay && this.players[this.currentPlayer]?.isHuman) {
            this._showHumanTurn();
        }
    }

    _addLog(message) {
        const timestamp = new Date().toLocaleTimeString();
        this.gameLog.push({ timestamp, message });
        
        const logContent = document.getElementById('log-content');
        const logItem = document.createElement('div');
        logItem.className = 'log-item';
        logItem.innerHTML = `<span class="log-time">${timestamp}</span> <span class="log-message">${message}</span>`;
        logContent.appendChild(logItem);
        logContent.scrollTop = logContent.scrollHeight;
    }

    _getNextActivePlayer() {
        let nextPlayerId = this.currentPlayer;
        let attempts = 0;
        const playerCount = this.settings.playerCount;
        
        do {
            nextPlayerId = (nextPlayerId + 1) % playerCount;
            attempts++;
        } while ((this.players[nextPlayerId].isFinished || nextPlayerId === this.currentPlayer) && attempts < playerCount);
        
        return attempts < playerCount ? this.players[nextPlayerId] : null;
    }
}

if (typeof window !== 'undefined') {
    window.OldMaidGame = OldMaidGame;
}
