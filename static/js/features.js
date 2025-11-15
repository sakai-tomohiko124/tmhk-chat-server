// 機能管理システム
class FeatureManager {
    constructor() {
        this.currentFeature = null;
        this.modal = null;
        this.container = null;
        this.init();
    }

    init() {
        // タブナビゲーション
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => this.switchTab(button));
        });

        // 機能カード
        const featureCards = document.querySelectorAll('.feature-card');
        featureCards.forEach(card => {
            card.addEventListener('click', () => this.openFeature(card.dataset.feature));
        });

        // モーダル
        this.modal = document.getElementById('feature-modal');
        this.container = document.getElementById('feature-container');
        const closeBtn = document.querySelector('.modal-close');
        closeBtn.addEventListener('click', () => this.closeModal());
        
        window.addEventListener('click', (event) => {
            if (event.target === this.modal) {
                this.closeModal();
            }
        });
    }

    switchTab(button) {
        // すべてのタブボタンとコンテンツから active クラスを削除
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        // クリックされたボタンと対応するコンテンツに active クラスを追加
        button.classList.add('active');
        const tabId = button.dataset.tab;
        document.getElementById(tabId).classList.add('active');
    }

    openFeature(featureName) {
        this.currentFeature = featureName;
        this.container.innerHTML = this.getFeatureHTML(featureName);
        this.modal.style.display = 'block';
        this.initializeFeature(featureName);
    }

    closeModal() {
        this.modal.style.display = 'none';
        this.container.innerHTML = '';
        this.currentFeature = null;
    }

    getFeatureHTML(featureName) {
        const features = {
            'audio-call': this.getAudioCallHTML(),
            'group-video-call': this.getGroupVideoCallHTML(),
            'group-audio-call': this.getGroupAudioCallHTML(),
            'call-recording': this.getCallRecordingHTML(),
            'call-history': this.getCallHistoryHTML(),
            'ai-chatbot': this.getAIChatbotHTML(),
            'auto-translate': this.getAutoTranslateHTML(),
            'emotion-analysis': this.getEmotionAnalysisHTML(),
            'image-recognition': this.getImageRecognitionHTML(),
            'keyword-extractor': this.getKeywordExtractorHTML(),
            'auto-classifier': this.getAutoClassifierHTML(),
            'image-sender': this.getImageSenderHTML(),
            'gif-support': this.getGIFSupportHTML(),
            'file-sharing': this.getFileSharingHTML(),
            'album-creator': this.getAlbumCreatorHTML(),
            'beautify-filter': this.getBeautifyFilterHTML(),
            'media-auto-save': this.getMediaAutoSaveHTML(),
            'mini-game': this.getMiniGameHTML(),
            'quiz-game': this.getQuizGameHTML(),
            'emoji-quiz': this.getEmojiQuizHTML(),
            'number-guessing': this.getNumberGuessingHTML(),
            'cooperative-game': this.getCooperativeGameHTML(),
            'project-management': this.getProjectManagementHTML(),
            'document-management': this.getDocumentManagementHTML(),
            'calendar-integration': this.getCalendarIntegrationHTML(),
            'meeting-room': this.getMeetingRoomHTML(),
            'attendance': this.getAttendanceHTML(),
            'expense-management': this.getExpenseManagementHTML(),
            'gmail-integration': this.getGmailIntegrationHTML(),
            'youtube-integration': this.getYouTubeIntegrationHTML(),
            'qr-code': this.getQRCodeHTML()
        };

        return features[featureName] || '<p>この機能は準備中です</p>';
    }

    // 各機能のHTML生成メソッド
    getAudioCallHTML() {
        return `
            <div class="feature-audio-call">
                <h2>音声通話</h2>
                <div id="call-status">待機中...</div>
                <div class="call-controls">
                    <button id="start-call-btn" class="btn btn-primary">通話開始</button>
                    <button id="end-call-btn" class="btn btn-danger" style="display:none;">通話終了</button>
                </div>
                <div id="call-timer" style="display:none;">通話時間: <span id="timer">00:00</span></div>
            </div>
        `;
    }

    getGroupVideoCallHTML() {
        return `
            <div class="feature-video-call">
                <h2>グループビデオ通話</h2>
                <div class="video-container">
                    <video id="local-video" autoplay muted playsinline></video>
                    <div id="remote-videos"></div>
                </div>
                <div class="call-controls">
                    <button id="start-video-btn" class="btn btn-primary">ビデオ開始</button>
                    <button id="end-video-btn" class="btn btn-danger" style="display:none;">終了</button>
                </div>
            </div>
        `;
    }

    getGroupAudioCallHTML() {
        return `
            <div class="feature-group-audio">
                <h2>グループ音声通話</h2>
                <div id="participants">参加者: なし</div>
                <div class="call-controls">
                    <button id="join-group-call-btn" class="btn btn-primary">参加</button>
                    <button id="leave-group-call-btn" class="btn btn-danger" style="display:none;">退出</button>
                </div>
                <div id="group-timer" style="display:none;">通話時間: <span id="group-timer-val">00:00</span></div>
            </div>
        `;
    }

    getCallRecordingHTML() {
        return `
            <div class="feature-call-recording">
                <h2>通話録音</h2>
                <div class="recording-controls">
                    <button id="start-recording-btn" class="btn btn-primary">録音開始</button>
                    <button id="stop-recording-btn" class="btn btn-danger" style="display:none;">録音停止</button>
                </div>
                <div id="recording-status">待機中</div>
                <audio id="recorded-audio" controls style="display:none; width:100%; margin-top:20px;"></audio>
            </div>
        `;
    }

    getCallHistoryHTML() {
        return `
            <div class="feature-call-history">
                <h2>通話履歴</h2>
                <ul id="history-list">
                    <li>2025-09-26 - 音声通話 (5分)</li>
                    <li>2025-09-25 - ビデオ通話 (8分)</li>
                    <li>2025-09-24 - グループ通話 (15分)</li>
                </ul>
            </div>
        `;
    }

    getAIChatbotHTML() {
        return `
            <div class="feature-ai-chatbot">
                <h2>AIチャットボット</h2>
                <div id="ai-chat-messages" style="border:1px solid #ccc; padding:10px; height:200px; overflow-y:scroll; margin-bottom:10px;"></div>
                <div class="input-group">
                    <input type="text" id="ai-input" class="form-control" placeholder="メッセージを入力...">
                    <button id="ai-send-btn" class="btn btn-primary">送信</button>
                </div>
            </div>
        `;
    }

    getAutoTranslateHTML() {
        return `
            <div class="feature-auto-translate">
                <h2>自動翻訳</h2>
                <textarea id="translate-input" class="form-control" placeholder="翻訳したいテキストを入力" rows="4"></textarea>
                <button id="translate-btn" class="btn btn-primary" style="margin-top:10px;">翻訳</button>
                <div id="translate-result" style="margin-top:20px; padding:10px; background:#f5f5f5; border-radius:5px; min-height:50px;"></div>
            </div>
        `;
    }

    getEmotionAnalysisHTML() {
        return `
            <div class="feature-emotion-analysis">
                <h2>感情分析</h2>
                <textarea id="emotion-input" class="form-control" placeholder="分析するテキストを入力" rows="4"></textarea>
                <button id="analyze-btn" class="btn btn-primary" style="margin-top:10px;">分析</button>
                <div id="emotion-result" style="margin-top:20px;"></div>
            </div>
        `;
    }

    getImageRecognitionHTML() {
        return `
            <div class="feature-image-recognition">
                <h2>画像認識</h2>
                <input type="file" id="image-upload" accept="image/*" class="form-control">
                <img id="preview-image" style="max-width:100%; margin-top:20px; display:none;">
                <div id="recognition-result" style="margin-top:20px;"></div>
            </div>
        `;
    }

    getKeywordExtractorHTML() {
        return `
            <div class="feature-keyword-extractor">
                <h2>キーワード抽出</h2>
                <textarea id="keyword-input" class="form-control" placeholder="テキストを入力" rows="4"></textarea>
                <button id="extract-btn" class="btn btn-primary" style="margin-top:10px;">抽出</button>
                <div id="keyword-result" style="margin-top:20px;">
                    <strong>キーワード:</strong> <span id="keywords"></span>
                </div>
            </div>
        `;
    }

    getAutoClassifierHTML() {
        return `
            <div class="feature-auto-classifier">
                <h2>自動分類</h2>
                <textarea id="classify-input" class="form-control" placeholder="分類するテキストを入力" rows="4"></textarea>
                <button id="classify-btn" class="btn btn-primary" style="margin-top:10px;">分類</button>
                <div id="classify-result" style="margin-top:20px;"></div>
            </div>
        `;
    }

    getImageSenderHTML() {
        return `
            <div class="feature-image-sender">
                <h2>画像送受信</h2>
                <input type="file" id="send-image" accept="image/*" class="form-control">
                <img id="send-preview" style="max-width:100%; margin-top:20px; display:none;">
            </div>
        `;
    }

    getGIFSupportHTML() {
        return `
            <div class="feature-gif-support">
                <h2>GIF画像対応</h2>
                <input type="file" id="gif-upload" accept="image/gif" class="form-control">
                <img id="gif-preview" style="max-width:100%; margin-top:20px; display:none;">
            </div>
        `;
    }

    getFileSharingHTML() {
        return `
            <div class="feature-file-sharing">
                <h2>ファイル共有</h2>
                <input type="file" id="file-upload" class="form-control">
                <div id="file-info" style="margin-top:20px;"></div>
            </div>
        `;
    }

    getAlbumCreatorHTML() {
        return `
            <div class="feature-album-creator">
                <h2>アルバム作成</h2>
                <div class="input-group" style="margin-bottom:20px;">
                    <input type="text" id="album-name" class="form-control" placeholder="アルバム名を入力">
                    <button id="create-album-btn" class="btn btn-primary">作成</button>
                </div>
                <ul id="album-list"></ul>
            </div>
        `;
    }

    getBeautifyFilterHTML() {
        return `
            <div class="feature-beautify-filter">
                <h2>美肌フィルター</h2>
                <input type="file" id="beautify-upload" accept="image/*" class="form-control">
                <img id="beautify-preview" style="max-width:100%; margin-top:20px; display:none; filter:grayscale(50%) brightness(110%);">
            </div>
        `;
    }

    getMediaAutoSaveHTML() {
        return `
            <div class="feature-media-auto-save">
                <h2>メディア自動保存</h2>
                <button id="save-media-btn" class="btn btn-primary">メディア保存シミュレーション</button>
                <ul id="saved-media-list" style="margin-top:20px;"></ul>
            </div>
        `;
    }

    getMiniGameHTML() {
        return `
            <div class="feature-mini-game">
                <h2>ミニゲーム</h2>
                <p id="game-message">ゲームを開始してください</p>
                <p>スコア: <span id="game-score">0</span></p>
                <div class="game-controls">
                    <button id="start-game-btn" class="btn btn-primary">ゲーム開始</button>
                    <button id="click-game-btn" class="btn btn-success">クリック！</button>
                </div>
            </div>
        `;
    }

    getQuizGameHTML() {
        return `
            <div class="feature-quiz-game">
                <h2>クイズ作成</h2>
                <p id="quiz-question">Reactの主な特徴は？</p>
                <input type="text" id="quiz-answer" class="form-control" placeholder="回答を入力">
                <button id="check-answer-btn" class="btn btn-primary" style="margin-top:10px;">回答確認</button>
                <div id="quiz-result" style="margin-top:20px;"></div>
            </div>
        `;
    }

    getEmojiQuizHTML() {
        return `
            <div class="feature-emoji-quiz">
                <h2>絵文字クイズ</h2>
                <p id="emoji-question" style="font-size:3em;">🍎📚</p>
                <p>ヒント: 果物と学び</p>
                <input type="text" id="emoji-answer" class="form-control" placeholder="答えを入力">
                <button id="check-emoji-btn" class="btn btn-primary" style="margin-top:10px;">回答確認</button>
                <div id="emoji-result" style="margin-top:20px;"></div>
            </div>
        `;
    }

    getNumberGuessingHTML() {
        return `
            <div class="feature-number-guessing">
                <h2>数字当てゲーム</h2>
                <p id="guess-message">1から100の数字を推理してみてください</p>
                <input type="number" id="guess-input" class="form-control" placeholder="数字を入力" min="1" max="100">
                <button id="guess-btn" class="btn btn-primary" style="margin-top:10px;">推理する</button>
                <div id="guess-attempts" style="margin-top:10px;">試行回数: <span id="attempts">0</span></div>
            </div>
        `;
    }

    getCooperativeGameHTML() {
        return `
            <div class="feature-cooperative-game">
                <h2>協力ゲーム</h2>
                <p>チームスコア: <span id="team-score">0</span></p>
                <button id="cooperate-btn" class="btn btn-primary">協力する</button>
            </div>
        `;
    }

    getProjectManagementHTML() {
        return `
            <div class="feature-project-management">
                <h2>プロジェクト管理</h2>
                <div class="input-group" style="margin-bottom:10px;">
                    <input type="text" id="project-name" class="form-control" placeholder="プロジェクト名">
                    <input type="number" id="project-progress" class="form-control" placeholder="進捗(%)" min="0" max="100">
                    <button id="add-project-btn" class="btn btn-primary">追加</button>
                </div>
                <ul id="project-list"></ul>
            </div>
        `;
    }

    getDocumentManagementHTML() {
        return `
            <div class="feature-document-management">
                <h2>文書管理</h2>
                <div style="margin-bottom:10px;">
                    <input type="text" id="doc-title" class="form-control" placeholder="文書タイトル" style="margin-bottom:10px;">
                    <textarea id="doc-content" class="form-control" placeholder="文書内容" rows="4"></textarea>
                    <button id="add-doc-btn" class="btn btn-primary" style="margin-top:10px;">文書追加</button>
                </div>
                <ul id="doc-list"></ul>
            </div>
        `;
    }

    getCalendarIntegrationHTML() {
        return `
            <div class="feature-calendar-integration">
                <h2>カレンダー統合</h2>
                <div class="input-group" style="margin-bottom:10px;">
                    <input type="text" id="event-title" class="form-control" placeholder="イベント名">
                    <input type="date" id="event-date" class="form-control">
                    <button id="add-event-btn" class="btn btn-primary">追加</button>
                </div>
                <ul id="event-list"></ul>
            </div>
        `;
    }

    getMeetingRoomHTML() {
        return `
            <div class="feature-meeting-room">
                <h2>会議室予約</h2>
                <div style="margin-bottom:10px;">
                    <input type="text" id="room-name" class="form-control" placeholder="会議室名" style="margin-bottom:10px;">
                    <input type="date" id="room-date" class="form-control" style="margin-bottom:10px;">
                    <input type="time" id="room-time" class="form-control" style="margin-bottom:10px;">
                    <button id="add-room-btn" class="btn btn-primary">予約追加</button>
                </div>
                <ul id="room-list"></ul>
            </div>
        `;
    }

    getAttendanceHTML() {
        return `
            <div class="feature-attendance">
                <h2>出勤管理</h2>
                <div style="margin-bottom:10px;">
                    <input type="text" id="employee-name" class="form-control" placeholder="従業員名" style="margin-bottom:10px;">
                    <input type="date" id="attendance-date" class="form-control" style="margin-bottom:10px;">
                    <select id="attendance-status" class="form-control" style="margin-bottom:10px;">
                        <option value="出勤">出勤</option>
                        <option value="欠勤">欠勤</option>
                        <option value="遅刻">遅刻</option>
                    </select>
                    <button id="add-attendance-btn" class="btn btn-primary">記録追加</button>
                </div>
                <ul id="attendance-list"></ul>
            </div>
        `;
    }

    getExpenseManagementHTML() {
        return `
            <div class="feature-expense-management">
                <h2>経費精算</h2>
                <div class="input-group" style="margin-bottom:10px;">
                    <input type="text" id="expense-item" class="form-control" placeholder="項目名">
                    <input type="number" id="expense-amount" class="form-control" placeholder="金額">
                    <button id="add-expense-btn" class="btn btn-primary">経費追加</button>
                </div>
                <ul id="expense-list"></ul>
            </div>
        `;
    }

    getGmailIntegrationHTML() {
        return `
            <div class="feature-gmail-integration">
                <h2>Gmail連携</h2>
                <button id="gmail-connect-btn" class="btn btn-primary">Gmailに接続</button>
                <div id="gmail-messages" style="margin-top:20px;"></div>
            </div>
        `;
    }

    getYouTubeIntegrationHTML() {
        return `
            <div class="feature-youtube-integration">
                <h2>YouTube検索</h2>
                <div class="input-group" style="margin-bottom:20px;">
                    <input type="text" id="youtube-query" class="form-control" placeholder="キーワードを入力">
                    <button id="youtube-search-btn" class="btn btn-primary">検索</button>
                </div>
                <div id="youtube-results"></div>
            </div>
        `;
    }

    getQRCodeHTML() {
        return `
            <div class="feature-qr-code">
                <h2>QRコード生成</h2>
                <div class="input-group" style="margin-bottom:20px;">
                    <input type="text" id="qr-url" class="form-control" placeholder="URLを入力" value="${window.location.href}">
                    <button id="qr-generate-btn" class="btn btn-primary">生成</button>
                </div>
                <div id="qr-canvas-holder" style="text-align:center; min-height:200px;"></div>
                <button id="qr-download-btn" class="btn btn-success" style="display:none; margin-top:10px;">ダウンロード</button>
            </div>
        `;
    }

    // 機能の初期化
    initializeFeature(featureName) {
        const initializers = {
            'audio-call': () => this.initAudioCall(),
            'group-video-call': () => this.initGroupVideoCall(),
            'group-audio-call': () => this.initGroupAudioCall(),
            'call-recording': () => this.initCallRecording(),
            'ai-chatbot': () => this.initAIChatbot(),
            'auto-translate': () => this.initAutoTranslate(),
            'emotion-analysis': () => this.initEmotionAnalysis(),
            'image-recognition': () => this.initImageRecognition(),
            'keyword-extractor': () => this.initKeywordExtractor(),
            'auto-classifier': () => this.initAutoClassifier(),
            'image-sender': () => this.initImageSender(),
            'gif-support': () => this.initGIFSupport(),
            'file-sharing': () => this.initFileSharing(),
            'album-creator': () => this.initAlbumCreator(),
            'beautify-filter': () => this.initBeautifyFilter(),
            'media-auto-save': () => this.initMediaAutoSave(),
            'mini-game': () => this.initMiniGame(),
            'quiz-game': () => this.initQuizGame(),
            'emoji-quiz': () => this.initEmojiQuiz(),
            'number-guessing': () => this.initNumberGuessing(),
            'cooperative-game': () => this.initCooperativeGame(),
            'project-management': () => this.initProjectManagement(),
            'document-management': () => this.initDocumentManagement(),
            'calendar-integration': () => this.initCalendarIntegration(),
            'meeting-room': () => this.initMeetingRoom(),
            'attendance': () => this.initAttendance(),
            'expense-management': () => this.initExpenseManagement(),
            'gmail-integration': () => this.initGmailIntegration(),
            'youtube-integration': () => this.initYouTubeIntegration(),
            'qr-code': () => this.initQRCode()
        };

        const initializer = initializers[featureName];
        if (initializer) {
            initializer();
        }
    }

    // 各機能の初期化メソッド
    initAudioCall() {
        let calling = false;
        let timer = 0;
        let interval = null;

        const startBtn = document.getElementById('start-call-btn');
        const endBtn = document.getElementById('end-call-btn');
        const status = document.getElementById('call-status');
        const timerDiv = document.getElementById('call-timer');
        const timerSpan = document.getElementById('timer');

        startBtn.addEventListener('click', () => {
            calling = true;
            status.textContent = '通話中...';
            startBtn.style.display = 'none';
            endBtn.style.display = 'inline-block';
            timerDiv.style.display = 'block';
            
            interval = setInterval(() => {
                timer++;
                const mins = Math.floor(timer / 60);
                const secs = timer % 60;
                timerSpan.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            }, 1000);
        });

        endBtn.addEventListener('click', () => {
            calling = false;
            clearInterval(interval);
            timer = 0;
            status.textContent = '通話終了';
            startBtn.style.display = 'inline-block';
            endBtn.style.display = 'none';
            timerDiv.style.display = 'none';
        });
    }

    initGroupVideoCall() {
        const startBtn = document.getElementById('start-video-btn');
        const endBtn = document.getElementById('end-video-btn');
        const localVideo = document.getElementById('local-video');

        startBtn.addEventListener('click', async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                localVideo.srcObject = stream;
                startBtn.style.display = 'none';
                endBtn.style.display = 'inline-block';
            } catch (error) {
                alert('カメラ/マイクへのアクセスが拒否されました');
            }
        });

        endBtn.addEventListener('click', () => {
            const stream = localVideo.srcObject;
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                localVideo.srcObject = null;
            }
            startBtn.style.display = 'inline-block';
            endBtn.style.display = 'none';
        });
    }

    initGroupAudioCall() {
        let calling = false;
        let timer = 0;
        let interval = null;

        const joinBtn = document.getElementById('join-group-call-btn');
        const leaveBtn = document.getElementById('leave-group-call-btn');
        const participants = document.getElementById('participants');
        const timerDiv = document.getElementById('group-timer');
        const timerVal = document.getElementById('group-timer-val');

        const dummyParticipants = ['Alice', 'Bob', 'Charlie'];

        joinBtn.addEventListener('click', () => {
            calling = true;
            participants.textContent = `参加者: ${dummyParticipants.join(', ')}`;
            joinBtn.style.display = 'none';
            leaveBtn.style.display = 'inline-block';
            timerDiv.style.display = 'block';

            interval = setInterval(() => {
                timer++;
                const mins = Math.floor(timer / 60);
                const secs = timer % 60;
                timerVal.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            }, 1000);
        });

        leaveBtn.addEventListener('click', () => {
            calling = false;
            clearInterval(interval);
            timer = 0;
            participants.textContent = '参加者: なし';
            joinBtn.style.display = 'inline-block';
            leaveBtn.style.display = 'none';
            timerDiv.style.display = 'none';
        });
    }

    initCallRecording() {
        let mediaRecorder = null;
        let chunks = [];

        const startBtn = document.getElementById('start-recording-btn');
        const stopBtn = document.getElementById('stop-recording-btn');
        const status = document.getElementById('recording-status');
        const audio = document.getElementById('recorded-audio');

        startBtn.addEventListener('click', async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                chunks = [];

                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) {
                        chunks.push(e.data);
                    }
                };

                mediaRecorder.onstop = () => {
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    const url = URL.createObjectURL(blob);
                    audio.src = url;
                    audio.style.display = 'block';
                };

                mediaRecorder.start();
                status.textContent = '録音中...';
                startBtn.style.display = 'none';
                stopBtn.style.display = 'inline-block';
            } catch (error) {
                alert('マイクへのアクセスが拒否されました');
            }
        });

        stopBtn.addEventListener('click', () => {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                status.textContent = '録音完了';
                startBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
            }
        });
    }

    initAIChatbot() {
        const messages = document.getElementById('ai-chat-messages');
        const input = document.getElementById('ai-input');
        const sendBtn = document.getElementById('ai-send-btn');

        const addMessage = (sender, message) => {
            const msgDiv = document.createElement('div');
            msgDiv.innerHTML = `<strong>${sender}:</strong> ${message}`;
            msgDiv.style.marginBottom = '10px';
            messages.appendChild(msgDiv);
            messages.scrollTop = messages.scrollHeight;
        };

        sendBtn.addEventListener('click', () => {
            const msg = input.value.trim();
            if (msg === '') return;

            addMessage('You', msg);
            input.value = '';

            // シミュレーションされたAIの返答
            setTimeout(() => {
                addMessage('AI', 'これはシミュレーションされた返答です。');
            }, 500);
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendBtn.click();
            }
        });
    }

    initAutoTranslate() {
        const input = document.getElementById('translate-input');
        const btn = document.getElementById('translate-btn');
        const result = document.getElementById('translate-result');

        btn.addEventListener('click', () => {
            const text = input.value.trim();
            if (text === '') return;

            // シンプルな変換: 文字列を反転
            const translated = text.split('').reverse().join('');
            result.innerHTML = `<strong>翻訳結果:</strong><br>${translated}`;
        });
    }

    initEmotionAnalysis() {
        const input = document.getElementById('emotion-input');
        const btn = document.getElementById('analyze-btn');
        const result = document.getElementById('emotion-result');

        btn.addEventListener('click', () => {
            const text = input.value.trim();
            if (text === '') return;

            const emotions = ['ポジティブ', 'ネガティブ', '中立'];
            const randomEmotion = emotions[Math.floor(Math.random() * emotions.length)];
            result.innerHTML = `<strong>分析結果:</strong> ${randomEmotion}`;
        });
    }

    initImageRecognition() {
        const upload = document.getElementById('image-upload');
        const preview = document.getElementById('preview-image');
        const result = document.getElementById('recognition-result');

        upload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const url = URL.createObjectURL(file);
                preview.src = url;
                preview.style.display = 'block';
                result.innerHTML = '<strong>認識結果:</strong> これはサンプルの画像認識結果です：猫の写真';
            }
        });
    }

    initKeywordExtractor() {
        const input = document.getElementById('keyword-input');
        const btn = document.getElementById('extract-btn');
        const keywords = document.getElementById('keywords');

        btn.addEventListener('click', () => {
            const text = input.value.trim();
            if (text === '') return;

            const words = text.split(' ').slice(0, 3);
            keywords.textContent = words.join(', ');
        });
    }

    initAutoClassifier() {
        const input = document.getElementById('classify-input');
        const btn = document.getElementById('classify-btn');
        const result = document.getElementById('classify-result');

        btn.addEventListener('click', () => {
            const text = input.value.trim();
            if (text === '') return;

            const category = text.includes('error') ? 'エラー' : '一般';
            result.innerHTML = `<strong>カテゴリー:</strong> ${category}`;
        });
    }

    initImageSender() {
        const upload = document.getElementById('send-image');
        const preview = document.getElementById('send-preview');

        upload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const url = URL.createObjectURL(file);
                preview.src = url;
                preview.style.display = 'block';
            }
        });
    }

    initGIFSupport() {
        const upload = document.getElementById('gif-upload');
        const preview = document.getElementById('gif-preview');

        upload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const url = URL.createObjectURL(file);
                preview.src = url;
                preview.style.display = 'block';
            }
        });
    }

    initFileSharing() {
        const upload = document.getElementById('file-upload');
        const info = document.getElementById('file-info');

        upload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                info.innerHTML = `<strong>選択されたファイル:</strong> ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
            }
        });
    }

    initAlbumCreator() {
        const nameInput = document.getElementById('album-name');
        const btn = document.getElementById('create-album-btn');
        const list = document.getElementById('album-list');

        btn.addEventListener('click', () => {
            const name = nameInput.value.trim();
            if (name === '') return;

            const li = document.createElement('li');
            li.textContent = name;
            list.appendChild(li);
            nameInput.value = '';
        });
    }

    initBeautifyFilter() {
        const upload = document.getElementById('beautify-upload');
        const preview = document.getElementById('beautify-preview');

        upload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const url = URL.createObjectURL(file);
                preview.src = url;
                preview.style.display = 'block';
            }
        });
    }

    initMediaAutoSave() {
        const btn = document.getElementById('save-media-btn');
        const list = document.getElementById('saved-media-list');
        let count = 0;

        btn.addEventListener('click', () => {
            count++;
            const li = document.createElement('li');
            li.textContent = `メディア_${count}`;
            list.appendChild(li);
        });
    }

    initMiniGame() {
        let score = 0;
        const message = document.getElementById('game-message');
        const scoreSpan = document.getElementById('game-score');
        const startBtn = document.getElementById('start-game-btn');
        const clickBtn = document.getElementById('click-game-btn');

        startBtn.addEventListener('click', () => {
            score = 0;
            scoreSpan.textContent = score;
            message.textContent = 'ゲームスタート！クリックして得点アップ';
        });

        clickBtn.addEventListener('click', () => {
            score++;
            scoreSpan.textContent = score;
        });
    }

    initQuizGame() {
        const answerInput = document.getElementById('quiz-answer');
        const btn = document.getElementById('check-answer-btn');
        const result = document.getElementById('quiz-result');

        btn.addEventListener('click', () => {
            const answer = answerInput.value.trim().toLowerCase();
            if (answer === 'コンポーネントベース' || answer === 'component-based') {
                result.textContent = '正解！';
                result.style.color = 'green';
            } else {
                result.textContent = '不正解。';
                result.style.color = 'red';
            }
        });
    }

    initEmojiQuiz() {
        const answerInput = document.getElementById('emoji-answer');
        const btn = document.getElementById('check-emoji-btn');
        const result = document.getElementById('emoji-result');

        btn.addEventListener('click', () => {
            const answer = answerInput.value.trim().toLowerCase();
            if (answer === 'apple' || answer === 'りんご') {
                result.textContent = '正解！';
                result.style.color = 'green';
            } else {
                result.textContent = '不正解。';
                result.style.color = 'red';
            }
        });
    }

    initNumberGuessing() {
        const randomNumber = Math.floor(Math.random() * 100) + 1;
        let attempts = 0;

        const input = document.getElementById('guess-input');
        const btn = document.getElementById('guess-btn');
        const message = document.getElementById('guess-message');
        const attemptsSpan = document.getElementById('attempts');

        btn.addEventListener('click', () => {
            const guess = parseInt(input.value);
            if (isNaN(guess)) return;

            attempts++;
            attemptsSpan.textContent = attempts;

            if (guess === randomNumber) {
                message.textContent = `正解！ 試行回数: ${attempts}`;
                message.style.color = 'green';
            } else if (guess < randomNumber) {
                message.textContent = 'もっと大きな数字です';
            } else {
                message.textContent = 'もっと小さな数字です';
            }

            input.value = '';
        });
    }

    initCooperativeGame() {
        let teamScore = 0;
        const scoreSpan = document.getElementById('team-score');
        const btn = document.getElementById('cooperate-btn');

        btn.addEventListener('click', () => {
            teamScore++;
            scoreSpan.textContent = teamScore;
        });
    }

    initProjectManagement() {
        const nameInput = document.getElementById('project-name');
        const progressInput = document.getElementById('project-progress');
        const btn = document.getElementById('add-project-btn');
        const list = document.getElementById('project-list');

        btn.addEventListener('click', () => {
            const name = nameInput.value.trim();
            const progress = progressInput.value;
            if (name === '' || progress === '') return;

            const li = document.createElement('li');
            li.innerHTML = `<strong>${name}</strong> - ${progress}% 完了`;
            list.appendChild(li);

            nameInput.value = '';
            progressInput.value = '';
        });
    }

    initDocumentManagement() {
        const titleInput = document.getElementById('doc-title');
        const contentInput = document.getElementById('doc-content');
        const btn = document.getElementById('add-doc-btn');
        const list = document.getElementById('doc-list');

        btn.addEventListener('click', () => {
            const title = titleInput.value.trim();
            const content = contentInput.value.trim();
            if (title === '' || content === '') return;

            const li = document.createElement('li');
            li.innerHTML = `<strong>${title}</strong>: ${content}`;
            list.appendChild(li);

            titleInput.value = '';
            contentInput.value = '';
        });
    }

    initCalendarIntegration() {
        const titleInput = document.getElementById('event-title');
        const dateInput = document.getElementById('event-date');
        const btn = document.getElementById('add-event-btn');
        const list = document.getElementById('event-list');

        btn.addEventListener('click', () => {
            const title = titleInput.value.trim();
            const date = dateInput.value;
            if (title === '' || date === '') return;

            const li = document.createElement('li');
            li.textContent = `${date}: ${title}`;
            list.appendChild(li);

            titleInput.value = '';
            dateInput.value = '';
        });
    }

    initMeetingRoom() {
        const nameInput = document.getElementById('room-name');
        const dateInput = document.getElementById('room-date');
        const timeInput = document.getElementById('room-time');
        const btn = document.getElementById('add-room-btn');
        const list = document.getElementById('room-list');

        btn.addEventListener('click', () => {
            const name = nameInput.value.trim();
            const date = dateInput.value;
            const time = timeInput.value;
            if (name === '' || date === '' || time === '') return;

            const li = document.createElement('li');
            li.textContent = `${date} ${time} - ${name}`;
            list.appendChild(li);

            nameInput.value = '';
            dateInput.value = '';
            timeInput.value = '';
        });
    }

    initAttendance() {
        const nameInput = document.getElementById('employee-name');
        const dateInput = document.getElementById('attendance-date');
        const statusSelect = document.getElementById('attendance-status');
        const btn = document.getElementById('add-attendance-btn');
        const list = document.getElementById('attendance-list');

        btn.addEventListener('click', () => {
            const name = nameInput.value.trim();
            const date = dateInput.value;
            const status = statusSelect.value;
            if (name === '' || date === '') return;

            const li = document.createElement('li');
            li.textContent = `${date} - ${name} (${status})`;
            list.appendChild(li);

            nameInput.value = '';
            dateInput.value = '';
        });
    }

    initExpenseManagement() {
        const itemInput = document.getElementById('expense-item');
        const amountInput = document.getElementById('expense-amount');
        const btn = document.getElementById('add-expense-btn');
        const list = document.getElementById('expense-list');

        btn.addEventListener('click', () => {
            const item = itemInput.value.trim();
            const amount = amountInput.value;
            if (item === '' || amount === '') return;

            const li = document.createElement('li');
            li.textContent = `${item} - ${amount}円`;
            list.appendChild(li);

            itemInput.value = '';
            amountInput.value = '';
        });
    }

    initGmailIntegration() {
        const btn = document.getElementById('gmail-connect-btn');
        const messages = document.getElementById('gmail-messages');

        btn.addEventListener('click', () => {
            messages.innerHTML = '<p>Gmail APIに接続しています...</p>';
            
            // 実際のAPI呼び出しをシミュレーション
            setTimeout(() => {
                messages.innerHTML = `
                    <div style="border:1px solid #ccc; padding:10px; margin-top:10px;">
                        <strong>件名:</strong> サンプルメール1<br>
                        <strong>送信者:</strong> example@gmail.com
                    </div>
                    <div style="border:1px solid #ccc; padding:10px; margin-top:10px;">
                        <strong>件名:</strong> サンプルメール2<br>
                        <strong>送信者:</strong> test@gmail.com
                    </div>
                `;
            }, 1000);
        });
    }

    initYouTubeIntegration() {
        const input = document.getElementById('youtube-query');
        const btn = document.getElementById('youtube-search-btn');
        const results = document.getElementById('youtube-results');

        btn.addEventListener('click', () => {
            const query = input.value.trim();
            if (query === '') return;

            results.innerHTML = '<p>検索中...</p>';

            // 実際のAPI呼び出しをシミュレーション
            setTimeout(() => {
                results.innerHTML = `
                    <div style="border:1px solid #ccc; padding:10px; margin-top:10px;">
                        <strong>サンプル動画1</strong><br>
                        チャンネル: Sample Channel
                    </div>
                    <div style="border:1px solid #ccc; padding:10px; margin-top:10px;">
                        <strong>サンプル動画2</strong><br>
                        チャンネル: Test Channel
                    </div>
                `;
            }, 1000);
        });
    }

    initQRCode() {
        const input = document.getElementById('qr-url');
        const genBtn = document.getElementById('qr-generate-btn');
        const dlBtn = document.getElementById('qr-download-btn');
        const holder = document.getElementById('qr-canvas-holder');

        // QRコードライブラリをロード（CDN経由）
        const loadQRScript = () => {
            return new Promise((resolve, reject) => {
                if (window.QRCode) {
                    resolve();
                    return;
                }
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/qrcode/build/qrcode.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        };

        genBtn.addEventListener('click', async () => {
            const url = input.value.trim();
            if (url === '') {
                alert('URLを入力してください');
                return;
            }

            try {
                await loadQRScript();
                holder.innerHTML = '';
                const canvas = document.createElement('canvas');
                holder.appendChild(canvas);

                QRCode.toCanvas(canvas, url, { width: 200, errorCorrectionLevel: 'H' }, (error) => {
                    if (error) {
                        holder.innerHTML = 'QRコードの生成に失敗しました。';
                    } else {
                        dlBtn.style.display = 'inline-block';
                    }
                });
            } catch (error) {
                holder.innerHTML = 'QRコードライブラリの読み込みに失敗しました。';
            }
        });

        dlBtn.addEventListener('click', () => {
            const canvas = holder.querySelector('canvas');
            if (!canvas) {
                alert('先にQRコードを生成してください');
                return;
            }

            const a = document.createElement('a');
            a.href = canvas.toDataURL('image/png');
            a.download = 'qrcode.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });
    }
}

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    new FeatureManager();
});
