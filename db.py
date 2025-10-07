import sqlite3
DATABASE = 'abc.db'
ADMIN_USERNAME = 'skytomo124'

def get_db_connection():
	"""データベース接続を取得する（タイムアウト10分）"""
	conn = sqlite3.connect(DATABASE, timeout=600)
	conn.row_factory = sqlite3.Row
	return conn

def init_db():
	"""データベースを初期化する (abc.sqlを実行)"""
	conn = get_db_connection()
	with open('abc.sql', 'r', encoding='utf-8') as f:
		conn.executescript(f.read())
	try:
		conn.execute('SELECT password FROM users LIMIT 1')
	except sqlite3.OperationalError:
		conn.execute('ALTER TABLE users ADD COLUMN password TEXT NOT NULL DEFAULT ""')
		print("passwordカラムを既存のusersテーブルに追加しました。")
	conn.close()
	print("データベースが初期化されました。")

def get_leaderboard_data(user_id=None):
	"""ランキング上位5名と指定ユーザーの順位を取得する（管理者除外）"""
	conn = get_db_connection()
	leaderboard = conn.execute(
		'SELECT username, balance FROM users WHERE username != ? ORDER BY balance DESC, registered_at ASC',
		(ADMIN_USERNAME,)
	).fetchall()
	leaderboard = [row for row in leaderboard if row['username'] != ADMIN_USERNAME][:5]
	my_rank = None
	if user_id:
		# 管理者はランキング対象外
		user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
		if user and user['username'] == ADMIN_USERNAME:
			my_rank = None
		else:
			# 管理者以外のユーザーの中で順位を計算
			user_balance = conn.execute('SELECT balance FROM users WHERE id = ? AND username != ?', (user_id, ADMIN_USERNAME)).fetchone()
			if user_balance:
				higher_count = conn.execute('SELECT COUNT(*) FROM users WHERE balance > ? AND username != ?', (user_balance['balance'], ADMIN_USERNAME)).fetchone()[0]
				my_rank = higher_count + 1
			else:
				my_rank = None
	conn.close()
	return leaderboard, my_rank
