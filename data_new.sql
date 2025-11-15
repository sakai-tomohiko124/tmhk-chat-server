-- 既存のテーブルを削除
DROP TABLE IF EXISTS unread_messages;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS follows;
DROP TABLE IF EXISTS ng_word_logs;
DROP TABLE IF EXISTS virus_logs;
DROP TABLE IF EXISTS security_logs;
DROP TABLE IF EXISTS money_transactions;
DROP TABLE IF EXISTS users;

-- ユーザーテーブル
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  is_admin INTEGER DEFAULT 0,
  is_active INTEGER DEFAULT 1,
  is_infected INTEGER DEFAULT 0,
  auto_login_token TEXT,
  balance INTEGER DEFAULT 20000,
  phone_number TEXT,
  email TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login DATETIME
);

-- 管理者アカウントを作成
INSERT INTO users (username, password, is_admin, is_active, balance) 
VALUES ('ともひこ', 'skytomo124', 1, 1, 999999999);

-- チャットメッセージテーブル
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT NOT NULL,
  username TEXT NOT NULL,
  message TEXT,
  file_path TEXT,
  file_type TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  safe INTEGER DEFAULT 1
);

-- 未読メッセージテーブル
CREATE TABLE unread_messages (
  user_username TEXT NOT NULL,
  message_id INTEGER NOT NULL,
  PRIMARY KEY (user_username, message_id),
  FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
);

-- フォロー関係テーブル
CREATE TABLE follows (
  follower TEXT NOT NULL,
  followee TEXT NOT NULL,
  PRIMARY KEY(follower, followee)
);

-- ウイルス感染ログテーブル
CREATE TABLE virus_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  username TEXT NOT NULL,
  infection_type TEXT NOT NULL,
  infected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  description TEXT,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 不正アクセスログテーブル
CREATE TABLE security_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  username TEXT,
  ip_address TEXT,
  action TEXT NOT NULL,
  attempt_count INTEGER DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- NGワード発言ログテーブル
CREATE TABLE ng_word_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  username TEXT NOT NULL,
  ng_word TEXT NOT NULL,
  message TEXT NOT NULL,
  detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 金額取引ログテーブル
CREATE TABLE money_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  username TEXT NOT NULL,
  amount INTEGER NOT NULL,
  transaction_type TEXT NOT NULL,
  description TEXT,
  balance_before INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- NGワードマスターテーブル
CREATE TABLE ng_words (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  word TEXT UNIQUE NOT NULL,
  severity INTEGER DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- デフォルトNGワードを追加
INSERT INTO ng_words (word, severity) VALUES 
('バカ', 1),
('アホ', 1),
('死ね', 3),
('殺す', 3),
('クソ', 2),
('fuck', 3),
('shit', 2),
('馬鹿', 1),
('阿呆', 1);

-- インデックスの作成
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_messages_username ON messages(username);
CREATE INDEX idx_virus_logs_user ON virus_logs(user_id);
CREATE INDEX idx_security_logs_user ON security_logs(user_id);
CREATE INDEX idx_ng_word_logs_user ON ng_word_logs(user_id);
CREATE INDEX idx_money_transactions_user ON money_transactions(user_id);
