import secrets
import json
import os
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from db import get_db_connection, init_db, get_leaderboard_data
from helpers import is_valid_message_content
from scraping import get_weather_info, get_train_delay_info

# ----------------------------------------
# 本番環境用ログ設定
# ----------------------------------------
os.environ['FLASK_ENV'] = 'production'  # 強制的に本番環境へ
logging.basicConfig(level=logging.WARNING)

# ----------------------------------------
# アプリケーションの初期設定
# ----------------------------------------

app = Flask(__name__)
# 本番用の強力なSECRET_KEY（環境変数優先、なければ固定値）
app.secret_key = os.environ.get('SECRET_KEY', 'skytomohiko124')
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS必須
app.config['SESSION_COOKIE_HTTPONLY'] = True  # XSS対策
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF対策

socketio = SocketIO(app, async_mode='threading')
online_users = {}
from config import DATABASE, ADMIN_USERNAME, NG_WORDS
from scraping import get_weather_info, get_train_delay_info


# ----------------------------------------
# 自動応答データの読み込み
# ----------------------------------------
with open('qa_data.json', 'r', encoding='utf-8') as f:
    qa_data = json.load(f)

# ----------------------------------------
# Flask ルート定義

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン画面（GET:表示, POST:認証）"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'error')
            return render_template('login.html')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            # 厳密な管理者判定（DBのusernameとADMIN_USERNAMEを比較）
            session['is_admin'] = str(user['username']).strip().lower() == str(ADMIN_USERNAME).strip().lower()
            flash('ログイン成功！', 'success')
            if session['is_admin']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('check_login_status'))
        else:
            flash('ユーザー名またはパスワードが間違っています。', 'error')
            return render_template('login.html')
    # GET: 画面表示
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """新規登録画面（GET:表示, POST:登録処理）"""
    # 利用規約未同意ならtermsへリダイレクト
    if not session.get('terms_agreed'):
        # 利用規約画面へ。inviteパラメータを保持
        invite_code = request.args.get('invite', '')
        return redirect(url_for('terms', invite=invite_code))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'error')
            return render_template('register.html')
        conn = get_db_connection()
        exists = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if exists:
            conn.close()
            flash('このユーザー名は既に登録されています。', 'error')
            return render_template('register.html')
        import random, string
        invite_code = request.args.get('invite', '')
        if not invite_code:
            invite_code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        exists_code = conn.execute('SELECT id FROM users WHERE invite_code = ?', (invite_code,)).fetchone()
        if exists_code:
            conn.close()
            flash('この招待コードは既に使用されています。', 'error')
            return render_template('register.html')
        else:
            conn.execute('INSERT INTO users (username, password, balance, invite_code) VALUES (?, ?, ?, ?)', (username, password, 200000, invite_code))
            # 招待コードが有効なら、招待元ユーザーに1万円加算
            inviter = conn.execute('SELECT id FROM users WHERE invite_code = ?', (request.args.get('invite', ''),)).fetchone()
            if inviter:
                conn.execute('UPDATE users SET balance = balance + 10000 WHERE id = ?', (inviter['id'],))
            conn.commit()
            conn.close()
            flash('登録が完了しました。ログインしてください。', 'success')
            return redirect(url_for('login'))
    # GET: 画面表示
    return render_template('register.html')

@app.route('/loading')
def loading():
    """ローディング画面（利用規約同意後の遷移用）"""
    next_url = request.args.get('next', url_for('login'))
    # ローディング画面を表示し、数秒後にnext_urlへ遷移（JSで自動遷移）
    return render_template('loading.html', next_url=next_url)
# ----------------------------------------

@app.route('/', methods=['GET'])
def index():
    """トップページ（初回は利用規約、2回目はloading→ログイン、3回目以降はloading→chatまたはログイン）"""
    if not session.get('terms_agreed'):
        return redirect(url_for('terms'))
    if not session.get('terms_shown'):
        session['terms_shown'] = 1
        return redirect(url_for('loading', next=url_for('login')))
    elif session['terms_shown'] == 1:
        session['terms_shown'] = 2
        return redirect(url_for('loading', next=url_for('login')))
    else:
        session['terms_shown'] += 1
        if 'user_id' in session:
            return redirect(url_for('loading', next=url_for('chat')))
        else:
            return redirect(url_for('login'))

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

@app.route('/logout')
def logout():
    """ログアウト機能"""
    user_id = session.get('user_id')
    
    # オンライン状態をクリア
    if user_id and user_id in online_users:
        del online_users[user_id]

        socketio.emit('user_status_change', {'user_id': user_id, 'status': 'offline'})
    
    # セッションをクリア
    session.clear()
    flash('ログアウトしました。')
    return redirect(url_for('check_login_status'))

@app.route('/check_login_status')
def check_login_status():
    """ログイン状態をチェックして適切な画面に遷移"""
    # ログイン済みの場合
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('chat'))
    else:
        # 未ログインの場合はログイン画面へ
        return redirect(url_for('login'))

@app.route('/admin/keep_memo', methods=['GET', 'POST'], endpoint='keep_memo')
def keep_memo():
    """
    管理者用Keepメモ画面（ユーザーが1人もいない場合のみ表示）
    POSTでメモ保存、GETで表示
    """
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    memo_content = ''
    saved = False
    if request.method == 'POST':
        memo_content = request.form.get('memo', '').strip()
        if memo_content:
            # 既存メモがあればUPDATE、なければINSERT
            exists = conn.execute('SELECT id FROM admin_memo LIMIT 1').fetchone()
            if exists:
                conn.execute('UPDATE admin_memo SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (memo_content, exists['id']))
            else:
                conn.execute('INSERT INTO admin_memo (content) VALUES (?)', (memo_content,))
            conn.commit()
            saved = True
    # 最新メモ取得
    memo_row = conn.execute('SELECT content FROM admin_memo ORDER BY updated_at DESC LIMIT 1').fetchone()
    if memo_row:
        memo_content = memo_row['content']
    conn.close()
    # 招待リンクのURL例: /register?invite=xxxx
    import secrets
    from datetime import datetime, timedelta
    conn2 = get_db_connection()
    now = datetime.now()
    invite = conn2.execute('SELECT * FROM invites WHERE expires_at > ? AND used = 0 ORDER BY created_at DESC LIMIT 1', (now,)).fetchone()
    if not invite:
        code = secrets.token_urlsafe(12)
        created_at = now
        expires_at = now + timedelta(hours=124)
        conn2.execute('INSERT INTO invites (code, created_at, expires_at) VALUES (?, ?, ?)', (code, created_at, expires_at))
        conn2.commit()
        invite = conn2.execute('SELECT * FROM invites WHERE code = ?', (code,)).fetchone()
    conn2.close()
    invite_url = url_for('register', invite=invite['code'], _external=True)
    expires_at_str = invite['expires_at']
    return render_template('keep_memo.html', invite_url=invite_url, expires_at=expires_at_str, memo_content=memo_content, saved=saved)
@app.route('/terms')
def terms():
    """利用規約画面"""
    invite_code = request.args.get('invite', '')
    # すでに同意済みならloading画面へ
    if session.get('terms_agreed'):
        return redirect(url_for('loading', next=url_for('register', invite=invite_code)))
    return render_template('terms.html', terms_text="TMHKchatの利用規約...（ここに規約本文が入ります）", invite=invite_code)

@app.route('/agree', methods=['POST'])
def agree():
    """利用規約同意処理"""
    invite_code = request.args.get('invite', '')
    if request.form.get('agree_button'):
        session['terms_agreed'] = True
        # 同意後はloading画面へ
        return redirect(url_for('loading', next=url_for('register', invite=invite_code)))
    return redirect(url_for('terms', invite=invite_code))

@app.route('/virus')
def virus_screen():
    """NG_WORDS違反時のウイルス感染画面"""
    if not session.get('ng_violation'):
        return redirect(url_for('chat'))

    ng_word = session.get('ng_word_used', '不適切な発言')
    user_id = session.get('user_id')
    # ウイルス画面遷移を記録
    if user_id:
        conn = get_db_connection()
        conn.execute('INSERT INTO virus_log (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()
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
    if not user_id:
        return redirect(url_for('check_login_status'))
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    # ユーザーが存在しない場合はセッションをクリア
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # 削除されていないメッセージのみを取得し、編集・既読状態も含める
    messages = conn.execute('''
        SELECT *, 
               strftime("%Y-%m-%dT%H:%M:%S", created_at, "localtime") as created_at_str,
               CASE 
                   WHEN sender_id = 0 THEN CASE WHEN user_read_at IS NOT NULL THEN 1 ELSE 0 END
                   ELSE CASE WHEN admin_read_at IS NOT NULL THEN 1 ELSE 0 END
               END as read_status
        FROM messages 
        WHERE ((sender_id = ? AND receiver_id = 0) OR (sender_id = 0 AND receiver_id = ?))
          AND is_deleted = 0
        ORDER BY created_at ASC
    ''', (user_id, user_id)).fetchall()
    
    # ユーザーが管理者からのメッセージを見た場合、自動で既読にする
    from datetime import datetime
    current_time = datetime.now().isoformat()
    conn.execute('''
        UPDATE messages 
        SET user_read_at = ? 
        WHERE sender_id = 0 AND receiver_id = ? AND user_read_at IS NULL AND is_deleted = 0
    ''', (current_time, user_id))
    conn.commit()
    conn.close()

    leaderboard, my_rank = get_leaderboard_data(user_id)
    
    # チュートリアル表示フラグを確認
    show_tutorial = session.pop('show_tutorial', False)
    
    from config import ADMIN_USERNAME
    return render_template('chat.html', user=user, messages=messages, leaderboard=leaderboard, my_rank=my_rank, show_tutorial=show_tutorial, ADMIN_USERNAME=ADMIN_USERNAME)


@app.route('/debug_session')
def debug_session():
    """セッション情報をデバッグするエンドポイント"""
    return {
        'session': dict(session),
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'is_admin': session.get('is_admin'),
        'online_users': list(online_users.keys())
    }

@app.route('/admin')
def admin_dashboard():
    """管理者用ダッシュボード"""
    if not session.get('is_admin'):
        return redirect(url_for('check_login_status'))
    conn = get_db_connection()
    from config import ADMIN_USERNAME
    users = conn.execute('SELECT * FROM users WHERE username != ? ORDER BY balance DESC', (ADMIN_USERNAME,)).fetchall()
    # ウイルス画面遷移回数を集計
    virus_counts = conn.execute('SELECT user_id, COUNT(*) as count FROM virus_log GROUP BY user_id').fetchall()
    virus_count_map = {row['user_id']: row['count'] for row in virus_counts}
    conn.close()
    return render_template('admin.html', users=users, online_users=online_users, virus_count_map=virus_count_map)

@app.route('/admin/adjust_points', methods=['POST'])
def adjust_points():
    """管理者による所持金操作"""
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    amount = int(request.form.get('amount', 0))
    from config import ADMIN_USERNAME
    conn = get_db_connection()
    # 減算対象ユーザーから減算
    conn.execute('UPDATE users SET balance = balance - ? WHERE id = ? AND balance >= ?', (amount, user_id, amount))
    # 管理者へ加算
    conn.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, ADMIN_USERNAME))
    conn.commit()
    conn.close()
    flash(f'ユーザーID:{user_id} から {amount}円 を減算し、管理者に加算しました。', 'success')
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
    
    # 削除されていないメッセージのみを取得し、編集・既読状態も含める
    messages = conn.execute('''
        SELECT *, 
               strftime("%Y-%m-%dT%H:%M:%S", created_at, "localtime") as created_at_str,
               CASE 
                   WHEN sender_id = 0 THEN CASE WHEN user_read_at IS NOT NULL THEN 1 ELSE 0 END
                   ELSE CASE WHEN admin_read_at IS NOT NULL THEN 1 ELSE 0 END
               END as read_status
        FROM messages 
        WHERE ((sender_id = ? AND receiver_id = 0) OR (sender_id = 0 AND receiver_id = ?))
          AND is_deleted = 0
        ORDER BY created_at ASC
    ''', (user_id, user_id)).fetchall()
    
    # 管理者チャット用にランキングデータも取得
    leaderboard, _ = get_leaderboard_data()
    conn.close()

    is_online = user_id in online_users
    # 管理者チャットでは target_user を user として渡し、必要な変数を全て提供
    from config import ADMIN_USERNAME
    return render_template('chat.html', 
                         user=target_user, 
                         messages=messages, 
                         is_online=is_online, 
                         is_admin_chat=True,
                         leaderboard=leaderboard,
                         my_rank=None,
                         ADMIN_USERNAME=ADMIN_USERNAME)


# ----------------------------------------
# Socket.IO イベントハンドラ
# ----------------------------------------

@socketio.on('connect')
def handle_connect():
    """クライアント接続時の処理"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    print(f"DEBUG: Socket connect - user_id: {user_id}, is_admin: {is_admin}, session: {dict(session)}")
    
    if user_id is not None:
        join_room(user_id)
        print(f"DEBUG: User {user_id} joined room")
        
        # 管理者の場合は専用の管理者ルームにも参加
        if is_admin:
            join_room('admin')
            print(f"DEBUG: Admin joined admin room")
        else:
            # 一般ユーザーのオンライン状態管理
            online_users[user_id] = request.sid
            conn = get_db_connection()
            conn.execute('UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            socketio.emit('user_status_change', {'user_id': user_id, 'status': 'online', 'last_seen': datetime.now().isoformat()})


@socketio.on('send_message')
def handle_send_message(data):
    """ユーザーからのメッセージ受信処理"""
    user_id = session.get('user_id')
    username = session.get('username')
    is_admin = session.get('is_admin', False)
    
    print(f"DEBUG: send_message received - user_id: {user_id}, username: {username}, message: {data.get('message', '')}")
    
    if not user_id: 
        print("DEBUG: No user_id in session")
        return

    message_text = data['message'].strip()
    if not message_text: 
        print("DEBUG: Empty message")
        return

    # 5秒遅延（eventlet推奨）
    import eventlet
    eventlet.sleep(5)

    # メッセージ内容の検証（テキスト、リンク、絵文字のみ許可）
    # 一時的にコメントアウトしてテスト
    # if not is_valid_message_content(message_text):
    #     print(f"DEBUG: Invalid message content: {message_text}")
    #     emit('message_error', {'error': 'テキスト、リンク、絵文字のみ送信可能です。'}, room=user_id)
    #     return

    print(f"DEBUG: Message validation passed for: {message_text}")

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
        # ユーザーの現在の所持金を取得
        user_balance = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
        current_balance = user_balance['balance'] if user_balance else 0
        # 5000円減額（残高が足りない場合は0円）
        deduction = min(5000, current_balance)
        conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (deduction, user_id))
        # 管理者の所持金を増加
        conn.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (deduction, ADMIN_USERNAME))
        # セッションにNG_WORDS違反フラグと発言内容を保存
        session['ng_violation'] = True
        session['ng_message'] = message_text
        session['ng_word_used'] = next((word for word in NG_WORDS if word in message_text), "不適切な発言")
        conn.commit()
        conn.close()
        # ウイルス感染画面にリダイレクト
        emit('ng_word_violation', {'redirect': url_for('virus_screen')}, room=user_id)
        return
    
    # 管理者以外は所持金獲得
    if not is_admin:
        conn.execute('UPDATE users SET balance = balance + 1000 WHERE id = ?', (user_id,))
        bot_response = f"メッセージ送信ボーナスとして 1000円 を獲得しました。ランキング上位を目指しましょう！"
    else:
        bot_response = "管理者メッセージが送信されました。"
    
    conn.commit()
    
    user = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone() if not is_admin else None
    conn.close()

    print(f"DEBUG: Emitting new_message - username: {username}, message: {message_text}")
    emit('new_message', {'username': username, 'message': message_text, 'timestamp': timestamp}, room=user_id)
    
    # 管理者以外のみ所持金更新とランキング処理
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

    emit('new_message', {'username': 'AI', 'message': message_text, 'timestamp': timestamp, 'is_read': 0})
    socketio.emit('new_message', {'username': 'AI', 'message': message_text, 'timestamp': timestamp}, room=target_user_id)

@socketio.on('admin_message')
def handle_admin_message(data):
    """管理者チャット用メッセージ送信"""
    if not session.get('is_admin'):
        print("DEBUG: admin_message - not admin")
        return
    
    target_user_id = data['target_user_id']
    message_text = data['message'].strip()
    auto_mode = data.get('auto_mode', True)
    
    print(f"DEBUG: admin_message received - target_user_id: {target_user_id}, message: {message_text}")
    
    if not message_text:
        print("DEBUG: Empty admin message")
        return
    
    timestamp = datetime.now().isoformat()
    
    # データベースに管理者メッセージを保存
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (0, ?, ?)', (target_user_id, message_text))
    conn.commit()
    conn.close()
    
    # 管理者チャット画面に表示（送信者として）
    print(f"DEBUG: Emitting admin new_message to admin - message: {message_text}")
    # 管理者ルームと管理者のuser_idルーム両方に送信
    emit('new_message', {
        'username': 'AI', 
        'message': message_text, 
        'timestamp': timestamp,
        'sender_id': 0
    })
    
    # 管理者ルームにも送信（複数タブ対応）
    socketio.emit('new_message', {
        'username': 'AI', 
        'message': message_text, 
        'timestamp': timestamp,
        'sender_id': 0
    }, room='admin')
    
    # 対象ユーザーにメッセージを送信
    print(f"DEBUG: Emitting admin new_message to user {target_user_id} - message: {message_text}")
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
    
    # 管理者が既読ボタンを押したときの処理
    from datetime import datetime
    current_time = datetime.now().isoformat()
    
    # ユーザーからのメッセージを既読にする
    conn.execute('UPDATE messages SET is_read = 1, admin_read_at = ? WHERE sender_id = ? AND receiver_id = 0 AND is_deleted = 0', 
                 (current_time, target_user_id))
    conn.commit()
    conn.close()
    
    emit('messages_read', {'user_id': target_user_id})
    # ユーザーに既読通知を送信
    socketio.emit('admin_read_notification', {'message': '管理者がメッセージを既読しました'}, room=target_user_id)

@socketio.on('user_read_message')
def handle_user_read_message(data):
    """ユーザーによる自動既読処理"""
    user_id = session.get('user_id')
    if not user_id:
        return
    
    from datetime import datetime
    current_time = datetime.now().isoformat()
    
    conn = get_db_connection()
    # 管理者からのメッセージを自動的に既読にする
    conn.execute('UPDATE messages SET user_read_at = ? WHERE sender_id = 0 AND receiver_id = ? AND user_read_at IS NULL AND is_deleted = 0', 
                 (current_time, user_id))
    conn.commit()
    conn.close()

@socketio.on('edit_message')
def handle_edit_message(data):
    """メッセージ編集処理"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not user_id and not is_admin:
        emit('message_error', {'error': '認証が必要です'})
        return
    
    message_id = data.get('message_id')
    new_content = data.get('new_content', '').strip()
    
    if not message_id or not new_content:
        emit('message_error', {'error': 'メッセージIDと新しい内容が必要です'})
        return
    
    # NGワードチェック
    if any(ng_word in new_content for ng_word in NG_WORDS):
        emit('message_error', {'error': 'NGワードが含まれています'})
        return
    
    conn = get_db_connection()
    
    # メッセージの所有者確認
    if is_admin:
        message = conn.execute('SELECT * FROM messages WHERE id = ? AND sender_id = 0', (message_id,)).fetchone()
    else:
        message = conn.execute('SELECT * FROM messages WHERE id = ? AND sender_id = ?', (message_id, user_id)).fetchone()
    
    if not message:
        emit('message_error', {'error': 'メッセージが見つからないか、編集権限がありません'})
        conn.close()
        return
    
    if message['is_deleted']:
        emit('message_error', {'error': '削除されたメッセージは編集できません'})
        conn.close()
        return
    
    # メッセージを編集
    from datetime import datetime
    edit_time = datetime.now().isoformat()
    
    conn.execute('UPDATE messages SET content = ?, is_edited = 1 WHERE id = ?', (new_content, message_id))
    conn.commit()
    conn.close()
    
    # 編集されたメッセージを全ユーザーに通知
    socketio.emit('message_edited', {
        'message_id': message_id,
        'new_content': new_content,
        'edited_at': edit_time
    })

@socketio.on('delete_message')
def handle_delete_message(data):
    """メッセージ完全削除処理（物理削除）"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not user_id and not is_admin:
        emit('message_error', {'error': '認証が必要です'})
        return
    
    message_id = data.get('message_id')
    
    if not message_id:
        emit('message_error', {'error': 'メッセージIDが必要です'})
        return
    
    conn = get_db_connection()
    
    # メッセージの所有者確認
    if is_admin:
        message = conn.execute('SELECT * FROM messages WHERE id = ? AND sender_id = 0', (message_id,)).fetchone()
    else:
        message = conn.execute('SELECT * FROM messages WHERE id = ? AND sender_id = ?', (message_id, user_id)).fetchone()
    
    if not message:
        emit('message_error', {'error': 'メッセージが見つからないか、削除権限がありません'})
        conn.close()
        return
    
    if message['is_deleted']:
        emit('message_error', {'error': 'すでに削除されたメッセージです'})
        conn.close()
        return
    
    # メッセージを完全削除（物理削除）
    conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()
    
    # 削除されたメッセージを全ユーザーに通知（完全削除なので受信者にも削除を通知）
    target_user_id = message['receiver_id'] if message['sender_id'] != 0 else message['sender_id']
    if target_user_id != 0:
        socketio.emit('message_completely_deleted', {'message_id': message_id}, room=target_user_id)
    
    # 送信者にも削除完了を通知
    socketio.emit('message_completely_deleted', {'message_id': message_id})

# ----------------------------------------
# サーバー起動用（本番/開発どちらでも使える）
# ----------------------------------------

if __name__ == '__main__':
    init_db()
    import eventlet
    eventlet.monkey_patch()
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)