from flask_socketio import emit, join_room, leave_room
from db import get_db_connection, get_leaderboard_data
from flask import session, request, url_for, flash
from datetime import datetime
import json
import os

from config import NG_WORDS
from helpers import is_valid_message_content

# NGワードリスト（分割管理）
NG_WORDS = [
	"やば","ザコ","くさ","AI","ひこ","ポテト","ねず","おかしい","うそ","大丈夫","？",
	"どうした","え？","は？","あっそ","ふーん","ふざ","でしょ","デッキブラシ","ブチコ","どっち","ん？",
	"すいません","とも","馬鹿", "アホ", "死ね", "殺す", "馬鹿野郎", "バカ","クソ", "糞", "ちくしょう",
	"畜生", "くたばれ", "うん","おかしい","ばか","学習"
]

# qa_data.jsonから管理者自動応答内容をロード
QA_DATA_PATH = os.path.join(os.path.dirname(__file__), 'qa_data.json')
with open(QA_DATA_PATH, encoding='utf-8') as f:
    QA_LIST = json.load(f)

# キーワード→応答辞書生成
ADMIN_AUTO_REPLY = {}
for qa in QA_LIST:
    for kw in qa['keywords']:
        ADMIN_AUTO_REPLY[kw] = qa['answer']

# 自動応答カスタマイズ用グローバル辞書
AUTO_REPLY_CONTENT = {
	'天気': None,  # Noneならscraping.pyのデフォルト
	'電車': None
}

# 管理者による自動応答キーワード追加
def add_auto_reply_keyword(keyword, content=None):
	AUTO_REPLY_CONTENT[keyword] = content

# 管理者による自動応答キーワード削除
def remove_auto_reply_keyword(keyword):
	if keyword in AUTO_REPLY_CONTENT:
		del AUTO_REPLY_CONTENT[keyword]



def register_socketio_events(socketio):
	# 管理者による自動応答キーワード追加
	@socketio.on('add_auto_reply_keyword')
	def handle_add_auto_reply_keyword(data):
		if not session.get('is_admin'):
			return
		keyword = data.get('keyword')
		content = data.get('content')
		if keyword and keyword not in AUTO_REPLY_CONTENT:
			add_auto_reply_keyword(keyword, content)
			emit('auto_reply_keyword_added', {'keyword': keyword, 'content': content})

	# 管理者による自動応答キーワード削除
	@socketio.on('remove_auto_reply_keyword')
	def handle_remove_auto_reply_keyword(data):
		if not session.get('is_admin'):
			return
		keyword = data.get('keyword')
		if keyword in AUTO_REPLY_CONTENT:
			remove_auto_reply_keyword(keyword)
			emit('auto_reply_keyword_removed', {'keyword': keyword})
	# 管理者による自動応答内容設定
	@socketio.on('set_auto_reply')
	def handle_set_auto_reply(data):
		if not session.get('is_admin'):
			return
		keyword = data.get('keyword')
		content = data.get('content')
		if keyword in AUTO_REPLY_CONTENT:
			AUTO_REPLY_CONTENT[keyword] = content
			emit('auto_reply_updated', {'keyword': keyword, 'content': content})
	# 管理者からのメッセージ送信
	@socketio.on('admin_send_message')
	def handle_admin_send_message(data):
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

	# 管理者チャット用メッセージ送信
	@socketio.on('admin_message')
	def handle_admin_message(data):
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
		conn = get_db_connection()
		conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (0, ?, ?)', (target_user_id, message_text))
		conn.commit()
		conn.close()
		# 管理者→ユーザー: ユーザーroomに送信
		socketio.emit('new_message', {
			'username': 'AI', 
			'message': message_text, 
			'timestamp': timestamp,
			'sender_id': 0
		}, room=target_user_id)
		# 管理者自身にも送信（管理者画面の即時反映）
		socketio.emit('new_message', {
			'username': 'AI', 
			'message': message_text, 
			'timestamp': timestamp,
			'sender_id': 0
		}, room='admin')

	# 管理者応答モード変更
	@socketio.on('toggle_admin_mode')
	def handle_admin_mode_change(data):
		global admin_auto_mode
		if not session.get('is_admin'):
			return
		admin_auto_mode = data['auto_mode']
		emit('mode_changed', {'auto_mode': admin_auto_mode})

	# 管理者による既読処理
	@socketio.on('mark_as_read')
	def handle_mark_as_read(data):
		if not session.get('is_admin'): return
		target_user_id = data['user_id']
		conn = get_db_connection()
		current_time = datetime.now().isoformat()
		conn.execute('UPDATE messages SET is_read = 1, admin_read_at = ? WHERE sender_id = ? AND receiver_id = 0 AND is_deleted = 0', 
					 (current_time, target_user_id))
		conn.commit()
		conn.close()
		emit('messages_read', {'user_id': target_user_id})
		socketio.emit('admin_read_notification', {'message': '管理者がメッセージを既読しました'}, room=target_user_id)

	# ユーザーによる自動既読処理
	@socketio.on('user_read_message')
	def handle_user_read_message(data):
		user_id = session.get('user_id')
		if not user_id:
			return
		current_time = datetime.now().isoformat()
		conn = get_db_connection()
		conn.execute('UPDATE messages SET user_read_at = ? WHERE sender_id = 0 AND receiver_id = ? AND user_read_at IS NULL AND is_deleted = 0', 
					 (current_time, user_id))
		conn.commit()
		conn.close()

	# メッセージ編集
	@socketio.on('edit_message')
	def handle_edit_message(data):
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
		from helpers import NG_WORDS
		if any(ng_word in new_content for ng_word in NG_WORDS):
			emit('message_error', {'error': 'NGワードが含まれています'})
			return
		conn = get_db_connection()
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
		edit_time = datetime.now().isoformat()
		conn.execute('UPDATE messages SET content = ?, is_edited = 1 WHERE id = ?', (new_content, message_id))
		conn.commit()
		conn.close()
		socketio.emit('message_edited', {
			'message_id': message_id,
			'new_content': new_content,
			'edited_at': edit_time
		})

	# メッセージ完全削除
	@socketio.on('delete_message')
	def handle_delete_message(data):
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
		conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
		conn.commit()
		conn.close()
		target_user_id = message['receiver_id'] if message['sender_id'] != 0 else message['sender_id']
		if target_user_id != 0:
			socketio.emit('message_completely_deleted', {'message_id': message_id}, room=target_user_id)
		socketio.emit('message_completely_deleted', {'message_id': message_id})
	# クライアント接続時
	@socketio.on('connect')
	def handle_connect(auth=None):
		user_id = session.get('user_id')
		is_admin = session.get('is_admin', False)
		print(f"DEBUG: Socket connect - user_id: {user_id}, is_admin: {is_admin}, session: {dict(session)}")
		if user_id is not None:
			join_room(user_id)
			print(f"DEBUG: User {user_id} joined room")
			if is_admin:
				join_room('admin')
				print(f"DEBUG: Admin joined admin room")
			else:
				# 一般ユーザーのオンライン状態管理
				from abcd import online_users
				online_users[user_id] = request.sid
				conn = get_db_connection()
				conn.execute('UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
				conn.commit()
				conn.close()
				socketio.emit('user_status_change', {'user_id': user_id, 'status': 'online', 'last_seen': datetime.now().isoformat()})

	# クライアント切断時
	@socketio.on('disconnect')
	def handle_disconnect(arg=None):
		user_id = session.get('user_id')
		is_admin = session.get('is_admin', False)
		if user_id is not None:
			if is_admin:
				leave_room('admin')
				print(f"DEBUG: Admin left admin room")
			else:
				from abcd import online_users
				if user_id in online_users:
					del online_users[user_id]
				last_seen_time = datetime.now().isoformat()
				conn = get_db_connection()
				conn.execute('UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
				conn.commit()
				conn.close()
				socketio.emit('user_status_change', {'user_id': user_id, 'status': 'offline', 'last_seen': last_seen_time})
			leave_room(user_id)

	# メッセージ送信
	@socketio.on('send_message')
	def handle_send_message(data):
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
		print(f"DEBUG: Message validation passed for: {message_text}")
		timestamp = datetime.now().isoformat()
		conn = get_db_connection()
		message_count = conn.execute('SELECT COUNT(*) as count FROM messages').fetchone()['count']
		if message_count >= 100:
			oldest_message = conn.execute('SELECT id FROM messages ORDER BY created_at ASC LIMIT 1').fetchone()
			if oldest_message:
				conn.execute('DELETE FROM messages WHERE id = ?', (oldest_message['id'],))
		conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, 0, ?)', (user_id, message_text))
		# NGワード判定
		from config import NG_WORDS
		from helpers import is_valid_message_content
		if any(ng_word in message_text for ng_word in NG_WORDS):
			conn.rollback()
			conn.close()
			emit('message_error', {'error': 'NGワードが含まれています'})
			return
		if not is_valid_message_content(message_text):
			conn.rollback()
			conn.close()
			emit('message_error', {'error': '不正な内容です'})
			return

		# 所持金チェック（通常送信:20円, 自動応答:10円）
		auto_reply = None
		for kw, reply in ADMIN_AUTO_REPLY.items():
			if kw in message_text:
				auto_reply = reply
				# break → ループ外で分岐
		if not is_admin:
			user = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
			# 自動応答の場合は10円、通常は20円
			deduction = 10 if auto_reply else 20
			if user and user['balance'] < deduction:
				conn.rollback()
				conn.close()
				emit('message_error', {'error': '所持金が足りません'})
				return
			conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (deduction, user_id))

		# 自動応答処理（管理者qa_data.json内容で返信）
		if auto_reply:
			conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (0, ?, ?)', (user_id, auto_reply))
			conn.commit()
			socketio.emit('new_message', {'username': 'AI', 'message': auto_reply, 'timestamp': datetime.now().isoformat()}, room=user_id)

		conn.commit()
		user = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone() if not is_admin else None
		conn.close()
		# ユーザー→管理者: 管理者roomに送信
		socketio.emit('new_message', {
			'username': username,
			'message': message_text,
			'timestamp': timestamp,
			'sender_id': user_id
		}, room='admin')
		# ユーザー自身にも送信（自分の画面の即時反映）
		socketio.emit('new_message', {
			'username': username,
			'message': message_text,
			'timestamp': timestamp,
			'sender_id': user_id
		}, room=user_id)
