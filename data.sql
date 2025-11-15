-- 既存のテーブルがあれば、依存関係を考慮して削除します。
-- 'unread_messages'は'messages'に依存しているため、先に削除します。
DROP TABLE IF EXISTS unread_messages;
DROP TABLE IF EXISTS messages;

-- チャットメッセージ本体を保存するためのテーブルを作成します。
CREATE TABLE messages (
  -- id: 各メッセージを一意に識別するための番号です。自動的に1ずつ増えます。(PRIMARY KEY)
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  
  -- room: このメッセージが属する会話ルームの名前です。
  -- グループチャットの場合は'__group__', 個人チャットの場合は'dm_ユーザーA_ユーザーB'のような形式になります。
  -- 空であってはいけません (NOT NULL)。
  room TEXT NOT NULL,
  
  -- username: メッセージを送信したユーザーの名前です。空であってはいけません (NOT NULL)。
  username TEXT NOT NULL,
  
  -- message: 送信されたテキストメッセージの内容です。ファイルが送信された場合は空 (NULL) になります。
  message TEXT,
  
  -- file_path: 送信されたファイルの名前です。(例: 'photo.jpg') テキストメッセージの場合は空 (NULL) です。
  file_path TEXT,
  
  -- file_type: ファイルの種類 ('image', 'video', 'pdf'など) です。テキストメッセージの場合は空 (NULL) です。
  file_type TEXT,
  
  -- timestamp: メッセージがデータベースに保存された日時です。データが追加された時点の現在時刻(UTC)が自動的に入ります。
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- どのユーザーがどのメッセージを読んでいないかを管理するためのテーブルを作成します。
CREATE TABLE unread_messages (
  -- user_username: メッセージをまだ読んでいないユーザーの名前です。
  user_username TEXT NOT NULL,
  
  -- message_id: まだ読んでいないメッセージのIDです。'messages'テーブルの'id'と対応します。
  message_id INTEGER NOT NULL,
  
  -- 複合主キー: 同じユーザーが同じメッセージを複数回「未読」として記録することはないため、
  -- この2つのカラムの組み合わせがユニークであることを保証します。
  PRIMARY KEY (user_username, message_id),
  
  -- 外部キー制約: 'message_id'は必ず'messages'テーブルの'id'に存在する値でなければなりません。
  -- また、'messages'テーブルからあるメッセージが削除された場合(ON DELETE CASCADE)、
  -- このテーブルにある関連する未読情報も自動的に削除されます。
  FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
);