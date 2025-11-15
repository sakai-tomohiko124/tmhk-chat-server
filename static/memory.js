class MemoryGame {
    constructor() {
        this.cards = [];
        this.flippedCards = [];
        this.matchedCards = [];
        this.gameState = 'setup';
        this.currentPlayer = 0;
        this.players = [];
        this.moves = 0;
        this.startTime = null;
        this.gameTimer = null;
        this.settings = {
            difficulty: 'easy',
            theme: 'numbers',
            playerCount: 1,
            timeLimit: 0,
            cardSets: {
                easy: { rows: 4, cols: 4 },
                medium: { rows: 6, cols: 6 },
                hard: { rows: 8, cols: 8 }
            }
        };
        this.themes = {
            numbers: { name: '数字', cards: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32'] },
            animals: { name: '動物', cards: ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🐔', '🐧', '🐦', '🐤', '🦄', '🐺', '🐗', '🦔', '🐙', '🦀', '🐠', '🐟', '🐬', '🐳', '🦈', '🐊', '🐢'] },
            fruits: { name: '果物', cards: ['🍎', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🍈', '🍑', '🍒', '🥝', '🍍', '🥭', '🍅', '🍆', '🥑', '🌶️', '🌽', '🥕', '🥔', '🍠', '🥜', '🌰', '🍄', '🥒', '🥬', '🥦', '🧄', '🧅', '🍯', '🧈', '🥖'] },
            shapes: { name: '図形', cards: ['●', '■', '▲', '♦', '★', '♠', '♥', '♣', '◆', '▼', '▶', '◀', '🔸', '🔹', '🔶', '🔷', '⬛', '⬜', '🔺', '🔻', '🔳', '🔲', '◼', '◻', '▪', '▫', '🟤', '🟣', '🟢', '🟡', '🔴', '🟠'] }
        };
    }

    initialize(containerId) {
        this.container = document.getElementById(containerId);
        this.createUI();
        this.setupEventListeners();
        this.updateDifficultySettings();
    }

    createUI() {
        this.container.innerHTML = `
            <div class="memory-game">
                <div class="game-header">
                    <h2>神経衰弱</h2>
                    <div class="game-info">
                        <span class="moves-count">手数: <span id="moves-count">0</span></span>
                        <span class="timer">時間: <span id="game-timer">00:00</span></span>
                        <span class="current-player">プレイヤー: <span id="current-player-name">プレイヤー1</span></span>
                    </div>
                    <div class="game-controls">
                        <button id="start-game" class="btn btn-success">ゲーム開始</button>
                        <button id="pause-game" class="btn btn-secondary" disabled>一時停止</button>
                        <button id="reset-game" class="btn btn-outline">リセット</button>
                        <button id="hint-button" class="btn btn-warning">ヒント</button>
                    </div>
                </div>

                <div class="settings-panel">
                    <div class="settings-row">
                        <label>
                            難易度:
                            <select id="difficulty-select">
                                <option value="easy">簡単 (4x4)</option>
                                <option value="medium">普通 (6x6)</option>
                                <option value="hard">難しい (8x8)</option>
                            </select>
                        </label>
                        <label>
                            テーマ:
                            <select id="theme-select">
                                <option value="numbers">数字</option>
                                <option value="animals">動物</option>
                                <option value="fruits">果物</option>
                                <option value="shapes">図形</option>
                            </select>
                        </label>
                        <label>
                            プレイヤー数:
                            <select id="player-count">
                                <option value="1">1人</option>
                                <option value="2">2人</option>
                                <option value="3">3人</option>
                                <option value="4">4人</option>
                            </select>
                        </label>
                        <label>
                            制限時間 (秒):
                            <input type="number" id="time-limit" min="0" max="600" value="0" placeholder="0=無制限">
                        </label>
                    </div>
                </div>

                <div class="players-score" id="players-score"></div>

                <div class="game-board" id="game-board"></div>

                <div class="game-stats" id="game-stats">
                    <div class="stat-item">
                        <span class="stat-label">マッチ数:</span>
                        <span class="stat-value" id="matches-count">0</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">成功率:</span>
                        <span class="stat-value" id="success-rate">0%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">残りペア:</span>
                        <span class="stat-value" id="remaining-pairs">0</span>
                    </div>
                </div>

                <div class="results-panel" id="results-panel" style="display: none;">
                    <h3>ゲーム結果</h3>
                    <div class="final-score" id="final-score"></div>
                    <div class="game-summary" id="game-summary"></div>
                    <button id="play-again" class="btn btn-success">もう一度プレイ</button>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        document.getElementById('start-game').addEventListener('click', () => this.startGame());
        document.getElementById('pause-game').addEventListener('click', () => this.pauseGame());
        document.getElementById('reset-game').addEventListener('click', () => this.resetGame());
        document.getElementById('hint-button').addEventListener('click', () => this.showHint());
        document.getElementById('play-again').addEventListener('click', () => this.startNewGame());

        document.getElementById('difficulty-select').addEventListener('change', (e) => {
            this.settings.difficulty = e.target.value;
            this.updateDifficultySettings();
        });

        document.getElementById('theme-select').addEventListener('change', (e) => {
            this.settings.theme = e.target.value;
        });

        document.getElementById('player-count').addEventListener('change', (e) => {
            this.settings.playerCount = parseInt(e.target.value);
            this.initializePlayers();
        });

        document.getElementById('time-limit').addEventListener('change', (e) => {
            this.settings.timeLimit = parseInt(e.target.value) || 0;
        });
    }

    updateDifficultySettings() {
        const { rows, cols } = this.settings.cardSets[this.settings.difficulty];
        const totalPairs = (rows * cols) / 2;
        document.getElementById('remaining-pairs').textContent = totalPairs;
    }

    initializePlayers() {
        this.players = [];
        for (let i = 0; i < this.settings.playerCount; i++) {
            this.players.push({
                id: i,
                name: `プレイヤー${i + 1}`,
                score: 0,
                matches: 0
            });
        }
        this.updatePlayersDisplay();
    }

    updatePlayersDisplay() {
        const playersScore = document.getElementById('players-score');
        if (this.settings.playerCount === 1) {
            playersScore.style.display = 'none';
            return;
        }

        playersScore.style.display = 'block';
        playersScore.innerHTML = this.players.map((player, index) => 
            `<div class="player-score ${index === this.currentPlayer ? 'current' : ''}">
                <span class="player-name">${player.name}</span>
                <span class="player-points">${player.score}点</span>
                <span class="player-matches">${player.matches}ペア</span>
            </div>`
        ).join('');
    }

    startGame() {
        this.gameState = 'playing';
        this.initializeGame();
        this.createBoard();
        this.startTimer();
        
        document.getElementById('start-game').disabled = true;
        document.getElementById('pause-game').disabled = false;
    }

    initializeGame() {
        this.cards = [];
        this.flippedCards = [];
        this.matchedCards = [];
        this.moves = 0;
        this.startTime = Date.now();
        this.currentPlayer = 0;
        
        this.initializePlayers();
        this.generateCards();
        this.shuffleCards();
        
        document.getElementById('moves-count').textContent = '0';
        document.getElementById('matches-count').textContent = '0';
        document.getElementById('success-rate').textContent = '0%';
    }

    generateCards() {
        const { rows, cols } = this.settings.cardSets[this.settings.difficulty];
        const totalCards = rows * cols;
        const pairsNeeded = totalCards / 2;
        const themeCards = this.themes[this.settings.theme].cards;
        
        const selectedCards = themeCards.slice(0, pairsNeeded);
        
        selectedCards.forEach((cardValue, index) => {
            this.cards.push(
                { id: index * 2, value: cardValue, matched: false },
                { id: index * 2 + 1, value: cardValue, matched: false }
            );
        });
    }

    shuffleCards() {
        for (let i = this.cards.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.cards[i], this.cards[j]] = [this.cards[j], this.cards[i]];
        }
    }

    createBoard() {
        const { rows, cols } = this.settings.cardSets[this.settings.difficulty];
        const gameBoard = document.getElementById('game-board');
        
        gameBoard.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
        gameBoard.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
        
        gameBoard.innerHTML = this.cards.map((card, index) => 
            `<div class="memory-card" data-card-id="${card.id}" data-index="${index}">
                <div class="card-front"></div>
                <div class="card-back">${card.value}</div>
            </div>`
        ).join('');

        gameBoard.querySelectorAll('.memory-card').forEach(cardElement => {
            cardElement.addEventListener('click', () => this.flipCard(cardElement));
        });
    }

    flipCard(cardElement) {
        if (this.gameState !== 'playing') return;
        if (cardElement.classList.contains('flipped') || cardElement.classList.contains('matched')) return;
        if (this.flippedCards.length >= 2) return;

        const cardIndex = parseInt(cardElement.dataset.index);
        const card = this.cards[cardIndex];

        cardElement.classList.add('flipped');
        this.flippedCards.push({ element: cardElement, card: card, index: cardIndex });

        if (this.flippedCards.length === 2) {
            this.moves++;
            document.getElementById('moves-count').textContent = this.moves;
            setTimeout(() => this.checkMatch(), 1000);
        }
    }

    checkMatch() {
        const [first, second] = this.flippedCards;
        
        if (first.card.value === second.card.value) {
            this.handleMatch(first, second);
        } else {
            this.handleMismatch(first, second);
        }
        
        this.flippedCards = [];
        this.updateStats();
        
        if (this.checkGameComplete()) {
            this.endGame();
        } else if (this.settings.playerCount > 1) {
            this.nextPlayer();
        }
    }

    handleMatch(first, second) {
        first.element.classList.add('matched');
        second.element.classList.add('matched');
        first.card.matched = true;
        second.card.matched = true;
        
        this.matchedCards.push(first.card, second.card);
        
        if (this.settings.playerCount > 1) {
            this.players[this.currentPlayer].score += 10;
            this.players[this.currentPlayer].matches += 1;
            this.updatePlayersDisplay();
        }
        
        this.addMatchEffect(first.element, second.element);
    }

    handleMismatch(first, second) {
        first.element.classList.remove('flipped');
        second.element.classList.remove('flipped');
    }

    addMatchEffect(element1, element2) {
        [element1, element2].forEach(element => {
            element.classList.add('match-effect');
            setTimeout(() => {
                element.classList.remove('match-effect');
            }, 600);
        });
    }

    nextPlayer() {
        if (this.flippedCards.length === 0 || !this.isLastMoveMatch()) {
            this.currentPlayer = (this.currentPlayer + 1) % this.settings.playerCount;
            document.getElementById('current-player-name').textContent = this.players[this.currentPlayer].name;
            this.updatePlayersDisplay();
        }
    }

    isLastMoveMatch() {
        return this.flippedCards.length === 2 && 
               this.flippedCards[0].card.value === this.flippedCards[1].card.value;
    }

    updateStats() {
        const matchesCount = this.matchedCards.length / 2;
        const successRate = this.moves > 0 ? Math.round((matchesCount / this.moves) * 100) : 0;
        const remainingPairs = (this.cards.length / 2) - matchesCount;
        
        document.getElementById('matches-count').textContent = matchesCount;
        document.getElementById('success-rate').textContent = successRate + '%';
        document.getElementById('remaining-pairs').textContent = remainingPairs;
    }

    checkGameComplete() {
        return this.matchedCards.length === this.cards.length;
    }

    startTimer() {
        this.gameTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            document.getElementById('game-timer').textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            if (this.settings.timeLimit > 0 && elapsed >= this.settings.timeLimit) {
                this.endGame('timeout');
            }
        }, 1000);
    }

    pauseGame() {
        if (this.gameState === 'playing') {
            this.gameState = 'paused';
            clearInterval(this.gameTimer);
            document.getElementById('pause-game').textContent = '再開';
            document.querySelectorAll('.memory-card').forEach(card => {
                card.style.pointerEvents = 'none';
            });
        } else if (this.gameState === 'paused') {
            this.gameState = 'playing';
            this.startTimer();
            document.getElementById('pause-game').textContent = '一時停止';
            document.querySelectorAll('.memory-card').forEach(card => {
                card.style.pointerEvents = 'auto';
            });
        }
    }

    showHint() {
        if (this.gameState !== 'playing') return;
        
        const unmatchedCards = this.cards.filter(card => !card.matched);
        if (unmatchedCards.length < 2) return;
        
        const cardValue = unmatchedCards[Math.floor(Math.random() * unmatchedCards.length)].value;
        const hintCards = unmatchedCards.filter(card => card.value === cardValue);
        
        if (hintCards.length >= 2) {
            const hintElements = hintCards.slice(0, 2).map(card => {
                const index = this.cards.findIndex(c => c.id === card.id);
                return document.querySelector(`[data-index="${index}"]`);
            });
            
            hintElements.forEach(element => {
                element.classList.add('hint');
                setTimeout(() => {
                    element.classList.remove('hint');
                }, 2000);
            });
        }
    }

    endGame(reason = 'complete') {
        this.gameState = 'finished';
        clearInterval(this.gameTimer);
        
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        this.showResults(elapsed, reason);
        
        document.getElementById('start-game').disabled = false;
        document.getElementById('pause-game').disabled = true;
    }

    showResults(elapsed, reason) {
        const resultsPanel = document.getElementById('results-panel');
        const finalScore = document.getElementById('final-score');
        const gameSummary = document.getElementById('game-summary');
        
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        const matchesCount = this.matchedCards.length / 2;
        const successRate = this.moves > 0 ? Math.round((matchesCount / this.moves) * 100) : 0;
        
        if (this.settings.playerCount === 1) {
            if (reason === 'timeout') {
                finalScore.innerHTML = '<h4>時間切れ！</h4>';
            } else {
                finalScore.innerHTML = '<h4>ゲームクリア！</h4>';
            }
            
            gameSummary.innerHTML = `
                <div class="summary-stats">
                    <div class="summary-item">
                        <span class="summary-label">プレイ時間:</span>
                        <span class="summary-value">${minutes}分${seconds}秒</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">手数:</span>
                        <span class="summary-value">${this.moves}手</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">成功率:</span>
                        <span class="summary-value">${successRate}%</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">マッチ数:</span>
                        <span class="summary-value">${matchesCount}ペア</span>
                    </div>
                </div>
            `;
        } else {
            const winner = this.players.reduce((max, player) => 
                player.score > max.score ? player : max
            );
            
            finalScore.innerHTML = `<h4>${winner.name}の勝利！</h4>`;
            
            gameSummary.innerHTML = `
                <div class="final-ranking">
                    ${this.players.sort((a, b) => b.score - a.score).map((player, index) => 
                        `<div class="rank-item">
                            <span class="rank">${index + 1}位</span>
                            <span class="player-name">${player.name}</span>
                            <span class="final-score">${player.score}点 (${player.matches}ペア)</span>
                        </div>`
                    ).join('')}
                </div>
                <div class="game-stats">
                    <p>プレイ時間: ${minutes}分${seconds}秒</p>
                    <p>総手数: ${this.moves}手</p>
                </div>
            `;
        }
        
        resultsPanel.style.display = 'block';
    }

    startNewGame() {
        document.getElementById('results-panel').style.display = 'none';
        this.resetGame();
        this.startGame();
    }

    resetGame() {
        this.gameState = 'setup';
        clearInterval(this.gameTimer);
        
        this.cards = [];
        this.flippedCards = [];
        this.matchedCards = [];
        this.moves = 0;
        this.currentPlayer = 0;
        
        document.getElementById('game-board').innerHTML = '';
        document.getElementById('moves-count').textContent = '0';
        document.getElementById('game-timer').textContent = '00:00';
        document.getElementById('matches-count').textContent = '0';
        document.getElementById('success-rate').textContent = '0%';
        document.getElementById('current-player-name').textContent = 'プレイヤー1';
        document.getElementById('results-panel').style.display = 'none';
        
        document.getElementById('start-game').disabled = false;
        document.getElementById('pause-game').disabled = true;
        document.getElementById('pause-game').textContent = '一時停止';
        
        this.updateDifficultySettings();
        this.initializePlayers();
    }
}

if (typeof window !== 'undefined') {
    window.MemoryGame = MemoryGame;
}
