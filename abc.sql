-- ユーザー情報を管理するテーブル
-- ユーザー名と招待コードは重複しないように UNIQUE 制約を付与
-- last_seen でオンライン状態を管理
-- balance は所持金（円）を表す
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL DEFAULT '',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    balance INTEGER NOT NULL DEFAULT 0,
    invite_code TEXT NOT NULL UNIQUE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO users (username, password, invite_code, balance) VALUES ('skytomo124', 'skytomo124', 'ADMINCODE', 99999999);
INSERT OR IGNORE INTO users (username, password, invite_code, balance) VALUES ('skytomo124', 'skytomo124', 'ADMINCODE', 99999999);
-- user_id に外部キー制約を設定し、usersテーブルの存在しないIDが登録されるのを防ぐ
CREATE TABLE IF NOT EXISTS user_agreements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    agreement_status TEXT NOT NULL,
    agreed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- チャットメッセージを保存するテーブル
-- sender_id: 送信者ID (0は管理者/システム)
-- receiver_id: 受信者ID (0は管理者/システム)
-- is_read: 従来の既読フラグ（互換性のため残す）
-- is_edited: メッセージが編集されたかどうか (0: 未編集, 1: 編集済み)
-- is_deleted: メッセージが削除されたかどうか (0: 存在, 1: 削除済み)
-- admin_read_at: 管理者が既読した時刻
-- user_read_at: ユーザーが既読した時刻
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER NOT NULL DEFAULT 0,
    is_edited INTEGER NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    admin_read_at TIMESTAMP NULL,
    user_read_at TIMESTAMP NULL
);

-- NGワード違反によるウイルス画面遷移ログ
CREATE TABLE IF NOT EXISTS virus_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 友達招待リンク管理テーブル
CREATE TABLE IF NOT EXISTS invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    used INTEGER DEFAULT 0
);

-- 管理者Keepメモ保存テーブル
CREATE TABLE IF NOT EXISTS admin_memo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);