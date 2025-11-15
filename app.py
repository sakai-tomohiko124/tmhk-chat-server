# ===================================================================
# geventのモンキーパッチは、他のどのライブラリよりも先に
# 実行する必要があるため、必ずファイルの最上部に記述します。
# ===================================================================
from gevent import monkey
monkey.patch_all()
#
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, abort, send_from_directory, jsonify, Response, stream_with_context
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import redis
from functools import wraps
import base64
import uuid
import shutil
from openai import OpenAI

# --- アプリケーションの基本設定 ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key_should_be_changed'
app.config['UPLOAD_FOLDER'] = 'uploads'
# 1ファイルあたりの上限（アプリ内チェック用）。Socket.IO 経由で base64 を送るため
# 大きなファイルはメモリと時間を多く消費します。安全上の実運用ではチャンク化アップロード
# を推奨しますが、開発/短期対応としてここでは 10GB に設定します。
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 1ファイルあたりの上限は10GB
app.config['UPLOAD_TEMP_FOLDER'] = 'uploads_tmp'
# サーバーが期待するチャンクサイズ（クライアントはこれを参照して分割送信します）
app.config['CHUNK_SIZE'] = 10 * 1024 * 1024  # 10MB

# アップロード先フォルダが存在しない場合は起動時に作成しておく
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
if not os.path.exists(app.config['UPLOAD_TEMP_FOLDER']):
    os.makedirs(app.config['UPLOAD_TEMP_FOLDER'], exist_ok=True)

# cleanup old incomplete upload_tmp directories (simple TTL: remove dirs older than 24 hours)
now_ts = datetime.utcnow()
for name in os.listdir(app.config['UPLOAD_TEMP_FOLDER']):
    p = os.path.join(app.config['UPLOAD_TEMP_FOLDER'], name)
    try:
        mtime = datetime.utcfromtimestamp(os.path.getmtime(p))
        if (now_ts - mtime).total_seconds() > 24*3600:
            if os.path.isdir(p): shutil.rmtree(p)
            else: os.remove(p)
    except Exception:
        continue

# --- 外部サービスの設定 ---
# 環境変数からRedisのURLを取得。なければローカルのデフォルト値を使用。
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# OpenAI APIクライアントの初期化
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Google AI API設定（既存機能との互換性維持）
import google.generativeai as genai
GOOGLE_API_KEY = os.environ.get('GOOGLE_AI_API_KEY', '')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# サービスのインポート
try:
    from services.ai_bot import AIBot
    from services.rtc_signaling import RTCSignalingServer
    from services.external_data import ExternalDataService, periodic_data_update
    
    # サービスの初期化
    ai_bot = AIBot() if GOOGLE_API_KEY else None
    rtc_server = RTCSignalingServer()
    external_data_service = ExternalDataService()
except ImportError as e:
    print(f"Warning: Could not import services: {e}")
    ai_bot = None
    rtc_server = None
    external_data_service = None

# Redisに接続
try:
    # decode_responses=Trueにすると、Redisからの応答が文字列としてデコードされる
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping() # サーバーへの接続をテスト
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"!!! WARNING: Could not connect to Redis: {e}")
    r = None # Redisに接続できなかった場合はNoneにして、後続の処理でチェックする

# --- SocketIO設定 (async_mode='gevent' を指定) ---
# message_queueを指定することで、Gunicornの複数ワーカー間でイベントを共有できる
socketio = SocketIO(app, async_mode='gevent', message_queue=REDIS_URL)

# --- 定数設定 ---
DATABASE = 'chat.db'
GROUP_ROOM = "__group__"
ONLINE_USERS_KEY = "online_users" # Redisでオンラインユーザーを管理するためのキー名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'pdf'}
MAX_STORAGE_BYTES = 1 * 1024 * 1024 * 1024 * 1024  # ストレージ上限を1TBに設定

# --- データベース関連 ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('data.sql', mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()

        # ensure follows table exists (for follow relationships)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS follows (follower TEXT NOT NULL, followee TEXT NOT NULL, PRIMARY KEY(follower, followee))')
            db.commit()
        except Exception:
            pass

        # ensure messages has a 'safe' column (0/1). SQLite supports ADD COLUMN.
        try:
            cur = db.execute("PRAGMA table_info(messages)")
            cols = [r['name'] for r in cur.fetchall()]
            if 'safe' not in cols:
                db.execute('ALTER TABLE messages ADD COLUMN safe INTEGER DEFAULT 1')
                db.commit()
        except Exception:
            pass

@app.cli.command('init-db')
def init_db_command():
    init_db()
    print('Initialized the database.')

# --- ストレージ管理用のヘルパー関数 ---
def get_total_upload_size():
    """uploadsフォルダ内の全ファイル合計サイズを返す"""
    total_size = 0
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        return 0
    for entry in os.scandir(upload_folder):
        if entry.is_file():
            try:
                total_size += entry.stat().st_size
            except FileNotFoundError:
                # スキャンと削除の間にファイルが消えた場合のエラーを無視
                continue
    return total_size

def enforce_storage_limit():
    """ストレージ上限を超えていれば、古いファイルから削除する"""
    upload_folder = app.config['UPLOAD_FOLDER']
    while get_total_upload_size() > MAX_STORAGE_BYTES:
        # このスコープ内でのみ使用するDB接続
        with app.app_context():
            db = get_db()
            # 最も古いファイルを持つメッセージを取得
            # PDF は削除対象外とし、管理者ユーザー（ユーザー名 'ともひこ'）のファイルも削除しない
            oldest_file_msg = db.execute(
                "SELECT id, file_path FROM messages WHERE file_path IS NOT NULL AND file_type != 'pdf' AND username != ? ORDER BY timestamp ASC LIMIT 1",
                ('ともひこ',)
            ).fetchone()
            
            if oldest_file_msg:
                file_id_to_delete = oldest_file_msg['id']
                file_path_to_delete = oldest_file_msg['file_path']
                full_path = os.path.join(upload_folder, file_path_to_delete)
                
                # 物理ファイルを削除
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"Storage limit exceeded. Deleted oldest file: {file_path_to_delete}")
                
                # データベースから該当メッセージを削除 (これにより未読情報もCASCADEで消える)
                db.execute("DELETE FROM messages WHERE id = ?", (file_id_to_delete,))
                db.commit()
            else:
                # 削除対象のファイルが見つからなければループを抜ける
                break

# --- その他のヘルパー関数 ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def generate_dm_room(user1, user2):
    users = sorted([user1, user2])
    return f"dm_{users[0]}_{users[1]}"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Flaskのルーティング (Webページ表示) ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        inviter = request.args.get('invite')
        if inviter:
            session['invited_by'] = inviter
        return render_template('index.html')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            flash("ユーザー名を入力してください.")
            return redirect(url_for('index'))
        if r:
            try:
                if r.sismember(ONLINE_USERS_KEY, username):
                    flash("その名前は既に使用されています。")
                    return redirect(url_for('index'))
            except redis.exceptions.ConnectionError:
                print("Warning: Could not check for duplicate username because Redis is not available.")
        
        session['username'] = 'ともひこ' if username == 'ともひこです' else username
        session['is_admin'] = (username == 'ともひこです')

        inviter = session.pop('invited_by', None)
        if inviter and session['username'] != inviter:
            dm_room = generate_dm_room(session['username'], inviter)
            return redirect(url_for('chat', room=dm_room))
        else:
            return redirect(url_for('chat', room=GROUP_ROOM))

@app.route('/chat')
@app.route('/chat/<room>')
def chat(room=GROUP_ROOM):
    username = session.get('username')
    if not username:
        return redirect(url_for('index'))

    db = get_db()
    # Build a robust list of users we've had any conversation with
    users_with_history_set = set()
    # 1) users who have sent messages (simple case)
    rows = db.execute("SELECT DISTINCT username FROM messages WHERE username != ?", (username,)).fetchall()
    for r in rows:
        users_with_history_set.add(r['username'])
    # 2) users who appear in dm room names
    dm_rooms = db.execute("SELECT DISTINCT room FROM messages WHERE room LIKE 'dm_%'").fetchall()
    for r in dm_rooms:
        room_name = r['room']
        parts = room_name.split('_')
        if len(parts) == 3 and (parts[1] == username or parts[2] == username):
            other = parts[2] if parts[1] == username else parts[1]
            if other != username:
                users_with_history_set.add(other)

    users_with_history = sorted(list(users_with_history_set))

    # determine currently online users from Redis (if available)
    try:
        online_users_set = set(r.smembers(ONLINE_USERS_KEY)) if r else set()
    except Exception:
        online_users_set = set()

    # unread counts per room for the current user
    unread_counts_rows = db.execute("SELECT m.room, COUNT(m.id) as count FROM messages m JOIN unread_messages um ON m.id = um.message_id WHERE um.user_username = ? GROUP BY m.room", (username,)).fetchall()
    unread_counts = {row['room']: row['count'] for row in unread_counts_rows}

    # Build history list entries with room name and per-user unread count
    history_list = []
    for other in users_with_history:
        dm_room = generate_dm_room(username, other)
        count = unread_counts.get(dm_room, 0)
        # get last message timestamp and excerpt for this dm
        last_row = db.execute('SELECT id, message, file_path, file_type, timestamp FROM messages WHERE room = ? ORDER BY timestamp DESC LIMIT 1', (dm_room,)).fetchone()
        last_ts = last_row['timestamp'] if last_row and last_row['timestamp'] else None
        last_excerpt = None
        last_file_type = None
        last_file_path = None
        if last_row:
            if last_row['message']:
                last_excerpt = (last_row['message'][:80] + '...') if len(last_row['message']) > 80 else last_row['message']
            elif last_row['file_path']:
                last_file_type = last_row['file_type']
                last_file_path = last_row['file_path']
        has_unread = 1 if count > 0 else 0
        # mark whether the other user is currently online (based on Redis set)
        is_online = (other in online_users_set)
        history_list.append({'username': other, 'room': dm_room, 'unread_count': count, 'last_timestamp': last_ts, 'has_unread': has_unread, 'last_excerpt': last_excerpt, 'last_file_type': last_file_type, 'last_file_path': last_file_path, 'is_online': is_online})

    # sort: unread first, then by last_timestamp desc (most recent first). If timestamp is None, treat as very old.
    def sort_key(item):
        ts = item.get('last_timestamp') or '0000-00-00 00:00:00'
        return (item.get('has_unread', 0), ts)

    history_list.sort(key=sort_key, reverse=True)

    # By default, hide offline users from the history list to avoid accumulating stale entries.
    # If you want to show offline users, pass query param ?show_offline=1
    if request.args.get('show_offline') != '1':
        history_list = [h for h in history_list if h.get('is_online')]

    # By default, filter to show only users the current user follows (friends) unless admin or ?show_all=1
    try:
        if not session.get('is_admin') and request.args.get('show_all') != '1':
            db = get_db()
            followed_rows = db.execute('SELECT followee FROM follows WHERE follower = ?', (username,)).fetchall()
            followed = set([r['followee'] for r in followed_rows])
            history_list = [h for h in history_list if h['username'] in followed]
    except Exception:
        pass
    messages_raw = db.execute('SELECT * FROM messages WHERE room = ? ORDER BY timestamp ASC', (room,)).fetchall()
    
    messages = []
    for msg in messages_raw:
        msg_dict = dict(msg)
        utc_dt = datetime.strptime(msg_dict['timestamp'], '%Y-%m-%d %H:%M:%S')
        jst_dt = utc_dt + timedelta(hours=9)
        msg_dict['timestamp_formatted'] = jst_dt.strftime('%Y-%m-%d %H:%M')
        messages.append(msg_dict)
    
    chat_partner = None
    if room.startswith("dm_"):
        parts = room.split('_')
        chat_partner = parts[2] if parts[1] == username else parts[1]
    # Determine initial filter and partner_source from URL to render partner_select server-side
    initial_filter = request.args.get('filter', 'followers')
    initial_partner_source = request.args.get('partner_source', 'online')
    partner_candidates = []
    try:
        if initial_partner_source == 'online':
            # use Redis-derived online users (exclude self)
            try:
                online_users_set = set(r.smembers(ONLINE_USERS_KEY)) if r else set()
            except Exception:
                online_users_set = set()
            partner_candidates = sorted([u for u in online_users_set if u != username])
        elif initial_partner_source == 'history':
            # Build candidates from full users_with_history (not the possibly filtered history_list)
            candidates_info = []
            for other in users_with_history:
                dm_room = generate_dm_room(username, other)
                # unread count
                try:
                    unread_cnt = unread_counts.get(dm_room, 0)
                except Exception:
                    unread_cnt = 0
                # last timestamp
                try:
                    last_row = db.execute('SELECT MAX(timestamp) as last_ts FROM messages WHERE room = ?', (dm_room,)).fetchone()
                    last_ts = last_row['last_ts'] if last_row and last_row['last_ts'] else None
                except Exception:
                    last_ts = None
                candidates_info.append({'username': other, 'unread': unread_cnt, 'last_ts': last_ts or '0000-00-00 00:00:00'})
            # sort: unread desc, then recent last_ts desc
            candidates_info.sort(key=lambda x: (x['unread'], x['last_ts']), reverse=True)
            partner_candidates = [c['username'] for c in candidates_info]
        elif initial_partner_source == 'all' and session.get('is_admin'):
            rows = db.execute("SELECT DISTINCT username FROM messages ORDER BY username").fetchall()
            partner_candidates = [r['username'] for r in rows if r['username'] != username]
    except Exception:
        partner_candidates = []

    return render_template('chat.html',
                           username=username,
                           messages=messages,
                           is_admin=session.get('is_admin', False),
                           users_with_history=history_list,
                           partner_candidates=partner_candidates,
                           initial_filter=initial_filter,
                           initial_partner_source=initial_partner_source,
                           current_room=room,
                           GROUP_ROOM=GROUP_ROOM,
                           chat_partner=chat_partner,
                           unread_counts=unread_counts,
                           MAX_CONTENT_BYTES=app.config.get('MAX_CONTENT_LENGTH', 16*1024*1024),
                           CHUNK_SIZE=app.config.get('CHUNK_SIZE', 5*1024*1024))

@app.route('/start_dm', methods=['POST'])
def start_dm():
    username = session.get('username')
    partner = request.form.get('partner')
    if not username or not partner or username == partner:
        return redirect(url_for('chat', room=GROUP_ROOM))
    dm_room = generate_dm_room(username, partner)
    return redirect(url_for('chat', room=dm_room))


@app.route('/follow', methods=['POST'])
def follow():
    follower = session.get('username')
    followee = request.form.get('username')
    if not follower or not followee or follower == followee:
        return jsonify({'status': 'error', 'reason': 'invalid parameters'}), 400
    db = get_db()
    try:
        db.execute('INSERT OR IGNORE INTO follows (follower, followee) VALUES (?, ?)', (follower, followee))
        db.commit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'reason': str(e)}), 500


@app.route('/unfollow', methods=['POST'])
def unfollow():
    follower = session.get('username')
    followee = request.form.get('username')
    if not follower or not followee or follower == followee:
        return jsonify({'status': 'error', 'reason': 'invalid parameters'}), 400
    db = get_db()
    try:
        db.execute('DELETE FROM follows WHERE follower = ? AND followee = ?', (follower, followee))
        db.commit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'reason': str(e)}), 500


@app.route('/is_following')
def is_following():
    follower = session.get('username')
    followee = request.args.get('username')
    if not follower or not followee:
        return jsonify({'following': False})
    db = get_db()
    try:
        row = db.execute('SELECT 1 FROM follows WHERE follower = ? AND followee = ?', (follower, followee)).fetchone()
        return jsonify({'following': True if row else False})
    except Exception:
        return jsonify({'following': False})


@app.route('/features')
def features():
    """機能一覧ページ"""
    username = session.get('username')
    if not username:
        return redirect(url_for('index'))
    return render_template('features.html')

@app.route('/online_status')
def online_status():
    """Returns current online users and follow relationships for the session user.
    Response JSON:
      { online: [...], followers: [...], following: [...] }
    """
    username = session.get('username')
    if not username:
        return jsonify({'online': [], 'followers': [], 'following': []})
    # online users from Redis
    try:
        online = list(r.smembers(ONLINE_USERS_KEY)) if r else []
    except Exception:
        online = []
    followers = []
    following = []
    try:
        db = get_db()
        # users who follow the current user
        rows = db.execute('SELECT follower FROM follows WHERE followee = ?', (username,)).fetchall()
        followers = [r['follower'] for r in rows]
        # users whom current user follows
        rows2 = db.execute('SELECT followee FROM follows WHERE follower = ?', (username,)).fetchall()
        following = [r['followee'] for r in rows2]
    except Exception:
        pass
    return jsonify({'online': online, 'followers': followers, 'following': following})


@app.route('/users_list')
@admin_required
def users_list():
    """Return a list of all known users (from messages). Admin-only endpoint."""
    try:
        db = get_db()
        rows = db.execute("SELECT DISTINCT username FROM messages ORDER BY username").fetchall()
        users = [r['username'] for r in rows]
        return jsonify({'users': users})
    except Exception:
        return jsonify({'users': []})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
@app.route('/admin')
@admin_required
def admin_panel():
    db = get_db()
    users = db.execute("SELECT DISTINCT username FROM messages WHERE username != 'ともひこ' ORDER BY username").fetchall()
    selected_user_name = request.args.get('user', None)
    selected_user_messages = []
    if selected_user_name:
        selected_user_messages = db.execute(
            "SELECT * FROM messages WHERE username = ? OR room LIKE ? OR room LIKE ? ORDER BY timestamp DESC",
            (selected_user_name, f'dm_{selected_user_name}_%', f'dm_%_{selected_user_name}')
        ).fetchall()
    return render_template('admin.html',
                           users=users,
                           selected_user=selected_user_name,
                           messages=selected_user_messages,
                           username=session.get('username'))

@app.route('/admin/edit_user', methods=['POST'])
@admin_required
def edit_user():
    old_username = request.form.get('old_username')
    new_username = request.form.get('new_username', '').strip()
    if not all([old_username, new_username]):
        flash("ユーザー名が正しくありません。", 'error')
        return redirect(url_for('admin_panel'))
    db = get_db()
    db.execute("UPDATE messages SET username = ? WHERE username = ?", (new_username, old_username))
    db.commit()
    flash(f"「{old_username}」を「{new_username}」に更新しました。", 'success')
    return redirect(url_for('admin_panel', user=new_username))

@app.route('/admin/delete_user', methods=['POST'])
@admin_required
def delete_user():
    username_to_delete = request.form.get('username')
    if not username_to_delete:
        flash("削除するユーザーが指定されていません。", 'error')
        return redirect(url_for('admin_panel'))
    db = get_db()
    db.execute("DELETE FROM messages WHERE username = ?", (username_to_delete,))
    db.execute("DELETE FROM messages WHERE room LIKE ? OR room LIKE ?", (f'dm_{username_to_delete}_%', f'dm_%_{username_to_delete}'))
    db.commit()
    flash(f"「{username_to_delete}」さんのアカウントと関連メッセージを削除しました。", 'success')
    return redirect(url_for('admin_panel'))

@app.route('/ai/stream', methods=['POST'])
def ai_stream():
    """OpenAI APIを使用してストリーミング形式でAI応答を返す"""
    if not openai_client:
        return jsonify({'error': 'OpenAI API key not configured'}), 500
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    conversation_history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    # 会話履歴を構築
    messages = [{"role": "system", "content": "あなたは親切で役に立つAIアシスタントです。日本語で丁寧に回答してください。"}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    
    def generate():
        try:
            stream = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=1000
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    # Server-Sent Events形式で送信
                    yield f"data: {content}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR]: {str(e)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

# --- SocketIOイベントハンドラ ---
@socketio.on('connect')
def handle_connect(*args, **kwargs):
    username = session.get('username')
    if not username or not r: return
    r.sadd(ONLINE_USERS_KEY, username)
    online_users = list(r.smembers(ONLINE_USERS_KEY))
    emit('update_user_list', online_users, broadcast=True)
    db = get_db()
    unread_messages = db.execute("SELECT m.* FROM messages m JOIN unread_messages um ON m.id = um.message_id WHERE um.user_username = ? ORDER BY m.timestamp ASC", (username,)).fetchall()
    if unread_messages:
        emit('receive_offline_messages', [dict(row) for row in unread_messages])
        db.execute("DELETE FROM unread_messages WHERE user_username = ?", (username,)); db.commit()

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if not username or not r: return
    r.srem(ONLINE_USERS_KEY, username)
    online_users = list(r.smembers(ONLINE_USERS_KEY))
    emit('update_user_list', online_users, broadcast=True)

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room')
    if room: join_room(room)

@socketio.on('mark_as_read')
def handle_mark_as_read(data):
    username = session.get('username'); room = data.get('room')
    if not username or not room: return
    # If the current user is admin, do not mark messages as read in the DB
    # (admin's viewing should not change unread state for regular users)
    if session.get('is_admin'):
        return
    db = get_db(); db.execute("DELETE FROM unread_messages WHERE user_username = ? AND message_id IN (SELECT id FROM messages WHERE room = ?)", (username, room)); db.commit()

@socketio.on('typing')
def handle_typing(data):
    username = session.get('username'); room = data.get('room', GROUP_ROOM)
    if username and room: emit('user_typing', {'username': username}, to=room, include_self=False)

@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username'); room = data.get('room', GROUP_ROOM)
    if not username or not room: return
    if room == GROUP_ROOM and not session.get('is_admin'):
        # inform client that non-admins cannot send to group
        emit('file_upload_result', {'status': 'error', 'reason': 'グループチャットは管理者のみ送信できます。'}, to=request.sid)
        return
        
    message_text = data.get('message'); file_data = data.get('file')
    db = get_db(); cursor = db.cursor(); new_msg_id = None

    if message_text:
        # determine safe flag: if DM, sender must follow recipient to be 'safe'
        safe_flag = 1
        if room.startswith('dm_'):
            parts = room.split('_')
            other = parts[2] if parts[1] == username else parts[1]
            try:
                row = db.execute('SELECT 1 FROM follows WHERE follower = ? AND followee = ?', (username, other)).fetchone()
                safe_flag = 1 if row else 0
            except Exception:
                safe_flag = 0
        cursor.execute('INSERT INTO messages (room, username, message, safe) VALUES (?, ?, ?, ?)', (room, username, message_text, safe_flag))
        new_msg_id = cursor.lastrowid
    elif file_data:
        # file_data may come as {'name': ..., 'data': <bytes> } or {'name': ..., 'data': 'data:...;base64,...'}
        original_filename = secure_filename(file_data.get('name', 'upload'))
        if allowed_file(original_filename):
            # make filename unique to avoid collisions
            unique_suffix = uuid.uuid4().hex[:8]
            filename = f"{os.path.splitext(original_filename)[0]}_{unique_suffix}{os.path.splitext(original_filename)[1]}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            raw = file_data.get('data')
            try:
                if isinstance(raw, (bytes, bytearray)):
                    data_bytes = raw
                elif isinstance(raw, str) and raw.startswith('data:') and 'base64,' in raw:
                    data_bytes = base64.b64decode(raw.split('base64,',1)[1])
                elif isinstance(raw, str):
                    data_bytes = base64.b64decode(raw)
                else:
                    data_bytes = None
                if data_bytes is None:
                    raise ValueError('Unsupported file data format')
                # size check
                size_bytes = len(data_bytes)
                print(f"Received file upload attempt: user={username}, name={original_filename}, size={size_bytes} bytes, room={room}")
                if size_bytes > app.config.get('MAX_CONTENT_LENGTH', 16*1024*1024):
                    limit = app.config.get('MAX_CONTENT_LENGTH')
                    def human(n):
                        for unit in ['B','KB','MB','GB','TB']:
                            if n < 1024:
                                return f"{n:.2f}{unit}"
                            n = n/1024
                        return f"{n:.2f}PB"
                    emit('file_upload_result', {'status': 'error', 'reason': f'ファイルサイズが大きすぎます（送信: {size_bytes} バイト）。上限は {human(limit)} です。'}, to=request.sid)
                    filepath = None
                else:
                    with open(filepath, 'wb') as f:
                        f.write(data_bytes)
                    # inform client of success for this file
                    emit('file_upload_result', {'status': 'success', 'filename': filename, 'size': size_bytes}, to=request.sid)
            except Exception as e:
                print(f"Failed to write uploaded file: {e}")
                emit('file_upload_result', {'status': 'error', 'reason': str(e)}, to=request.sid)
                filepath = None
            
            # 非管理者（かつ本番環境）の場合のみストレージ上限をチェック・適用
            if not session.get('is_admin'):
                enforce_storage_limit()

            file_ext = filename.rsplit('.', 1)[1].lower()
            if file_ext in {'png', 'jpg', 'jpeg', 'gif'}: file_type = 'image'
            elif file_ext in {'mp4', 'mov', 'avi'}: file_type = 'video'
            elif file_ext == 'pdf': file_type = 'pdf'
            else: file_type = 'file'
            # determine safe flag for file messages as well
            safe_flag = 1
            if room.startswith('dm_'):
                parts = room.split('_')
                other = parts[2] if parts[1] == username else parts[1]
                try:
                    row = db.execute('SELECT 1 FROM follows WHERE follower = ? AND followee = ?', (username, other)).fetchone()
                    safe_flag = 1 if row else 0
                except Exception:
                    safe_flag = 0
            cursor.execute('INSERT INTO messages (room, username, file_path, file_type, safe) VALUES (?, ?, ?, ?, ?)', (room, username, filename, file_type, safe_flag))
            new_msg_id = cursor.lastrowid
    else: return
    db.commit()
    if not new_msg_id: return

    recipients = []
    if room == GROUP_ROOM:
        all_users = db.execute("SELECT DISTINCT username FROM messages").fetchall(); recipients = [u['username'] for u in all_users if u['username'] != username]
    elif room.startswith("dm_"):
        parts = room.split('_'); recipients.append(parts[2] if parts[1] == username else parts[1])
    if r:
        online_users = r.smembers(ONLINE_USERS_KEY)
        for user in recipients:
            if user not in online_users: db.execute("INSERT OR IGNORE INTO unread_messages (user_username, message_id) VALUES (?, ?)", (user, new_msg_id))
        db.commit()

    new_msg_row = db.execute('SELECT * FROM messages WHERE id = ?', (new_msg_id,)).fetchone()
    if not new_msg_row:
        print("Message may have been deleted by storage management before emission."); return
        
    msg_to_emit = dict(new_msg_row)
    utc_dt = datetime.strptime(msg_to_emit['timestamp'], '%Y-%m-%d %H:%M:%S')
    jst_dt = utc_dt + timedelta(hours=9)
    msg_to_emit['timestamp_formatted'] = jst_dt.strftime('%Y-%m-%d %H:%M')
    socketio.emit('new_message', msg_to_emit, to=room)

    # If this is a DM room, emit an update_history event so connected participants can
    # dynamically update their history lists. Include unread counts per user for this room.
    if room.startswith('dm_'):
        parts = room.split('_')
        participant_a = parts[1]
        participant_b = parts[2]
        # unread counts per user for this room
        unread_rows = db.execute(
            "SELECT um.user_username, COUNT(um.message_id) as cnt FROM unread_messages um JOIN messages m ON m.id = um.message_id WHERE m.room = ? GROUP BY um.user_username",
            (room,)
        ).fetchall()
        unread_map = {r['user_username']: r['cnt'] for r in unread_rows}
        # get last timestamp for this room and convert to ISO-like format for client
        last_row = db.execute('SELECT MAX(timestamp) as last_ts FROM messages WHERE room = ?', (room,)).fetchone()
        last_ts = last_row['last_ts'] if last_row and last_row['last_ts'] else None
        last_ts_iso = (last_ts.replace(' ', 'T') + 'Z') if last_ts else None
        # include followers lists for each participant so clients can determine follow relationship
        try:
            followers_a = [r['follower'] for r in db.execute('SELECT follower FROM follows WHERE followee = ?', (participant_a,)).fetchall()]
            followers_b = [r['follower'] for r in db.execute('SELECT follower FROM follows WHERE followee = ?', (participant_b,)).fetchall()]
        except Exception:
            followers_a = []
            followers_b = []
        socketio.emit('update_history', {'room': room, 'participants': [participant_a, participant_b], 'unread': unread_map, 'last_timestamp': last_ts_iso, 'followers': {participant_a: followers_a, participant_b: followers_b}}, to=room)


@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    # Expected form fields: upload_id, chunk_index, total_chunks, filename, room
    upload_id = request.form.get('upload_id')
    chunk_index = request.form.get('chunk_index')
    total_chunks = request.form.get('total_chunks')
    filename = request.form.get('filename')
    room = request.form.get('room', GROUP_ROOM)
    username = session.get('username')
    if not upload_id or chunk_index is None or not total_chunks or not filename or not username:
        return jsonify({'status': 'error', 'reason': 'missing parameters'}), 400
    try:
        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)
    except ValueError:
        return jsonify({'status': 'error', 'reason': 'invalid chunk indices'}), 400

    chunk_file = request.files.get('chunk')
    if not chunk_file:
        return jsonify({'status': 'error', 'reason': 'no chunk file'}), 400

    # save chunk to temporary folder
    upload_dir = os.path.join(app.config['UPLOAD_TEMP_FOLDER'], upload_id)
    os.makedirs(upload_dir, exist_ok=True)
    chunk_path = os.path.join(upload_dir, f"chunk_{chunk_index}")
    try:
        chunk_file.save(chunk_path)
    except Exception as e:
        return jsonify({'status': 'error', 'reason': f'failed to save chunk: {e}'}), 500

    # check if all chunks present
    present = [name for name in os.listdir(upload_dir) if name.startswith('chunk_')]
    if len(present) < total_chunks:
        return jsonify({'status': 'ok', 'received_chunks': len(present)})

    # assemble file
    original_filename = secure_filename(filename)
    unique_suffix = uuid.uuid4().hex[:8]
    unique_filename = f"{os.path.splitext(original_filename)[0]}_{unique_suffix}{os.path.splitext(original_filename)[1]}"
    final_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    try:
        with open(final_path, 'wb') as dest:
            for i in range(total_chunks):
                part_path = os.path.join(upload_dir, f"chunk_{i}")
                with open(part_path, 'rb') as src:
                    shutil.copyfileobj(src, dest)
        # clean up temp dir
        shutil.rmtree(upload_dir)
    except Exception as e:
        return jsonify({'status': 'error', 'reason': f'failed to assemble file: {e}'}), 500

    # Insert into DB and unread handling similar to send_message file branch
    try:
        db = get_db(); cursor = db.cursor()
        file_ext = unique_filename.rsplit('.', 1)[1].lower() if '.' in unique_filename else ''
        if file_ext in {'png', 'jpg', 'jpeg', 'gif'}: file_type = 'image'
        elif file_ext in {'mp4', 'mov', 'avi'}: file_type = 'video'
        elif file_ext == 'pdf': file_type = 'pdf'
        else: file_type = 'file'
        # determine safe flag for assembled file
        safe_flag = 1
        if room.startswith('dm_'):
            parts = room.split('_')
            other = parts[2] if parts[1] == username else parts[1]
            try:
                row = db.execute('SELECT 1 FROM follows WHERE follower = ? AND followee = ?', (username, other)).fetchone()
                safe_flag = 1 if row else 0
            except Exception:
                safe_flag = 0
        cursor.execute('INSERT INTO messages (room, username, file_path, file_type, safe) VALUES (?, ?, ?, ?, ?)', (room, username, unique_filename, file_type, safe_flag))
        new_msg_id = cursor.lastrowid
        db.commit()
        # mark unread for offline recipients
        recipients = []
        if room == GROUP_ROOM:
            all_users = db.execute("SELECT DISTINCT username FROM messages").fetchall(); recipients = [u['username'] for u in all_users if u['username'] != username]
        elif room.startswith('dm_'):
            parts = room.split('_'); recipients.append(parts[2] if parts[1] == username else parts[1])
        if r:
            online_users = r.smembers(ONLINE_USERS_KEY)
            for user in recipients:
                if user not in online_users: db.execute("INSERT OR IGNORE INTO unread_messages (user_username, message_id) VALUES (?, ?)", (user, new_msg_id))
            db.commit()
        # emit new_message and update_history
        new_msg_row = db.execute('SELECT * FROM messages WHERE id = ?', (new_msg_id,)).fetchone()
        if new_msg_row:
            msg_to_emit = dict(new_msg_row)
            utc_dt = datetime.strptime(msg_to_emit['timestamp'], '%Y-%m-%d %H:%M:%S')
            jst_dt = utc_dt + timedelta(hours=9)
            msg_to_emit['timestamp_formatted'] = jst_dt.strftime('%Y-%m-%d %H:%M')
            socketio.emit('new_message', msg_to_emit, to=room)
            if room.startswith('dm_'):
                parts = room.split('_')
                participant_a = parts[1]; participant_b = parts[2]
                unread_rows = db.execute(
                    "SELECT um.user_username, COUNT(um.message_id) as cnt FROM unread_messages um JOIN messages m ON m.id = um.message_id WHERE m.room = ? GROUP BY um.user_username",
                    (room,)
                ).fetchall()
                unread_map = {r['user_username']: r['cnt'] for r in unread_rows}
                last_row = db.execute('SELECT MAX(timestamp) as last_ts FROM messages WHERE room = ?', (room,)).fetchone()
                last_ts = last_row['last_ts'] if last_row and last_row['last_ts'] else None
                last_ts_iso = (last_ts.replace(' ', 'T') + 'Z') if last_ts else None
                try:
                    followers_a = [r['follower'] for r in db.execute('SELECT follower FROM follows WHERE followee = ?', (participant_a,)).fetchall()]
                    followers_b = [r['follower'] for r in db.execute('SELECT follower FROM follows WHERE followee = ?', (participant_b,)).fetchall()]
                except Exception:
                    followers_a = []
                    followers_b = []
                socketio.emit('update_history', {'room': room, 'participants': [participant_a, participant_b], 'unread': unread_map, 'last_timestamp': last_ts_iso, 'followers': {participant_a: followers_a, participant_b: followers_b}}, to=room)
    except Exception as e:
        print(f"Error inserting assembled file message: {e}")
        return jsonify({'status': 'error', 'reason': str(e)}), 500

    return jsonify({'status': 'ok', 'filename': unique_filename})

# --- AI Chat WebSocket Handlers ---
@socketio.on('send_to_ai')
def handle_ai_message(data):
    """Google Gemini AIへのメッセージ送信（既存機能との互換性）"""
    username = session.get('username')
    if not username:
        emit('ai_response', {'message': 'ログインが必要です。'})
        return
    
    message = data.get('message', '').strip()
    if not message:
        return
    
    # Google Gemini AIを使用
    if not GOOGLE_API_KEY:
        emit('ai_response', {'message': 'Google AI APIキーが設定されていません。'})
        return
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(message)
        ai_response_text = response.text
        emit('ai_response', {'message': ai_response_text})
    except Exception as e:
        emit('ai_response', {'message': f'申し訳ありません、AIとの通信中にエラーが発生しました: {str(e)}'})

@socketio.on('send_to_openai')
def handle_openai_message(data):
    """OpenAI GPTへのメッセージ送信（新機能）"""
    username = session.get('username')
    if not username:
        emit('openai_response', {'message': 'ログインが必要です。'})
        return
    
    message = data.get('message', '').strip()
    conversation_history = data.get('history', [])
    
    if not message:
        return
    
    if not openai_client:
        emit('openai_response', {'message': 'OpenAI APIキーが設定されていません。'})
        return
    
    try:
        # 会話履歴を構築
        messages = [{"role": "system", "content": "あなたは親切で役に立つAIアシスタントです。日本語で丁寧に回答してください。"}]
        messages.extend(conversation_history[-10:])  # 直近10件の履歴
        messages.append({"role": "user", "content": message})
        
        # OpenAI APIでストリーミング応答を生成
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=1000
        )
        
        # ストリーミングでクライアントに送信
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                emit('openai_chunk', {'content': content})
        
        # 完了シグナルを送信
        emit('openai_done', {})
        
    except Exception as e:
        emit('openai_response', {'message': f'申し訳ありません、OpenAI APIとの通信中にエラーが発生しました: {str(e)}'})

# --- WebRTC Signaling Handlers ---
@socketio.on('join_call')
def handle_join_call(data):
    """WebRTC通話ルームに参加"""
    if rtc_server:
        result = rtc_server.handle_join_call(data)
        emit('call_joined', result)

@socketio.on('leave_call')
def handle_leave_call(data):
    """WebRTC通話ルームから退出"""
    if rtc_server:
        rtc_server.handle_leave_call(data)

@socketio.on('rtc_offer')
def handle_rtc_offer(data):
    """WebRTC Offerの転送"""
    if rtc_server:
        rtc_server.handle_offer(data)

@socketio.on('rtc_answer')
def handle_rtc_answer(data):
    """WebRTC Answerの転送"""
    if rtc_server:
        rtc_server.handle_answer(data)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    """ICE Candidateの転送"""
    if rtc_server:
        rtc_server.handle_ice_candidate(data)

@socketio.on('call_request')
def handle_call_request(data):
    """通話リクエストの送信"""
    if rtc_server:
        rtc_server.handle_call_request(data)

@socketio.on('call_response')
def handle_call_response(data):
    """通話リクエストへの応答"""
    if rtc_server:
        rtc_server.handle_call_response(data)

# --- External Data API ---
@app.route('/api/external/weather')
def get_weather():
    """天気予報APIエンドポイント"""
    if not external_data_service:
        return jsonify({'error': 'External data service not available'}), 503
    
    import asyncio
    area_code = request.args.get('area', '130000')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(external_data_service.get_weather_forecast(area_code))
        return jsonify(result)
    finally:
        loop.close()

@app.route('/api/external/trains')
def get_trains():
    """電車運行情報APIエンドポイント"""
    if not external_data_service:
        return jsonify({'error': 'External data service not available'}), 503
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(external_data_service.get_train_status())
        return jsonify(result)
    finally:
        loop.close()

@app.route('/api/external/alerts')
def get_alerts():
    """災害情報APIエンドポイント"""
    if not external_data_service:
        return jsonify({'error': 'External data service not available'}), 503
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(external_data_service.get_disaster_alerts())
        return jsonify(result)
    finally:
        loop.close()

# --- 新規追加: プロフィールAPI ---
@app.route('/api/profile/<int:user_id>')
def get_profile(user_id):
    """プロフィール情報取得"""
    try:
        from services.profile_manager import ProfileManager
        db = get_db()
        profile_manager = ProfileManager(db, app.root_path)
        profile = profile_manager.get_profile(user_id)
        
        if profile:
            return jsonify({'success': True, 'profile': profile})
        else:
            return jsonify({'success': False, 'message': 'ユーザーが見つかりません'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    """プロフィール情報更新"""
    try:
        from services.profile_manager import ProfileManager
        db = get_db()
        profile_manager = ProfileManager(db, app.root_path)
        data = request.json
        profile = profile_manager.update_profile(user_id, data)
        
        return jsonify({'success': True, 'profile': profile})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/profile/<int:user_id>/avatar', methods=['POST'])
def upload_avatar(user_id):
    """アバター画像アップロード"""
    try:
        from services.profile_manager import ProfileManager
        db = get_db()
        profile_manager = ProfileManager(db, app.root_path)
        
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': '画像がありません'}), 400
        
        image_file = request.files['image']
        filename = profile_manager.update_profile_image(user_id, image_file)
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/profile/<int:user_id>/cover', methods=['POST'])
def upload_cover(user_id):
    """カバー画像アップロード"""
    try:
        from services.profile_manager import ProfileManager
        db = get_db()
        profile_manager = ProfileManager(db, app.root_path)
        
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': '画像がありません'}), 400
        
        image_file = request.files['image']
        filename = profile_manager.update_background_image(user_id, image_file)
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/profile/<int:user_id>/stats')
def get_profile_stats(user_id):
    """プロフィール統計情報取得"""
    try:
        db = get_db()
        
        # 友達数を取得
        cursor = db.execute("SELECT COUNT(*) as count FROM friends WHERE user_id = ? AND status = 'friend'", (user_id,))
        friend_count = cursor.fetchone()['count']
        
        # グループ数を取得
        cursor = db.execute("SELECT COUNT(*) as count FROM room_members WHERE user_id = ?", (user_id,))
        room_count = cursor.fetchone()['count']
        
        return jsonify({
            'success': True,
            'stats': {
                'friends': friend_count,
                'rooms': room_count
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/profile/<int:user_id>/privacy')
def get_privacy_settings(user_id):
    """プライバシー設定取得"""
    try:
        from services.profile_manager import ProfileManager
        db = get_db()
        profile_manager = ProfileManager(db, app.root_path)
        settings = profile_manager.get_privacy_settings(user_id)
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/profile/<int:user_id>/privacy', methods=['PUT'])
def update_privacy_settings(user_id):
    """プライバシー設定更新"""
    try:
        from services.profile_manager import ProfileManager
        db = get_db()
        profile_manager = ProfileManager(db, app.root_path)
        data = request.json
        settings = profile_manager.update_privacy_settings(user_id, data)
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stamps')
def get_stamps():
    """スタンプ一覧取得"""
    try:
        from services.stamp_manager import StampManager
        db = get_db()
        stamp_manager = StampManager(db, app.root_path)
        
        category = request.args.get('category')
        tag = request.args.get('tag')
        
        stamps = stamp_manager.get_stamps(category, tag)
        categories = stamp_manager.get_categories()
        
        return jsonify({
            'success': True,
            'stamps': stamps,
            'categories': categories
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Gmail/YouTube API統合
@app.route('/api/gmail/messages')
def gmail_messages():
    """Gmail メッセージ取得（シミュレーション）"""
    # 実際のGmail API実装はGoogle OAuth2認証が必要
    # ここでは動作確認用のシミュレーションデータを返す
    return jsonify({
        'messages': [
            {'id': '1', 'subject': 'サンプルメール1', 'from': 'example@gmail.com'},
            {'id': '2', 'subject': 'サンプルメール2', 'from': 'test@gmail.com'}
        ]
    })

@app.route('/api/youtube/search')
def youtube_search():
    """YouTube検索（シミュレーション）"""
    query = request.args.get('q', '')
    # 実際のYouTube API実装はAPIキーが必要
    # ここでは動作確認用のシミュレーションデータを返す
    return jsonify({
        'items': [
            {
                'id': {'videoId': '1'},
                'snippet': {
                    'title': f'{query}に関するサンプル動画1',
                    'channelTitle': 'Sample Channel'
                }
            },
            {
                'id': {'videoId': '2'},
                'snippet': {
                    'title': f'{query}に関するサンプル動画2',
                    'channelTitle': 'Test Channel'
                }
            }
        ]
    })

@app.route('/auth/google')
def google_auth():
    """Google認証リダイレクト"""
    # 実際のOAuth2フローの実装
    # ここでは簡易版として、認証済みとしてリダイレクト
    return redirect(url_for('features'))

# チャットルーム画面
@app.route('/chat')
def chat_room():
    """チャットルーム画面"""
    return render_template('chat_room.html')

# プロフィール画面
@app.route('/profile')
def profile():
    """プロフィール画面"""
    return render_template('profile.html')

# --- SocketIOハンドラー追加 ---
@socketio.on('join_room')
def handle_join_room(data):
    """ルーム参加"""
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    
    join_room(room_id)
    emit('user_joined', {'user_id': user_id, 'room_id': room_id}, room=room_id)

@socketio.on('send_message')
def handle_send_message(data):
    """メッセージ送信"""
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    content = data.get('content')
    message_type = data.get('message_type', 'text')
    
    # データベースに保存
    db = get_db()
    cursor = db.execute(
        'INSERT INTO messages (room_id, user_id, content, message_type) VALUES (?, ?, ?, ?)',
        (room_id, user_id, content, message_type)
    )
    db.commit()
    
    # 全員にブロードキャスト
    emit('new_message', {
        'id': cursor.lastrowid,
        'room_id': room_id,
        'user_id': user_id,
        'content': content,
        'message_type': message_type,
        'timestamp': datetime.now().isoformat()
    }, room=room_id)

@socketio.on('typing')
def handle_typing(data):
    """タイピング通知"""
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    
    emit('typing', {'user_id': user_id}, room=room_id, include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    """タイピング停止通知"""
    room_id = data.get('room_id')
    
    emit('stop_typing', {}, room=room_id, include_self=False)

if __name__ == '__main__':
    import sys
    # support a simple test mode to verify server-side file saving without modifying DB
    test_mode = (len(sys.argv) > 1 and sys.argv[1] == 'test-save-file') or os.environ.get('TEST_SAVE_FILE') == '1'
    if test_mode:
        # a tiny 1x1 PNG (transparent) as DataURL
        dataurl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
        original_filename = 'test.png'
        unique_suffix = uuid.uuid4().hex[:8]
        filename = f"{os.path.splitext(original_filename)[0]}_{unique_suffix}{os.path.splitext(original_filename)[1]}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            # decode and write
            data_bytes = base64.b64decode(dataurl.split('base64,', 1)[1])
            with open(filepath, 'wb') as f:
                f.write(data_bytes)
            print(f"Test file saved to: {filepath}")
            sys.exit(0)
        except Exception as e:
            print(f"Test save failed: {e}")
            sys.exit(2)
    else:
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        # Ensure DB is initialized (create tables) if missing
        with app.app_context():
            try:
                db = get_db()
                db.execute("SELECT 1 FROM messages LIMIT 1").fetchone()
            except sqlite3.OperationalError:
                print("Database not initialized. Running init_db() to create tables from data.sql...")
                init_db()
        # disable reloader here to avoid double-start issues
        socketio.run(app, debug=True, use_reloader=False)