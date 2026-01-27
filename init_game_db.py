#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RPG脱出ゲーム - データベース初期化スクリプト
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'game.db')

def init_database():
    """ゲーム用データベースを初期化"""
    
    # 既存のDBがあれば削除
    if os.path.exists(DB_PATH):
        print(f"既存のデータベースを削除: {DB_PATH}")
        os.remove(DB_PATH)
    
    print(f"新しいデータベースを作成: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # プレイヤーテーブル
    cursor.execute('''
    CREATE TABLE players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        current_stage INTEGER DEFAULT 1,
        hp INTEGER DEFAULT 100,
        intelligence INTEGER DEFAULT 10,
        experience INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # インベントリテーブル
    cursor.execute('''
    CREATE TABLE inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        item_description TEXT,
        acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
    )
    ''')
    
    # ゲーム進行状況テーブル
    cursor.execute('''
    CREATE TABLE game_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        stage_id INTEGER NOT NULL,
        completed BOOLEAN DEFAULT FALSE,
        completion_time INTEGER,
        attempts INTEGER DEFAULT 0,
        hints_used INTEGER DEFAULT 0,
        completed_at TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
        UNIQUE(player_id, stage_id)
    )
    ''')
    
    # ゲームステージ定義テーブル
    cursor.execute('''
    CREATE TABLE stages (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        puzzle_type TEXT NOT NULL,
        difficulty INTEGER DEFAULT 1
    )
    ''')
    
    # ステージデータを挿入
    stages_data = [
        (1, 'entrance_hall', 'エントランスホール', 
         '古代神殿の入り口。壁には謎の文字が刻まれている...', 'text_decode', 1),
        (2, 'library', '図書館', 
         '埃をかぶった本が並ぶ図書館。どこかに重要な手がかりが...', 'book_selection', 2),
        (3, 'treasury', '宝物庫', 
         '財宝が眠る部屋。しかし数字の鍵が必要だ...', 'number_puzzle', 3),
        (4, 'final_chamber', '最終の間', 
         'これまでの謎が全て繋がる場所。真実の扉がここにある...', 'combined_puzzle', 4)
    ]
    
    cursor.executemany(
        'INSERT INTO stages (id, name, title, description, puzzle_type, difficulty) VALUES (?, ?, ?, ?, ?, ?)',
        stages_data
    )
    
    # アイテム定義テーブル
    cursor.execute('''
    CREATE TABLE items (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL,
        item_type TEXT NOT NULL,
        stage_reward INTEGER
    )
    ''')
    
    # アイテムデータを挿入
    items_data = [
        (1, '古代の碑文', '謎の文字が刻まれた石板。解読のヒントになるかもしれない。', 'key_item', 1),
        (2, '古代の地図', '神殿の構造が描かれた古い地図。', 'key_item', 2),
        (3, '賢者の書', '知識を高める古代の書物。知力+5', 'power_up', 2),
        (4, '宝石の鍵', '最終の扉を開くための宝石がはめ込まれた鍵。', 'key_item', 3),
        (5, '回復の薬', 'HPを50回復する。', 'consumable', None)
    ]
    
    cursor.executemany(
        'INSERT INTO items (id, name, description, item_type, stage_reward) VALUES (?, ?, ?, ?, ?)',
        items_data
    )
    
    conn.commit()
    conn.close()
    
    print("✓ データベースの初期化が完了しました")
    print(f"  - players テーブル作成")
    print(f"  - inventory テーブル作成")
    print(f"  - game_progress テーブル作成")
    print(f"  - stages テーブル作成 (4ステージ)")
    print(f"  - items テーブル作成 (5アイテム)")

if __name__ == '__main__':
    init_database()
