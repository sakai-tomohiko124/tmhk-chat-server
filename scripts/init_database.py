#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース初期化スクリプト
既存のchat.dbをバックアップして新しいスキーマで再作成します
"""

import sqlite3
import os
import shutil
from datetime import datetime

DB_FILE = 'chat.db'
SCHEMA_FILE = 'data_new.sql'
BACKUP_DIR = 'backup'

def main():
    print("=" * 50)
    print("データベース初期化スクリプト")
    print("=" * 50)
    
    # バックアップディレクトリを作成
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"✓ バックアップディレクトリを作成: {BACKUP_DIR}")
    
    # 既存のDBをバックアップ
    if os.path.exists(DB_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_DIR, f'chat_db_backup_{timestamp}.db')
        shutil.copy2(DB_FILE, backup_file)
        print(f"✓ 既存データベースをバックアップ: {backup_file}")
        
        # 古いDBを削除
        os.remove(DB_FILE)
        print(f"✓ 古いデータベースを削除: {DB_FILE}")
    else:
        print(f"ℹ 既存のデータベースが見つかりません。新規作成します。")
    
    # スキーマファイルを読み込み
    if not os.path.exists(SCHEMA_FILE):
        print(f"✗ エラー: スキーマファイルが見つかりません: {SCHEMA_FILE}")
        return
    
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # 新しいDBを作成
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print(f"✓ 新しいデータベースを作成: {DB_FILE}")
        
        # 作成されたテーブルを確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ 作成されたテーブル: {', '.join(tables)}")
        
        # 管理者アカウントを確認
        cursor.execute("SELECT username, is_admin FROM users WHERE is_admin = 1")
        admin = cursor.fetchone()
        if admin:
            print(f"✓ 管理者アカウント: {admin[0]}")
        
        print("\n" + "=" * 50)
        print("データベースの初期化が完了しました！")
        print("=" * 50)
        print("\n管理者ログイン情報:")
        print("  ユーザー名: ともひこ")
        print("  パスワード: skytomo124")
        print("\n※ この情報は安全に保管してください。")
        
    except Exception as e:
        print(f"✗ エラー: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
