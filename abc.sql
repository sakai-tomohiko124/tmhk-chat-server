-- ユーザー情報を管理するテーブル
-- ユーザー名と招待コードは重複しないように UNIQUE 制約を付与
-- last_seen でオンライン状態を管理
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL DEFAULT '',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    balance INTEGER NOT NULL DEFAULT 0,
    invite_code TEXT NOT NULL UNIQUE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 利用規約の同意状況を記録するテーブル
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
-- is_read: 管理者がメッセージを読んだかどうかの既読フラグ (0: 未読, 1: 既読)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER NOT NULL DEFAULT 0
);