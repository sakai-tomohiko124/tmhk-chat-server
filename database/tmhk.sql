-- users テーブル: ユーザー情報を格納
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    profile_image TEXT DEFAULT 'default_avatar.png',
    background_image TEXT DEFAULT 'default_bg.png',
    status_message TEXT DEFAULT 'はじめまして！',
    bio TEXT,
    birthday DATE,
    account_type TEXT DEFAULT 'private',
    show_typing INTEGER DEFAULT 1,
    show_online_status INTEGER DEFAULT 1,
    UNIQUE(username),
    UNIQUE(email, account_type)
);

-- custom_friend_lists テーブル: ユーザーが作成するカスタム友達リスト
CREATE TABLE IF NOT EXISTS custom_friend_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    list_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- custom_list_members テーブル: カスタムリストに所属する友達
CREATE TABLE IF NOT EXISTS custom_list_members (
    list_id INTEGER NOT NULL,
    friend_id INTEGER NOT NULL,
    PRIMARY KEY (list_id, friend_id),
    FOREIGN KEY (list_id) REFERENCES custom_friend_lists(id) ON DELETE CASCADE,
    FOREIGN KEY (friend_id) REFERENCES users(id)
);

-- messages テーブル: グループチャットのメッセージ
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reactions TEXT, -- JSON形式
    is_deleted INTEGER DEFAULT 0,
    updated_at TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);


-- private_messages テーブル (1対1チャット、キープメモ、AIチャット用)
CREATE TABLE private_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text', -- 'text', 'voice', 'image'などを格納
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_from_ai INTEGER DEFAULT 0,
    is_read INTEGER DEFAULT 0,
    is_deleted BOOLEAN DEFAULT 0,
    updated_at DATETIME,
    reactions TEXT,
    FOREIGN KEY (sender_id) REFERENCES users (id),
    FOREIGN KEY (recipient_id) REFERENCES users (id)
);



-- blocked_users テーブル: ユーザーがブロックした相手
CREATE TABLE IF NOT EXISTS blocked_users (
    user_id INTEGER NOT NULL,
    blocked_user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, blocked_user_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (blocked_user_id) REFERENCES users(id)
);

-- hidden_users テーブル: ユーザーが非表示にした相手
CREATE TABLE IF NOT EXISTS hidden_users (
    user_id INTEGER NOT NULL,
    hidden_user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, hidden_user_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (hidden_user_id) REFERENCES users(id)
);

-- auto_replies テーブル: 自動応答メッセージ
CREATE TABLE IF NOT EXISTS auto_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    response_message TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- canned_messages テーブル: 定型文
CREATE TABLE IF NOT EXISTS canned_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ai_knowledge_base テーブル: AIの学習内容
CREATE TABLE IF NOT EXISTS ai_knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, -- 0の場合はグローバルな知識
    keyword TEXT NOT NULL,
    fact TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- friends テーブル: 友達関係
CREATE TABLE IF NOT EXISTS friends (
    user_id INTEGER NOT NULL,
    friend_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    is_notification_off INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, friend_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (friend_id) REFERENCES users (id)
);

-- rooms テーブル: グループチャットのルーム情報
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    creator_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users (id)
);

-- room_members テーブル: グループチャットの参加メンバー
CREATE TABLE IF NOT EXISTS room_members (
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (room_id, user_id),
    FOREIGN KEY (room_id) REFERENCES rooms (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- blocked_notifications テーブル: （機能詳細不明）
CREATE TABLE IF NOT EXISTS blocked_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocker_id INTEGER NOT NULL,
    blocked_id INTEGER NOT NULL,
    notify_at TIMESTAMP NOT NULL,
    is_notified INTEGER DEFAULT 0,
    FOREIGN KEY (blocker_id) REFERENCES users (id),
    FOREIGN KEY (blocked_id) REFERENCES users (id)
);

-- invitation_tokens テーブル: 友達招待用トークン
CREATE TABLE IF NOT EXISTS invitation_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- violation_reports テーブル: 違反報告
CREATE TABLE IF NOT EXISTS violation_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL,
    violator_id INTEGER NOT NULL,
    message_content TEXT NOT NULL,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (violator_id) REFERENCES users (id)
);

-- announcements テーブル: 運営からのお知らせ
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- surveys テーブル: アンケート
CREATE TABLE IF NOT EXISTS surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- survey_questions テーブル: アンケートの質問
CREATE TABLE IF NOT EXISTS survey_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,
    FOREIGN KEY (survey_id) REFERENCES surveys (id)
);

-- survey_options テーブル: アンケートの選択肢
CREATE TABLE IF NOT EXISTS survey_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES survey_questions (id)
);

-- survey_responses テーブル: アンケートの回答
CREATE TABLE IF NOT EXISTS survey_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    survey_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    option_id INTEGER,
    response_text TEXT,
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (survey_id) REFERENCES surveys (id),
    FOREIGN KEY (question_id) REFERENCES survey_questions (id),
    FOREIGN KEY (option_id) REFERENCES survey_options (id)
);

-- timeline_posts テーブル: タイムラインへの投稿
CREATE TABLE IF NOT EXISTS timeline_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    media_url TEXT,
    post_type TEXT DEFAULT 'text',
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- weather_data, traffic_data, disaster_data: 外部情報
CREATE TABLE IF NOT EXISTS weather_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    data TEXT,
    timestamp TIMESTAMP
);
CREATE TABLE IF NOT EXISTS traffic_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    timestamp TIMESTAMP
);
CREATE TABLE IF NOT EXISTS disaster_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    timestamp TIMESTAMP
);

-- game_scores テーブル: ミニゲームのスコア
CREATE TABLE IF NOT EXISTS game_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_type TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- stamps, user_stamps: スタンプ機能
CREATE TABLE IF NOT EXISTS stamps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    image_url TEXT NOT NULL,
    category TEXT,
    is_free INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS user_stamps (
    user_id INTEGER NOT NULL,
    stamp_id INTEGER NOT NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, stamp_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (stamp_id) REFERENCES stamps (id)
);

-- custom_themes テーブル: カスタムテーマ
CREATE TABLE IF NOT EXISTS custom_themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    css_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- login_streaks テーブル: 連続ログイン記録
CREATE TABLE IF NOT EXISTS login_streaks (
    user_id INTEGER PRIMARY KEY,
    current_streak INTEGER DEFAULT 0,
    max_streak INTEGER DEFAULT 0,
    last_login_date DATE,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- missions, user_missions: デイリーミッション
CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    reward_points INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS user_missions (
    user_id INTEGER NOT NULL,
    mission_id INTEGER NOT NULL,
    completed INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, mission_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (mission_id) REFERENCES missions (id)
);

-- activity_feed テーブル: ユーザーアクティビティ
CREATE TABLE IF NOT EXISTS activity_feed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    activity_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 実績関連テーブル
CREATE TABLE IF NOT EXISTS achievement_criteria (
    achievement_name TEXT PRIMARY KEY,
    criteria_description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_name TEXT NOT NULL,
    description TEXT,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (achievement_name) REFERENCES achievement_criteria(achievement_name)
);
CREATE TABLE IF NOT EXISTS user_achievement_progress (
    user_id INTEGER NOT NULL,
    achievement_name TEXT NOT NULL,
    progress INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_name),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (achievement_name) REFERENCES achievement_criteria(achievement_name)
);

-- user_youtube_links テーブル: プロフィールに表示するYouTubeリンク
CREATE TABLE IF NOT EXISTS user_youtube_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- saved_games, saved_game_players: 中断したゲームの状態
CREATE TABLE IF NOT EXISTS saved_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL UNIQUE,
    game_type TEXT NOT NULL,
    game_state TEXT NOT NULL, -- JSON形式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS saved_game_players (
    game_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, user_id),
    FOREIGN KEY (game_id) REFERENCES saved_games (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

UPDATE users SET is_admin = 1 WHERE email = 'skytomohiko17@gmail.com';