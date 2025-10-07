# メッセージ機能拡張スクリプト
# 編集・削除機能とより明確な既読表示を追加

import sqlite3

def upgrade_database():
    """データベースに新しいフィールドを追加"""
    conn = sqlite3.connect('abc.db')
    
    try:
        # is_editedフィールドを追加（編集されたメッセージかどうか）
        conn.execute('ALTER TABLE messages ADD COLUMN is_edited INTEGER NOT NULL DEFAULT 0')
        print("is_editedフィールドを追加しました")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("is_editedフィールドは既に存在します")
        else:
            print(f"Error adding is_edited: {e}")
    
    try:
        # is_deletedフィールドを追加（削除されたメッセージかどうか）
        conn.execute('ALTER TABLE messages ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0')
        print("is_deletedフィールドを追加しました")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("is_deletedフィールドは既に存在します")
        else:
            print(f"Error adding is_deleted: {e}")
    
    try:
        # admin_read_atフィールドを追加（管理者が既読した時刻）
        conn.execute('ALTER TABLE messages ADD COLUMN admin_read_at TIMESTAMP NULL')
        print("admin_read_atフィールドを追加しました")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("admin_read_atフィールドは既に存在します")
        else:
            print(f"Error adding admin_read_at: {e}")
    
    try:
        # user_read_atフィールドを追加（ユーザーが既読した時刻）
        conn.execute('ALTER TABLE messages ADD COLUMN user_read_at TIMESTAMP NULL')
        print("user_read_atフィールドを追加しました")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("user_read_atフィールドは既に存在します")
        else:
            print(f"Error adding user_read_at: {e}")
    
    conn.commit()
    conn.close()
    print("データベースの拡張が完了しました")

if __name__ == '__main__':
    upgrade_database()