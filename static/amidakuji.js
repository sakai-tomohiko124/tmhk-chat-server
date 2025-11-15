class AmidakujiGame {
    constructor() {
        this.players = [];
        this.prizes = [];
        this.lines = [];
        this.gameState = 'setup';
        this.results = new Map();
        this.canvas = null;
        this.ctx = null;
        this.settings = {
            playerCount: 4,
            lineCount: 6,
            animationSpeed: 50,
            lineWidth: 3,
            colors: {
                vertical: '#333',
                horizontal: '#e74c3c',
                player: '#3498db',
                prize: '#2ecc71',
                trace: '#f39c12'
            }
        };
    }

    initialize(containerId) {
        this.container = document.getElementById(containerId);
        this.createUI();
        this.setupEventListeners();
        this.gameState = 'setup';
    }

    createUI() {
        this.container.innerHTML = `
            <div class="amidakuji-game">
                <div class="game-header">
                    <h2>あみだくじ</h2>
                    <div class="game-controls">
                        <button id="add-player" class="btn btn-secondary">参加者追加</button>
                        <button id="add-prize" class="btn btn-secondary">景品追加</button>
                        <button id="generate-lines" class="btn btn-primary">線を生成</button>
                        <button id="start-game" class="btn btn-success" disabled>ゲーム開始</button>
                        <button id="reset-game" class="btn btn-outline">リセット</button>
                    </div>
                </div>
                
                <div class="setup-panel">
                    <div class="players-section">
                        <h3>参加者</h3>
                        <div class="players-list"></div>
                        <div class="add-player-form">
                            <input type="text" id="player-name" placeholder="参加者名" maxlength="10">
                            <button id="add-player-btn" class="btn btn-sm btn-primary">追加</button>
                        </div>
                    </div>
                    
                    <div class="prizes-section">
                        <h3>景品</h3>
                        <div class="prizes-list"></div>
                        <div class="add-prize-form">
                            <input type="text" id="prize-name" placeholder="景品名" maxlength="15">
                            <button id="add-prize-btn" class="btn btn-sm btn-primary">追加</button>
                        </div>
                    </div>
                </div>
                
                <div class="game-canvas-container">
                    <canvas id="amidakuji-canvas" width="800" height="600"></canvas>
                </div>
                
                <div class="results-panel" style="display: none;">
                    <h3>結果</h3>
                    <div class="results-list"></div>
                </div>
                
                <div class="game-settings">
                    <details>
                        <summary>詳細設定</summary>
                        <div class="settings-grid">
                            <label>
                                横線の本数:
                                <input type="range" id="line-count" min="3" max="15" value="6">
                                <span id="line-count-value">6</span>
                            </label>
                            <label>
                                アニメーション速度:
                                <input type="range" id="animation-speed" min="10" max="100" value="50">
                                <span id="animation-speed-value">50ms</span>
                            </label>
                        </div>
                    </details>
                </div>
            </div>
        `;

        this.canvas = document.getElementById('amidakuji-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.resizeCanvas();
    }

    setupEventListeners() {
        document.getElementById('add-player-btn').addEventListener('click', () => this.addPlayer());
        document.getElementById('add-prize-btn').addEventListener('click', () => this.addPrize());
        document.getElementById('generate-lines').addEventListener('click', () => this.generateLines());
        document.getElementById('start-game').addEventListener('click', () => this.startGame());
        document.getElementById('reset-game').addEventListener('click', () => this.resetGame());

        document.getElementById('player-name').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addPlayer();
        });

        document.getElementById('prize-name').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addPrize();
        });

        document.getElementById('line-count').addEventListener('input', (e) => {
            this.settings.lineCount = parseInt(e.target.value);
            document.getElementById('line-count-value').textContent = e.target.value;
        });

        document.getElementById('animation-speed').addEventListener('input', (e) => {
            this.settings.animationSpeed = parseInt(e.target.value);
            document.getElementById('animation-speed-value').textContent = e.target.value + 'ms';
        });

        window.addEventListener('resize', () => this.resizeCanvas());
    }

    addPlayer() {
        const input = document.getElementById('player-name');
        const name = input.value.trim();
        
        if (!name) return;
        if (this.players.length >= 10) {
            alert('参加者は最大10人までです');
            return;
        }
        if (this.players.some(p => p.name === name)) {
            alert('同じ名前の参加者が既にいます');
            return;
        }

        this.players.push({
            id: this.generateId(),
            name: name,
            color: this.getRandomColor()
        });

        input.value = '';
        this.updatePlayersDisplay();
        this.updateGameState();
    }

    addPrize() {
        const input = document.getElementById('prize-name');
        const name = input.value.trim();
        
        if (!name) return;
        if (this.prizes.length >= 10) {
            alert('景品は最大10個までです');
            return;
        }

        this.prizes.push({
            id: this.generateId(),
            name: name
        });

        input.value = '';
        this.updatePrizesDisplay();
        this.updateGameState();
    }

    updatePlayersDisplay() {
        const list = document.querySelector('.players-list');
        list.innerHTML = this.players.map(player => `
            <div class="player-item" style="border-left: 4px solid ${player.color}">
                <span>${player.name}</span>
                <button class="remove-btn" onclick="amidakujiGame.removePlayer('${player.id}')">&times;</button>
            </div>
        `).join('');
    }

    updatePrizesDisplay() {
        const list = document.querySelector('.prizes-list');
        list.innerHTML = this.prizes.map(prize => `
            <div class="prize-item">
                <span>${prize.name}</span>
                <button class="remove-btn" onclick="amidakujiGame.removePrize('${prize.id}')">&times;</button>
            </div>
        `).join('');
    }

    removePlayer(playerId) {
        this.players = this.players.filter(p => p.id !== playerId);
        this.updatePlayersDisplay();
        this.updateGameState();
    }

    removePrize(prizeId) {
        this.prizes = this.prizes.filter(p => p.id !== prizeId);
        this.updatePrizesDisplay();
        this.updateGameState();
    }

    updateGameState() {
        const canGenerate = this.players.length >= 2 && this.prizes.length >= 2;
        document.getElementById('generate-lines').disabled = !canGenerate;
        
        const canStart = canGenerate && this.lines.length > 0;
        document.getElementById('start-game').disabled = !canStart;
    }

    generateLines() {
        if (this.players.length !== this.prizes.length) {
            const diff = Math.abs(this.players.length - this.prizes.length);
            if (this.players.length > this.prizes.length) {
                confirm(`参加者が${diff}人多いです。空の景品を追加しますか？`) && this.addEmptyPrizes(diff);
            } else {
                confirm(`景品が${diff}個多いです。空の参加者を追加しますか？`) && this.addEmptyPlayers(diff);
            }
        }

        this.lines = [];
        const playerCount = Math.max(this.players.length, this.prizes.length);
        
        for (let i = 0; i < this.settings.lineCount; i++) {
            const validPositions = [];
            for (let j = 0; j < playerCount - 1; j++) {
                validPositions.push(j);
            }
            
            if (this.lines.length > 0) {
                const lastLines = this.lines[this.lines.length - 1];
                validPositions.forEach((pos, index) => {
                    if (lastLines.includes(pos) || lastLines.includes(pos - 1) || lastLines.includes(pos + 1)) {
                        validPositions.splice(index, 1);
                    }
                });
            }
            
            const lineCount = Math.floor(Math.random() * Math.min(3, validPositions.length)) + 1;
            const selectedLines = [];
            
            for (let k = 0; k < lineCount; k++) {
                if (validPositions.length === 0) break;
                const randomIndex = Math.floor(Math.random() * validPositions.length);
                const selectedPos = validPositions.splice(randomIndex, 1)[0];
                selectedLines.push(selectedPos);
                
                validPositions.forEach((pos, index) => {
                    if (Math.abs(pos - selectedPos) <= 1) {
                        validPositions.splice(index, 1);
                    }
                });
            }
            
            this.lines.push(selectedLines.sort((a, b) => a - b));
        }

        this.drawAmidakuji();
        this.updateGameState();
    }

    addEmptyPrizes(count) {
        for (let i = 0; i < count; i++) {
            this.prizes.push({
                id: this.generateId(),
                name: 'はずれ'
            });
        }
        this.updatePrizesDisplay();
    }

    addEmptyPlayers(count) {
        for (let i = 0; i < count; i++) {
            this.players.push({
                id: this.generateId(),
                name: `参加者${this.players.length + 1}`,
                color: this.getRandomColor()
            });
        }
        this.updatePlayersDisplay();
    }

    drawAmidakuji() {
        const ctx = this.ctx;
        const canvas = this.canvas;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const playerCount = Math.max(this.players.length, this.prizes.length);
        const margin = 100;
        const spacing = (canvas.width - 2 * margin) / (playerCount - 1);
        const topY = 80;
        const bottomY = canvas.height - 80;
        const lineSpacing = (bottomY - topY) / (this.lines.length + 1);

        ctx.lineWidth = this.settings.lineWidth;

        for (let i = 0; i < playerCount; i++) {
            const x = margin + i * spacing;
            
            ctx.strokeStyle = this.settings.colors.vertical;
            ctx.beginPath();
            ctx.moveTo(x, topY);
            ctx.lineTo(x, bottomY);
            ctx.stroke();
            
            if (i < this.players.length) {
                ctx.fillStyle = this.players[i].color;
                ctx.fillRect(x - 20, topY - 30, 40, 20);
                ctx.fillStyle = '#fff';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(this.players[i].name, x, topY - 15);
            }
            
            if (i < this.prizes.length) {
                ctx.fillStyle = this.settings.colors.prize;
                ctx.fillRect(x - 30, bottomY + 10, 60, 20);
                ctx.fillStyle = '#fff';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(this.prizes[i].name, x, bottomY + 25);
            }
        }

        this.lines.forEach((horizontalLines, lineIndex) => {
            const y = topY + (lineIndex + 1) * lineSpacing;
            
            horizontalLines.forEach(pos => {
                const x1 = margin + pos * spacing;
                const x2 = margin + (pos + 1) * spacing;
                
                ctx.strokeStyle = this.settings.colors.horizontal;
                ctx.beginPath();
                ctx.moveTo(x1, y);
                ctx.lineTo(x2, y);
                ctx.stroke();
                
                ctx.fillStyle = this.settings.colors.horizontal;
                ctx.beginPath();
                ctx.arc(x1, y, 4, 0, 2 * Math.PI);
                ctx.arc(x2, y, 4, 0, 2 * Math.PI);
                ctx.fill();
            });
        });
    }

    async startGame() {
        this.gameState = 'playing';
        this.results.clear();
        
        document.querySelector('.game-controls').style.pointerEvents = 'none';
        
        for (let playerIndex = 0; playerIndex < this.players.length; playerIndex++) {
            await this.tracePlayerPath(playerIndex);
        }
        
        this.showResults();
        this.gameState = 'finished';
        document.querySelector('.game-controls').style.pointerEvents = 'auto';
    }

    async tracePlayerPath(playerIndex) {
        const canvas = this.canvas;
        const ctx = this.ctx;
        const playerCount = Math.max(this.players.length, this.prizes.length);
        const margin = 100;
        const spacing = (canvas.width - 2 * margin) / (playerCount - 1);
        const topY = 80;
        const bottomY = canvas.height - 80;
        const lineSpacing = (bottomY - topY) / (this.lines.length + 1);

        let currentPosition = playerIndex;
        const path = [{ x: margin + currentPosition * spacing, y: topY }];

        ctx.strokeStyle = this.players[playerIndex].color;
        ctx.lineWidth = 6;
        ctx.globalAlpha = 0.8;

        for (let lineIndex = 0; lineIndex < this.lines.length; lineIndex++) {
            const y = topY + (lineIndex + 1) * lineSpacing;
            const horizontalLines = this.lines[lineIndex];
            
            path.push({ x: margin + currentPosition * spacing, y: y });
            
            if (horizontalLines.includes(currentPosition)) {
                currentPosition++;
                path.push({ x: margin + currentPosition * spacing, y: y });
            } else if (horizontalLines.includes(currentPosition - 1)) {
                currentPosition--;
                path.push({ x: margin + currentPosition * spacing, y: y });
            }
        }

        path.push({ x: margin + currentPosition * spacing, y: bottomY });

        for (let i = 1; i < path.length; i++) {
            ctx.beginPath();
            ctx.moveTo(path[i - 1].x, path[i - 1].y);
            ctx.lineTo(path[i].x, path[i].y);
            ctx.stroke();
            
            await this.sleep(this.settings.animationSpeed);
        }

        ctx.globalAlpha = 1;
        
        this.results.set(this.players[playerIndex].id, {
            player: this.players[playerIndex],
            prize: this.prizes[currentPosition] || { name: 'なし' },
            position: currentPosition
        });
    }

    showResults() {
        const resultsList = document.querySelector('.results-list');
        const results = Array.from(this.results.values());
        
        resultsList.innerHTML = results.map(result => `
            <div class="result-item" style="border-left: 4px solid ${result.player.color}">
                <div class="result-player">${result.player.name}</div>
                <div class="result-arrow">→</div>
                <div class="result-prize">${result.prize.name}</div>
            </div>
        `).join('');
        
        document.querySelector('.results-panel').style.display = 'block';
    }

    resetGame() {
        this.gameState = 'setup';
        this.lines = [];
        this.results.clear();
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        document.querySelector('.results-panel').style.display = 'none';
        document.querySelector('.game-controls').style.pointerEvents = 'auto';
        
        this.updateGameState();
    }

    resizeCanvas() {
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();
        
        this.canvas.width = Math.min(800, rect.width - 40);
        this.canvas.height = 600;
        
        if (this.lines.length > 0) {
            this.drawAmidakuji();
        }
    }

    getRandomColor() {
        const colors = [
            '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#e67e22', '#34495e', '#e91e63', '#ff5722'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

if (typeof window !== 'undefined') {
    window.AmidakujiGame = AmidakujiGame;
}
