class DaifugoGame {
    constructor() {
        this.players = [];
        this.deck = [];
        this.currentCards = [];
        this.gameState = 'setup';
        this.currentPlayer = 0;
        this.passCount = 0;
        this.lastPlayedBy = -1;
        this.revolution = false;
        this.gameHistory = [];
        this.ranks = ['大富豪', '富豪', '平民', '貧民', '大貧民'];
        this.settings = {
            playerCount: 4,
            jokerCount: 2,
            revolutionRule: true,
            taxRule: true,
            skipRule: true,
            bindRule: false
        };
    }

    initialize(containerId) {
        this.container = document.getElementById(containerId);
        this.createUI();
        this.setupEventListeners();
        this.initializeDeck();
    }

    createUI() {
        this.container.innerHTML = `
            <div class="daifugo-game">
                <div class="game-header">
                    <h2>大富豪</h2>
                    <div class="game-info">
                        <span class="current-player">現在のプレイヤー: <span id="current-player-name">-</span></span>
                        <span class="revolution-status" id="revolution-status">通常</span>
                        <span class="cards-count">残り: <span id="cards-count">0</span>枚</span>
                    </div>
                    <div class="game-controls">
                        <button id="start-game" class="btn btn-success">ゲーム開始</button>
                        <button id="pass-turn" class="btn btn-secondary" disabled>パス</button>
                        <button id="reset-game" class="btn btn-outline">リセット</button>
                    </div>
                </div>

                <div class="game-board">
                    <div class="field-area">
                        <div class="current-cards" id="current-cards">
                            <div class="no-cards">カードが出されていません</div>
                        </div>
                        <div class="field-info">
                            <span id="last-played-by">-</span>がプレイ
                        </div>
                    </div>

                    <div class="players-area">
                        <div class="other-players" id="other-players"></div>
                        
                        <div class="player-hand" id="player-hand">
                            <div class="hand-cards" id="hand-cards"></div>
                            <div class="play-controls">
                                <button id="play-cards" class="btn btn-primary" disabled>カードを出す</button>
                                <button id="clear-selection" class="btn btn-secondary">選択解除</button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="game-log" id="game-log">
                    <h3>ゲームログ</h3>
                    <div class="log-content" id="log-content"></div>
                </div>

                <div class="settings-panel">
                    <details>
                        <summary>ゲーム設定</summary>
                        <div class="settings-grid">
                            <label>
                                <input type="checkbox" id="revolution-rule" checked> 革命あり
                            </label>
                            <label>
                                <input type="checkbox" id="tax-rule" checked> 税金あり
                            </label>
                            <label>
                                <input type="checkbox" id="skip-rule" checked> スキップあり
                            </label>
                            <label>
                                <input type="checkbox" id="bind-rule"> 縛りあり
                            </label>
                            <label>
                                プレイヤー数:
                                <select id="player-count">
                                    <option value="3">3人</option>
                                    <option value="4" selected>4人</option>
                                    <option value="5">5人</option>
                                </select>
                            </label>
                        </div>
                    </details>
                </div>

                <div class="results-panel" id="results-panel" style="display: none;">
                    <h3>ゲーム結果</h3>
                    <div class="final-ranks" id="final-ranks"></div>
                    <button id="next-game" class="btn btn-success">次のゲーム</button>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        document.getElementById('start-game').addEventListener('click', () => this.startGame());
        document.getElementById('pass-turn').addEventListener('click', () => this.passTurn());
        document.getElementById('play-cards').addEventListener('click', () => this.playSelectedCards());
        document.getElementById('clear-selection').addEventListener('click', () => this.clearSelection());
        document.getElementById('reset-game').addEventListener('click', () => this.resetGame());
        document.getElementById('next-game').addEventListener('click', () => this.nextGame());

        document.getElementById('revolution-rule').addEventListener('change', (e) => {
            this.settings.revolutionRule = e.target.checked;
        });
        document.getElementById('tax-rule').addEventListener('change', (e) => {
            this.settings.taxRule = e.target.checked;
        });
        document.getElementById('skip-rule').addEventListener('change', (e) => {
            this.settings.skipRule = e.target.checked;
        });
        document.getElementById('bind-rule').addEventListener('change', (e) => {
            this.settings.bindRule = e.target.checked;
        });
        document.getElementById('player-count').addEventListener('change', (e) => {
            this.settings.playerCount = parseInt(e.target.value);
        });
    }

    initializeDeck() {
        this.deck = [];
        const suits = ['♠', '♥', '♦', '♣'];
        const values = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2'];
        
        suits.forEach(suit => {
            values.forEach((value, index) => {
                this.deck.push({
                    suit: suit,
                    value: value,
                    rank: index + 3,
                    id: `${suit}${value}`
                });
            });
        });

        if (this.settings.jokerCount > 0) {
            for (let i = 0; i < this.settings.jokerCount; i++) {
                this.deck.push({
                    suit: '★',
                    value: 'JOKER',
                    rank: 16,
                    id: `JOKER${i + 1}`
                });
            }
        }
    }

    startGame() {
        this.gameState = 'playing';
        this.revolution = false;
        this.currentCards = [];
        this.passCount = 0;
        this.lastPlayedBy = -1;
        
        this.initializePlayers();
        this.shuffleDeck();
        this.dealCards();
        this.determinFirstPlayer();
        this.updateUI();
        
        this.addLog('ゲームを開始しました！');
        document.getElementById('start-game').disabled = true;
        document.getElementById('pass-turn').disabled = false;
    }

    initializePlayers() {
        this.players = [];
        for (let i = 0; i < this.settings.playerCount; i++) {
            this.players.push({
                id: i,
                name: i === 0 ? 'あなた' : `CPU${i}`,
                cards: [],
                rank: null,
                isFinished: false,
                isHuman: i === 0
            });
        }
    }

    shuffleDeck() {
        for (let i = this.deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.deck[i], this.deck[j]] = [this.deck[j], this.deck[i]];
        }
    }

    dealCards() {
        let cardIndex = 0;
        this.players.forEach(player => {
            player.cards = [];
        });

        while (cardIndex < this.deck.length) {
            this.players.forEach((player, playerIndex) => {
                if (cardIndex < this.deck.length) {
                    player.cards.push(this.deck[cardIndex]);
                    cardIndex++;
                }
            });
        }

        this.players.forEach(player => {
            this.sortCards(player.cards);
        });
    }

    sortCards(cards) {
        cards.sort((a, b) => {
            if (this.revolution) {
                return a.rank - b.rank;
            } else {
                return b.rank - a.rank;
            }
        });
    }

    determinFirstPlayer() {
        for (let i = 0; i < this.players.length; i++) {
            const has3Spades = this.players[i].cards.some(card => 
                card.suit === '♠' && card.value === '3'
            );
            if (has3Spades) {
                this.currentPlayer = i;
                this.addLog(`${this.players[i].name}が♠3を持っているため先攻です`);
                return;
            }
        }
        this.currentPlayer = 0;
        this.addLog('ランダムに先攻を決定しました');
    }

    updateUI() {
        this.updateCurrentPlayerDisplay();
        this.updateFieldDisplay();
        this.updateHandDisplay();
        this.updateOtherPlayersDisplay();
        this.updateRevolutionStatus();
    }

    updateCurrentPlayerDisplay() {
        const currentPlayerName = this.players[this.currentPlayer].name;
        document.getElementById('current-player-name').textContent = currentPlayerName;
    }

    updateFieldDisplay() {
        const fieldArea = document.getElementById('current-cards');
        const lastPlayedBy = document.getElementById('last-played-by');

        if (this.currentCards.length === 0) {
            fieldArea.innerHTML = '<div class="no-cards">カードが出されていません</div>';
            lastPlayedBy.textContent = '-';
        } else {
            fieldArea.innerHTML = this.currentCards.map(card => 
                `<div class="card field-card ${card.suit === '♥' || card.suit === '♦' ? 'red' : ''}">${card.suit}${card.value}</div>`
            ).join('');
            
            if (this.lastPlayedBy >= 0) {
                lastPlayedBy.textContent = this.players[this.lastPlayedBy].name;
            }
        }
    }

    updateHandDisplay() {
        const player = this.players[0];
        const handCards = document.getElementById('hand-cards');
        
        handCards.innerHTML = player.cards.map(card => 
            `<div class="card hand-card ${card.suit === '♥' || card.suit === '♦' ? 'red' : ''}" data-card-id="${card.id}">
                ${card.suit}${card.value}
            </div>`
        ).join('');

        handCards.querySelectorAll('.hand-card').forEach(cardElement => {
            cardElement.addEventListener('click', () => this.toggleCardSelection(cardElement));
        });

        document.getElementById('cards-count').textContent = player.cards.length;
    }

    updateOtherPlayersDisplay() {
        const otherPlayersDiv = document.getElementById('other-players');
        const otherPlayers = this.players.slice(1);
        
        otherPlayersDiv.innerHTML = otherPlayers.map(player => 
            `<div class="other-player ${player.id === this.currentPlayer ? 'current' : ''}">
                <div class="player-name">${player.name}</div>
                <div class="player-cards-count">${player.cards.length}枚</div>
                ${player.isFinished ? `<div class="player-rank">${player.rank}</div>` : ''}
            </div>`
        ).join('');
    }

    updateRevolutionStatus() {
        document.getElementById('revolution-status').textContent = this.revolution ? '革命中' : '通常';
    }

    toggleCardSelection(cardElement) {
        cardElement.classList.toggle('selected');
        this.updatePlayButton();
    }

    clearSelection() {
        document.querySelectorAll('.hand-card.selected').forEach(card => {
            card.classList.remove('selected');
        });
        this.updatePlayButton();
    }

    updatePlayButton() {
        const selectedCards = document.querySelectorAll('.hand-card.selected');
        const playButton = document.getElementById('play-cards');
        
        if (selectedCards.length === 0) {
            playButton.disabled = true;
            return;
        }

        const selectedCardIds = Array.from(selectedCards).map(card => card.dataset.cardId);
        const cards = this.players[0].cards.filter(card => selectedCardIds.includes(card.id));
        
        playButton.disabled = !this.isValidPlay(cards);
    }

    playSelectedCards() {
        const selectedCards = document.querySelectorAll('.hand-card.selected');
        const selectedCardIds = Array.from(selectedCards).map(card => card.dataset.cardId);
        const cards = this.players[0].cards.filter(card => selectedCardIds.includes(card.id));
        
        if (this.isValidPlay(cards)) {
            this.playCards(0, cards);
        }
    }

    isValidPlay(cards) {
        if (cards.length === 0) return false;

        if (this.currentCards.length === 0) {
            return this.isValidCardCombination(cards);
        }

        if (cards.length !== this.currentCards.length) return false;
        if (!this.isValidCardCombination(cards)) return false;

        const playRank = this.getCardsRank(cards);
        const currentRank = this.getCardsRank(this.currentCards);

        if (this.revolution) {
            return playRank < currentRank;
        } else {
            return playRank > currentRank;
        }
    }

    isValidCardCombination(cards) {
        if (cards.length === 1) return true;

        if (cards.some(card => card.value === 'JOKER')) {
            return true;
        }

        const ranks = cards.map(card => card.rank).sort((a, b) => a - b);
        return ranks.every(rank => rank === ranks[0]);
    }

    getCardsRank(cards) {
        if (cards.some(card => card.value === 'JOKER')) {
            return this.revolution ? 0 : 20;
        }
        return cards[0].rank;
    }

    playCards(playerIndex, cards) {
        const player = this.players[playerIndex];
        
        cards.forEach(card => {
            const cardIndex = player.cards.findIndex(c => c.id === card.id);
            if (cardIndex !== -1) {
                player.cards.splice(cardIndex, 1);
            }
        });

        this.currentCards = [...cards];
        this.lastPlayedBy = playerIndex;
        this.passCount = 0;

        this.addLog(`${player.name}が${cards.map(c => `${c.suit}${c.value}`).join(', ')}を出しました`);

        if (this.settings.revolutionRule && cards.length >= 4) {
            this.revolution = !this.revolution;
            this.addLog(this.revolution ? '革命が起こりました！' : '革命が終了しました！');
            this.players.forEach(p => this.sortCards(p.cards));
        }

        if (player.cards.length === 0) {
            this.finishPlayer(playerIndex);
        }

        this.nextTurn();
        this.updateUI();
    }

    finishPlayer(playerIndex) {
        const player = this.players[playerIndex];
        const finishedCount = this.players.filter(p => p.isFinished).length;
        
        player.isFinished = true;
        player.rank = this.ranks[finishedCount];
        
        this.addLog(`${player.name}が${player.rank}でフィニッシュ！`);

        if (this.players.filter(p => !p.isFinished).length <= 1) {
            this.endGame();
        }
    }

    passTurn() {
        this.addLog(`${this.players[this.currentPlayer].name}がパスしました`);
        this.passCount++;
        
        if (this.passCount >= this.players.filter(p => !p.isFinished).length - 1) {
            this.currentCards = [];
            this.lastPlayedBy = -1;
            this.addLog('全員パスしたため場が流れました');
        }
        
        this.nextTurn();
        this.updateUI();
    }

    nextTurn() {
        do {
            this.currentPlayer = (this.currentPlayer + 1) % this.players.length;
        } while (this.players[this.currentPlayer].isFinished);

        if (!this.players[this.currentPlayer].isHuman) {
            setTimeout(() => this.cpuTurn(), 1000);
        }
    }

    cpuTurn() {
        const player = this.players[this.currentPlayer];
        const playableCards = this.findPlayableCards(player.cards);
        
        if (playableCards.length > 0 && Math.random() > 0.3) {
            const randomPlay = playableCards[Math.floor(Math.random() * playableCards.length)];
            this.playCards(this.currentPlayer, randomPlay);
        } else {
            this.passTurn();
        }
    }

    findPlayableCards(cards) {
        const playableCards = [];
        
        for (let i = 1; i <= 4; i++) {
            for (let j = 0; j <= cards.length - i; j++) {
                const combination = cards.slice(j, j + i);
                if (this.isValidPlay(combination)) {
                    playableCards.push(combination);
                }
            }
        }
        
        return playableCards;
    }

    endGame() {
        this.gameState = 'finished';
        
        const remainingPlayers = this.players.filter(p => !p.isFinished);
        remainingPlayers.forEach((player, index) => {
            player.isFinished = true;
            player.rank = this.ranks[this.players.filter(p => p.isFinished).length - remainingPlayers.length + index];
        });

        this.showResults();
        this.addLog('ゲーム終了！');
    }

    showResults() {
        const resultsPanel = document.getElementById('results-panel');
        const finalRanks = document.getElementById('final-ranks');
        
        const sortedPlayers = [...this.players].sort((a, b) => {
            return this.ranks.indexOf(a.rank) - this.ranks.indexOf(b.rank);
        });

        finalRanks.innerHTML = sortedPlayers.map(player => 
            `<div class="rank-item">
                <span class="rank">${player.rank}</span>
                <span class="player-name">${player.name}</span>
            </div>`
        ).join('');

        resultsPanel.style.display = 'block';
    }

    nextGame() {
        this.resetGame();
        this.startGame();
    }

    resetGame() {
        this.gameState = 'setup';
        this.players = [];
        this.currentCards = [];
        this.passCount = 0;
        this.lastPlayedBy = -1;
        this.revolution = false;
        this.gameHistory = [];
        
        this.initializeDeck();
        
        document.getElementById('start-game').disabled = false;
        document.getElementById('pass-turn').disabled = true;
        document.getElementById('play-cards').disabled = true;
        document.getElementById('results-panel').style.display = 'none';
        
        document.getElementById('current-cards').innerHTML = '<div class="no-cards">カードが出されていません</div>';
        document.getElementById('hand-cards').innerHTML = '';
        document.getElementById('other-players').innerHTML = '';
        document.getElementById('log-content').innerHTML = '';
        document.getElementById('current-player-name').textContent = '-';
        document.getElementById('revolution-status').textContent = '通常';
        document.getElementById('cards-count').textContent = '0';
    }

    addLog(message) {
        const logContent = document.getElementById('log-content');
        const logItem = document.createElement('div');
        logItem.className = 'log-item';
        logItem.textContent = `${new Date().toLocaleTimeString()}: ${message}`;
        logContent.appendChild(logItem);
        logContent.scrollTop = logContent.scrollHeight;
        
        this.gameHistory.push({
            timestamp: new Date(),
            message: message
        });
    }
}

if (typeof window !== 'undefined') {
    window.DaifugoGame = DaifugoGame;
}
