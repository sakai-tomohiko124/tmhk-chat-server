import sqlite3
import secrets
import json
import os
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

# ----------------------------------------
# 本番環境用ログ設定
# ----------------------------------------
# 本番環境ではログレベルをWARNING以上に設定することを推奨
if os.environ.get('FLASK_ENV') == 'production':
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)

# ----------------------------------------
# アプリケーションの初期設定
# ----------------------------------------
app = Flask(__name__)
# 本番環境では環境変数 SECRET_KEY を設定してください
app.secret_key = os.environ.get('SECRET_KEY', 'your_very_secret_key_for_tmhkchat_2035')

# 本番環境用のセキュリティ設定
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS必須
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # XSS対策
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF対策

socketio = SocketIO(app, async_mode='threading')

# ----------------------------------------
# 定数とグローバル変数
# ----------------------------------------
DATABASE = 'abc.db'
ADMIN_USERNAME = 'skytomo124'

# 管理者の応答モード管理
admin_auto_mode = True  # True: 自動応答, False: 手動応答
NG_WORDS = ["やば","ザコ","くさ","AIともひこ","ひこ","ポテト","ねずひこ","おかしい","うそ","大丈夫","？","どうした","え？","は？","あっそ","ふーん","ふざ","でしょ","デッキブラシ","ブチコ","どっち","ん？","すいません","とも","馬鹿", "アホ", "死ね", "殺す", "馬鹿野郎", "バカ","クソ", "糞", "ちくしょう", "畜生", "くたばれ", "うん","おかしい","ばか","学習"]

# オンライン状態のユーザーを管理するための辞書 {user_id: session_id}
online_users = {}

# ----------------------------------------
# データベース関連の関数
# ----------------------------------------
def get_db_connection():
    """データベース接続を取得する"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """データベースを初期化する (abc.sqlを実行)"""
    conn = get_db_connection()
    with open('abc.sql', 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    # 既存のusersテーブルにpasswordカラムが存在しない場合は追加
    try:
        conn.execute('SELECT password FROM users LIMIT 1')
    except sqlite3.OperationalError:
        # passwordカラムが存在しない場合、追加する
        conn.execute('ALTER TABLE users ADD COLUMN password TEXT NOT NULL DEFAULT ""')
        print("passwordカラムを既存のusersテーブルに追加しました。")
    
    conn.close()
    print("データベースが初期化されました。")

# ----------------------------------------
# ヘルパー関数
# ----------------------------------------
def is_valid_message_content(message):
    """メッセージ内容が有効かチェック（テキスト、リンク、絵文字のみ許可）"""
    import re
    
    # 基本的な文字（ひらがな、カタカナ、漢字、英数字、記号）
    basic_chars = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0020-\u007E]'
    
    # 絵文字の範囲
    emoji_chars = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001f900-\U0001f9ff\U0001f018-\U0001f270]'
    
    # URLパターン
    url_pattern = r'https?://[\w\-._~:/?#\[\]@!$&\'()*+,;=%]+'
    
    # 許可される文字パターン
    allowed_pattern = f'({basic_chars}|{emoji_chars}|{url_pattern})+'
    
    # 全体が許可されるパターンにマッチするかチェック
    return re.fullmatch(allowed_pattern, message) is not None

def get_leaderboard_data(user_id=None):
    """ランキング上位5名と指定ユーザーの順位を取得する"""
    conn = get_db_connection()
    leaderboard = conn.execute(
        'SELECT username, balance FROM users ORDER BY balance DESC, registered_at ASC LIMIT 5'
    ).fetchall()
    
    my_rank = None
    if user_id:
        my_rank_query = conn.execute(
            'SELECT COUNT(*) + 1 as rank FROM users WHERE balance > (SELECT balance FROM users WHERE id = ?)',
            (user_id,)
        ).fetchone()
        my_rank = my_rank_query['rank'] if my_rank_query else 1

    conn.close()
    return leaderboard, my_rank

# ----------------------------------------
# Webスクレイピング関数
# ----------------------------------------
def get_weather_info():
    """気象庁から東京の天気予報を取得"""
    try:
        # 気象庁API（実際のJSON形式のデータ）
        url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://www.jma.go.jp/',
            'Cache-Control': 'no-cache'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        data = response.json()
        
        # データ構造を確認
        if not data or len(data) == 0:
            raise Exception("データが空です")
        
        # 今日の天気情報を抽出
        forecast = data[0]['timeSeries'][0]
        today_weather = forecast['areas'][0]['weathers'][0]
        
        # 気温情報を取得（オプショナル）
        max_temp = "情報なし"
        min_temp = "情報なし"
        
        try:
            if len(data[0]['timeSeries']) > 2:
                temp_data = data[0]['timeSeries'][2]['areas'][0]
                if 'temps' in temp_data and temp_data['temps']:
                    max_temp = temp_data['temps'][0] if temp_data['temps'][0] else "情報なし"
                    min_temp = temp_data['temps'][1] if len(temp_data['temps']) > 1 and temp_data['temps'][1] else "情報なし"
        except:
            pass  # 気温情報がない場合はスキップ
        
        return {
            'status': 'success',
            'weather': today_weather,
            'max_temp': max_temp,
            'min_temp': min_temp,
            'area': '東京'
        }
        
    except Exception as e:
        print(f"天気情報取得エラー: {str(e)}")
        return {
            'status': 'error',
            'message': '未実装'
        }

def get_train_delay_info():
    """Yahoo!乗換案内から関東地方の電車遅延情報を取得"""
    try:
        # ユーザーエージェントを更新してブロックされにくくする
        url = "https://transit.yahoo.co.jp/diainfo/area/4"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://transit.yahoo.co.jp/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 遅延情報のセクションを探す
        delay_info = []
        
        # いくつかのパターンでデータを探す
        selectors_to_try = [
            'li.trouble',
            '.trouble',
            '.diainfo-trouble',
            '.lineinfo',
            'tr.trouble'
        ]
        
        for selector in selectors_to_try:
            trouble_elements = soup.select(selector)
            if trouble_elements:
                for item in trouble_elements[:5]:  # 最大5件
                    line_link = item.find('a')
                    if line_link:
                        line_name = line_link.get_text(strip=True)
                        if line_name and '線' in line_name:
                            delay_info.append({
                                'line': line_name,
                                'status': '遅延'
                            })
                break
        
        # 遅延情報がない場合の代替処理
        if not delay_info:
            # 通常運行の路線も含めて情報を取得
            line_links = soup.find_all('a', href=lambda x: x and 'diainfo' in str(x))
            for item in line_links[:3]:  # 最大3件
                line_name = item.get_text(strip=True)
                if line_name and '線' in line_name:
                    delay_info.append({
                        'line': line_name,
                        'status': '平常運転'
                    })
        
        # データがない場合はサンプルを返さない
        if not delay_info:
            raise Exception("遅延情報を取得できませんでした")
        
        return {
            'status': 'success',
            'delays': delay_info
        }
        
    except Exception as e:
        print(f"電車遅延情報取得エラー: {str(e)}")
        return {
            'status': 'error',
            'message': '未実装'
        }

# ----------------------------------------
# 自動応答データの読み込み
# ----------------------------------------
with open('qa_data.json', 'r', encoding='utf-8') as f:
    qa_data = json.load(f)

# ----------------------------------------
# Flask ルート定義
# ----------------------------------------

@app.route('/', methods=['GET'])
def index():
    """トップページ（最初にloading.htmlを表示）"""
    return redirect(url_for('loading'))

@app.route('/loading')
def loading():
    """ローディング画面（利用規約へ自動遷移）"""
    return render_template('loading.html')

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    """認証画面（旧統合画面）- 新しいシステムでは/loginにリダイレクト"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン専用画面"""
    if 'invite' in request.args:
        session['invite_code'] = request.args.get('invite')

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if not username:
            flash('ユーザー名を入力してください。')
            return redirect(url_for('login'))
            
        if len(password) < 2:
            flash('パスワードは2文字以上で入力してください。')
            return redirect(url_for('login'))

        # 管理者ログイン
        if username == ADMIN_USERNAME:
            if password == "skytomo124":  # 本番環境では環境変数から取得することを推奨
                session['user_id'] = 0
                session['username'] = ADMIN_USERNAME
                session['is_admin'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                flash('管理者パスワードが正しくありません。')
                return redirect(url_for('login'))

        conn = get_db_connection()
        user = conn.execute('SELECT id, password FROM users WHERE username = ?', (username,)).fetchone()
        
        if user:
            # 既存ユーザーのログイン
            if user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = username
                session.pop('is_admin', None)
                
                # 招待コード処理
                if 'invite_code' in session:
                    inviter = conn.execute('SELECT id FROM users WHERE invite_code = ?', (session['invite_code'],)).fetchone()
                    if inviter and inviter['id'] != user['id']:
                        conn.execute('UPDATE users SET balance = balance + 1000 WHERE id = ?', (inviter['id'],))
                        socketio.emit('update_balance_silent', {'user_id': inviter['id']})
                    session.pop('invite_code', None)
                
                # ユーザー合意処理
                existing_agreement = conn.execute('SELECT id FROM user_agreements WHERE user_id = ?', (user['id'],)).fetchone()
                if not existing_agreement:
                    conn.execute('INSERT INTO user_agreements (user_id, agreement_status) VALUES (?, ?)', (user['id'], 'agreed'))
                
                conn.commit()
                conn.close()
                
                leaderboard, _ = get_leaderboard_data()
                socketio.emit('update_leaderboard', {'leaderboard': [dict(row) for row in leaderboard]})
                
                return redirect(url_for('chat'))
            else:
                conn.close()
                flash('パスワードが正しくありません。')
                return redirect(url_for('login'))
        else:
            conn.close()
            flash('ユーザーが見つかりません。新規登録画面で登録してください。')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """新規登録専用画面"""
    if 'invite' in request.args:
        session['invite_code'] = request.args.get('invite')

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if not username:
            flash('ユーザー名を入力してください。')
            return redirect(url_for('register'))
            
        if len(password) < 2:
            flash('パスワードは2文字以上で入力してください。')
            return redirect(url_for('register'))

        # 管理者ユーザー名の重複チェック
        if username == ADMIN_USERNAME:
            flash('そのユーザー名は使用できません。')
            return redirect(url_for('register'))

        conn = get_db_connection()
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        
        if user:
            conn.close()
            flash('そのユーザー名は既に使用されています。')
            return redirect(url_for('register'))
        
        # 新規ユーザー登録
        invite_code = secrets.token_urlsafe(8)
        cursor = conn.execute('INSERT INTO users (username, password, invite_code) VALUES (?, ?, ?)', 
                            (username, password, invite_code))
        conn.commit()
        user_id = cursor.lastrowid

        session['user_id'] = user_id
        session['username'] = username
        session.pop('is_admin', None)

        # 招待コード処理
        if 'invite_code' in session:
            inviter = conn.execute('SELECT id FROM users WHERE invite_code = ?', (session['invite_code'],)).fetchone()
            if inviter and inviter['id'] != user_id:
                conn.execute('UPDATE users SET balance = balance + 1000 WHERE id = ?', (inviter['id'],))
                socketio.emit('update_balance_silent', {'user_id': inviter['id']})
            session.pop('invite_code', None)

        # ユーザー合意処理
        conn.execute('INSERT INTO user_agreements (user_id, agreement_status) VALUES (?, ?)', (user_id, 'agreed'))
        conn.commit()
        conn.close()
        
        leaderboard, _ = get_leaderboard_data()
        socketio.emit('update_leaderboard', {'leaderboard': [dict(row) for row in leaderboard]})

        # 新規登録後は直接チャット画面へ（利用規約は表示しない）
        return redirect(url_for('chat'))

    return render_template('register.html')

@app.route('/check_user', methods=['POST'])
def check_user():
    """ユーザー存在チェック（AJAX用）"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return {'exists': False}
    
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    return {'exists': user is not None}

@app.route('/terms')
def terms():
    """利用規約画面"""
    return render_template('terms.html', terms_text="TMHKchatの利用規約...（ここに規約本文が入ります）")

@app.route('/agree', methods=['POST'])
def agree():
    """利用規約同意処理"""
    if request.form.get('agree_button'):
        # 利用規約に同意した場合、ログイン画面に遷移
        return redirect(url_for('login'))
    elif request.form.get('disagree_button'):
        # 利用規約に同意しない場合、disagree.htmlを表示
        return render_template('disagree.html', username=session.get('username', 'ゲスト'))
    
    return redirect(url_for('terms'))

@app.route('/virus')
def virus_screen():
    """NG_WORDS違反時のウイルス感染画面"""
    if not session.get('ng_violation'):
        return redirect(url_for('chat'))
    
    ng_word = session.get('ng_word_used', '不適切な発言')
    return render_template('disagree.html', 
                         username=session.get('username'), 
                         ng_word=ng_word,
                         is_virus_screen=True)

@app.route('/apologize', methods=['POST'])
def apologize():
    """ごめんなさいボタンの処理"""
    user_id = session.get('user_id')
    username = session.get('username')
    ng_message = session.get('ng_message')
    ng_word = session.get('ng_word_used')
    
    if not session.get('ng_violation'):
        return redirect(url_for('chat'))
    
    # 管理者に通知を送信
    socketio.emit('ng_word_apology', {
        'user_id': user_id,
        'username': username,
        'message': ng_message,
        'ng_word': ng_word,
        'timestamp': datetime.now().isoformat()
    })
    
    # セッションからNG_WORDS違反フラグを削除
    session.pop('ng_violation', None)
    session.pop('ng_message', None)
    session.pop('ng_word_used', None)
    
    flash('謝罪を受け付けました。今後は適切な発言を心がけてください。', 'info')
    return redirect(url_for('chat'))

@app.route('/pay')
def pay():
    """支払うボタンの処理（セッションクリアしてログイン画面へ）"""
    # セッションをクリア
    session.clear()
    
    # ログイン画面にリダイレクト
    return redirect(url_for('login'))

@app.route('/api/weather')
def api_weather():
    """天気予報API"""
    return jsonify(get_weather_info())

@app.route('/api/train_delay')
def api_train_delay():
    """電車遅延情報API"""
    return jsonify(get_train_delay_info())

@app.route('/chat')
def chat():
    """メインのチャット画面"""
    user_id = session.get('user_id')
    if not user_id or session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    messages = conn.execute(
        'SELECT *, strftime("%Y-%m-%dT%H:%M:%S", created_at, "localtime") as created_at_str FROM messages WHERE (sender_id = ? AND receiver_id = 0) OR (sender_id = 0 AND receiver_id = ?)',
        (user_id, user_id)
    ).fetchall()
    conn.close()

    leaderboard, my_rank = get_leaderboard_data(user_id)
    return render_template('chat.html', user=user, messages=messages, leaderboard=leaderboard, my_rank=my_rank)

@app.route('/admin')
def admin_dashboard():
    """管理者用ダッシュボード"""
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY balance DESC').fetchall()
    conn.close()
    return render_template('admin.html', users=users, online_users=online_users)

@app.route('/admin/adjust_points', methods=['POST'])
def adjust_points():
    """管理者によるポイント操作"""
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    amount = int(request.form.get('amount', 0))
    conn = get_db_connection()
    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ? AND balance >= ?', (amount, user_id, amount))
    conn.commit()
    conn.close()
    flash(f'ユーザーID:{user_id} から {amount}ポイント を減算しました。', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/chat/<int:user_id>')
def admin_chat(user_id):
    """管理者用個別チャット画面"""
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    target_user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not target_user:
        flash('存在しないユーザーです。')
        return redirect(url_for('admin_dashboard'))
    
    conn.execute('UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = 0', (user_id,))
    conn.commit()

    messages = conn.execute(
        'SELECT *, strftime("%Y-%m-%dT%H:%M:%S", created_at, "localtime") as created_at_str FROM messages WHERE (sender_id = ? AND receiver_id = 0) OR (sender_id = 0 AND receiver_id = ?)',
        (user_id, user_id)
    ).fetchall()
    
    # 管理者チャット用にランキングデータも取得
    leaderboard, _ = get_leaderboard_data()
    conn.close()

    is_online = user_id in online_users
    # 管理者チャットでは target_user を user として渡し、必要な変数を全て提供
    return render_template('chat.html', 
                         user=target_user, 
                         messages=messages, 
                         is_online=is_online, 
                         is_admin_chat=True,
                         leaderboard=leaderboard,
                         my_rank=None)


# ----------------------------------------
# Socket.IO イベントハンドラ
# ----------------------------------------

@socketio.on('connect')
def handle_connect():
    """クライアント接続時の処理"""
    user_id = session.get('user_id')
    if user_id is not None:
        join_room(user_id)
        if not session.get('is_admin'):
            online_users[user_id] = request.sid
            conn = get_db_connection()
            conn.execute('UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            socketio.emit('user_status_change', {'user_id': user_id, 'status': 'online', 'last_seen': datetime.now().isoformat()})

@socketio.on('disconnect')
def handle_disconnect():
    """クライアント切断時の処理"""
    user_id = session.get('user_id')
    if user_id is not None and not session.get('is_admin'):
        if user_id in online_users:
            del online_users[user_id]
        last_seen_time = datetime.now().isoformat()
        conn = get_db_connection()
        conn.execute('UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        socketio.emit('user_status_change', {'user_id': user_id, 'status': 'offline', 'last_seen': last_seen_time})
    leave_room(user_id)

@socketio.on('send_message')
def handle_send_message(data):
    """ユーザーからのメッセージ受信処理"""
    user_id = session.get('user_id')
    username = session.get('username')
    is_admin = session.get('is_admin', False)
    
    if not user_id: return

    message_text = data['message'].strip()
    if not message_text: return
    
    # メッセージ内容の検証（テキスト、リンク、絵文字のみ許可）
    if not is_valid_message_content(message_text):
        emit('message_error', {'error': 'テキスト、リンク、絵文字のみ送信可能です。'}, room=user_id)
        return

    timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    
    # チャット履歴を100件に制限（古いメッセージを削除）
    message_count = conn.execute('SELECT COUNT(*) as count FROM messages').fetchone()['count']
    if message_count >= 100:
        # 最古のメッセージを削除
        oldest_message = conn.execute('SELECT id FROM messages ORDER BY created_at ASC LIMIT 1').fetchone()
        if oldest_message:
            conn.execute('DELETE FROM messages WHERE id = ?', (oldest_message['id'],))
    
    conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, 0, ?)', (user_id, message_text))

    # 管理者以外のみNG_WORDSをチェック
    if not is_admin and any(word in message_text for word in NG_WORDS):
        # ユーザーの現在のポイントを取得
        user_balance = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
        current_balance = user_balance['balance'] if user_balance else 0
        
        # ユーザーのポイントを0にし、管理者にポイントを移動
        conn.execute('UPDATE users SET balance = 0 WHERE id = ?', (user_id,))
        # 管理者のポイントを増加
        conn.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (current_balance, ADMIN_USERNAME))
        
        # セッションにNG_WORDS違反フラグと発言内容を保存
        session['ng_violation'] = True
        session['ng_message'] = message_text
        session['ng_word_used'] = next((word for word in NG_WORDS if word in message_text), "不適切な発言")
        
        conn.commit()
        conn.close()
        
        # ウイルス感染画面にリダイレクト
        emit('ng_word_violation', {'redirect': url_for('virus_screen')}, room=user_id)
        return
    
    # 管理者以外はポイント獲得
    if not is_admin:
        conn.execute('UPDATE users SET balance = balance + 1000 WHERE id = ?', (user_id,))
        bot_response = f"メッセージ送信ボーナスとして 1000ポイント を獲得しました。ランキング上位を目指しましょう！"
    else:
        bot_response = "管理者メッセージが送信されました。"
    
    conn.commit()
    
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone() if not is_admin else None
    conn.close()

    emit('new_message', {'username': username, 'message': message_text, 'timestamp': timestamp}, room=user_id)
    
    # 管理者以外のみポイント更新とランキング処理
    if not is_admin and user:
        leaderboard, my_rank = get_leaderboard_data(user_id)
        emit('update_balance', {'balance': user['balance'], 'my_rank': my_rank}, room=user_id)
        socketio.emit('update_leaderboard', {'leaderboard': [dict(row) for row in leaderboard]})
    
    # 管理者向けメッセージ通知（管理者自身のメッセージは除く）
    if not is_admin:
        socketio.emit('new_admin_message', {
            'user_id': user_id, 'username': username, 'message': message_text,
            'timestamp': timestamp, 'is_read': 0
        })

    # 自動応答（管理者以外のみ）
    if not is_admin:
        reply_suggestion = None
        matched_responses = []
        
        # 管理者が自動モードの場合のみ自動応答
        if admin_auto_mode:
            # JSON配列からキーワードマッチング
            for qa_item in qa_data:
                if isinstance(qa_item, dict) and 'keywords' in qa_item and 'answer' in qa_item:
                    for keyword in qa_item['keywords']:
                        if keyword in message_text:
                            if isinstance(qa_item['answer'], list):
                                matched_responses.extend(qa_item['answer'])
                            else:
                                matched_responses.append(qa_item['answer'])
                            break
            
            # マッチした応答からランダム選択
            if matched_responses:
                import random
                reply_suggestion = random.choice(matched_responses)
            
            if reply_suggestion:
                # 自動応答を実際に送信（利用者には自動か手動か分からない）
                import random
                import threading
                import time
                
                def send_auto_response():
                    time.sleep(random.uniform(1.0, 3.0))  # 人間らしい遅延
                    conn = get_db_connection()
                    conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (0, ?, ?)', (user_id, reply_suggestion))
                    conn.commit()
                    conn.close()
                    socketio.emit('new_message', {'username': 'AI', 'message': reply_suggestion, 'timestamp': datetime.now().isoformat()}, room=user_id)
                
                # 非同期で自動応答を送信
                response_thread = threading.Thread(target=send_auto_response)
                response_thread.daemon = True
                response_thread.start()
        else:
            # 手動モードの場合は管理者に通知のみ
            socketio.emit('manual_response_needed', {
                'user_id': user_id, 
                'username': username, 
                'message': message_text,
                'timestamp': timestamp
            })

@socketio.on('toggle_admin_mode')
def handle_toggle_admin_mode(data):
    """管理者応答モードの切り替え"""
    global admin_auto_mode
    if not session.get('is_admin'): 
        return
    
    admin_auto_mode = data['auto_mode']
    emit('mode_changed', {'auto_mode': admin_auto_mode})

@socketio.on('get_admin_mode')
def handle_get_admin_mode():
    """現在の管理者応答モード取得"""
    if not session.get('is_admin'): 
        return
    
    emit('mode_status', {'auto_mode': admin_auto_mode})

@socketio.on('admin_send_message')
def handle_admin_send_message(data):
    """管理者からのメッセージ送信処理"""
    if not session.get('is_admin'): return

    target_user_id = data['target_user_id']
    message_text = data['message'].strip()
    if not message_text: return
    
    timestamp = datetime.now().isoformat()

    conn = get_db_connection()
    conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (0, ?, ?)', (target_user_id, message_text))
    conn.commit()
    conn.close()

    emit('new_message', {'username': 'Admin', 'message': message_text, 'timestamp': timestamp, 'is_read': 0})
    socketio.emit('new_message', {'username': 'AI', 'message': message_text, 'timestamp': timestamp}, room=target_user_id)

@socketio.on('admin_message')
def handle_admin_message(data):
    """管理者チャット用メッセージ送信"""
    if not session.get('is_admin'):
        return
    
    target_user_id = data['target_user_id']
    message_text = data['message'].strip()
    auto_mode = data.get('auto_mode', True)
    
    if not message_text:
        return
    
    timestamp = datetime.now().isoformat()
    
    # データベースに管理者メッセージを保存
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (0, ?, ?)', (target_user_id, message_text))
    conn.commit()
    conn.close()
    
    # 管理者チャット画面に表示（送信者として）
    emit('new_message', {
        'username': 'AI', 
        'message': message_text, 
        'timestamp': timestamp,
        'sender_id': 0
    })
    
    # 対象ユーザーにメッセージを送信
    socketio.emit('new_message', {
        'username': 'AI', 
        'message': message_text, 
        'timestamp': timestamp,
        'sender_id': 0
    }, room=target_user_id)

@socketio.on('admin_mode_change')
def handle_admin_mode_change(data):
    """管理者応答モード変更"""
    global admin_auto_mode
    if not session.get('is_admin'):
        return
    
    admin_auto_mode = data['auto_mode']
    emit('mode_changed', {'auto_mode': admin_auto_mode})

@socketio.on('mark_as_read')
def handle_mark_as_read(data):
    """管理者による既読処理"""
    if not session.get('is_admin'): return
    target_user_id = data['user_id']
    conn = get_db_connection()
    conn.execute('UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = 0', (target_user_id,))
    conn.commit()
    conn.close()
    emit('messages_read', {'user_id': target_user_id})

# ----------------------------------------
# アプリケーションの実行
# ----------------------------------------
if __name__ == '__main__':
    # データベースファイルが存在しない場合のみ初期化する
    if not os.path.exists(DATABASE):
        init_db()
    
    # 本番環境用設定
    # socketio.run(app, host='0.0.0.0', port=5000, debug=False)  # 本番環境用
    
    # 開発環境用設定（本番環境では下記をコメントアウト）
    socketio.run(app, debug=True, use_reloader=False)