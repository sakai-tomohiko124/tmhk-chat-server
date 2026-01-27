#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RPG風脱出ゲーム - メインアプリケーション
古代神殿からの脱出をテーマにした謎解きゲーム
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# データベースパス
DB_PATH = 'game.db'

# ================================================================================
# データベースヘルパー関数
# ================================================================================

def get_db():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    """データベースクエリを実行"""
    conn = get_db()
    cursor = conn.execute(query, args)
    rv = cursor.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """データベース更新を実行"""
    conn = get_db()
    cursor = conn.execute(query, args)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

# ================================================================================
# 認証デコレーター
# ================================================================================

def login_required(f):
    """ログインが必要なページを保護"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'player_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ================================================================================
# ルート: トップページとログイン
# ================================================================================

@app.route('/')
def index():
    """トップページ（ランディング）"""
    if 'player_id' in session:
        return redirect(url_for('game_intro'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン・新規登録"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        is_register = data.get('register', False)
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'ユーザー名とパスワードを入力してください'})
        
        if is_register:
            # 新規登録
            existing = query_db('SELECT id FROM players WHERE username = ?', [username], one=True)
            if existing:
                return jsonify({'success': False, 'message': 'このユーザー名は既に使用されています'})
            
            password_hash = generate_password_hash(password)
            player_id = execute_db(
                'INSERT INTO players (username, password_hash) VALUES (?, ?)',
                [username, password_hash]
            )
            
            # 初期進行状況を作成
            for stage_id in range(1, 5):
                execute_db(
                    'INSERT INTO game_progress (player_id, stage_id) VALUES (?, ?)',
                    [player_id, stage_id]
                )
            
            session['player_id'] = player_id
            session['username'] = username
            return jsonify({'success': True, 'message': '登録完了！冒険を始めましょう'})
        else:
            # ログイン
            player = query_db('SELECT * FROM players WHERE username = ?', [username], one=True)
            if not player:
                return jsonify({'success': False, 'message': 'ユーザーが見つかりません'})
            
            if not check_password_hash(player['password_hash'], password):
                return jsonify({'success': False, 'message': 'パスワードが違います'})
            
            # ログイン成功
            execute_db('UPDATE players SET last_login = ? WHERE id = ?', 
                      [datetime.now(), player['id']])
            
            session['player_id'] = player['id']
            session['username'] = player['username']
            return jsonify({'success': True, 'message': 'ログイン成功'})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """ログアウト"""
    session.clear()
    return redirect(url_for('index'))

# ================================================================================
# ルート: ゲーム画面
# ================================================================================

@app.route('/intro')
@login_required
def game_intro():
    """イントロダクション画面"""
    player = query_db('SELECT * FROM players WHERE id = ?', [session['player_id']], one=True)
    return render_template('game_intro.html', player=dict(player))

@app.route('/game')
@login_required
def game():
    """メインゲーム画面"""
    player = query_db('SELECT * FROM players WHERE id = ?', [session['player_id']], one=True)
    return render_template('game.html', player=dict(player))

@app.route('/game/complete')
@login_required
def game_complete():
    """ゲームクリア画面"""
    player = query_db('SELECT * FROM players WHERE id = ?', [session['player_id']], one=True)
    return render_template('game_complete.html', player=dict(player))

# ================================================================================
# API: プレイヤー情報
# ================================================================================

@app.route('/api/player/status')
@login_required
def get_player_status():
    """プレイヤーステータスを取得"""
    player = query_db('SELECT * FROM players WHERE id = ?', [session['player_id']], one=True)
    if not player:
        return jsonify({'success': False, 'message': 'プレイヤーが見つかりません'})
    
    return jsonify({
        'success': True,
        'player': {
            'id': player['id'],
            'username': player['username'],
            'current_stage': player['current_stage'],
            'hp': player['hp'],
            'intelligence': player['intelligence'],
            'experience': player['experience']
        }
    })

@app.route('/api/player/inventory')
@login_required
def get_inventory():
    """インベントリを取得"""
    items = query_db(
        'SELECT * FROM inventory WHERE player_id = ? ORDER BY acquired_at DESC',
        [session['player_id']]
    )
    
    return jsonify({
        'success': True,
        'items': [dict(item) for item in items]
    })

# ================================================================================
# API: ゲーム進行
# ================================================================================

@app.route('/api/game/progress')
@login_required
def get_game_progress():
    """ゲーム進行状況を取得"""
    progress = query_db(
        '''SELECT gp.*, s.name, s.title, s.description, s.puzzle_type, s.difficulty
           FROM game_progress gp
           JOIN stages s ON gp.stage_id = s.id
           WHERE gp.player_id = ?
           ORDER BY s.id''',
        [session['player_id']]
    )
    
    return jsonify({
        'success': True,
        'progress': [dict(p) for p in progress]
    })

@app.route('/api/game/stage/<int:stage_id>')
@login_required
def get_stage_info(stage_id):
    """ステージ情報を取得"""
    stage = query_db('SELECT * FROM stages WHERE id = ?', [stage_id], one=True)
    if not stage:
        return jsonify({'success': False, 'message': 'ステージが見つかりません'})
    
    progress = query_db(
        'SELECT * FROM game_progress WHERE player_id = ? AND stage_id = ?',
        [session['player_id'], stage_id], one=True
    )
    
    return jsonify({
        'success': True,
        'stage': dict(stage),
        'progress': dict(progress) if progress else None
    })

# ================================================================================
# API: 謎解き判定
# ================================================================================

# 各ステージの正解
PUZZLE_ANSWERS = {
    1: 'ひかり',  # ステージ1: 古代文字解読
    2: ['赤', '青', '緑', '黄'],  # ステージ2: 本の順序
    3: '7392',  # ステージ3: 数字パズル
    4: 'えいえんのひかり'  # ステージ4: 最終問題
}

@app.route('/api/puzzle/submit', methods=['POST'])
@login_required
def submit_puzzle_answer():
    """謎解きの答えを提出"""
    data = request.get_json()
    stage_id = data.get('stage_id')
    answer = data.get('answer')
    
    if not stage_id or answer is None:
        return jsonify({'success': False, 'message': '入力が不正です'})
    
    # プレイヤーの現在のステージを確認
    player = query_db('SELECT current_stage FROM players WHERE id = ?', 
                      [session['player_id']], one=True)
    
    if stage_id > player['current_stage']:
        return jsonify({'success': False, 'message': 'まだこのステージには進めません'})
    
    # 試行回数を増やす
    execute_db(
        'UPDATE game_progress SET attempts = attempts + 1 WHERE player_id = ? AND stage_id = ?',
        [session['player_id'], stage_id]
    )
    
    # 答えを判定
    correct_answer = PUZZLE_ANSWERS.get(stage_id)
    is_correct = False
    
    if isinstance(correct_answer, list):
        # リスト形式の答え（順序問題）
        if isinstance(answer, list):
            is_correct = answer == correct_answer
        else:
            is_correct = False
    else:
        # 文字列の答え
        is_correct = str(answer).strip() == str(correct_answer)
    
    if is_correct:
        # 正解処理
        execute_db(
            '''UPDATE game_progress 
               SET completed = TRUE, completed_at = ? 
               WHERE player_id = ? AND stage_id = ?''',
            [datetime.now(), session['player_id'], stage_id]
        )
        
        # プレイヤーのステージを進める
        if stage_id == player['current_stage'] and stage_id < 4:
            execute_db(
                'UPDATE players SET current_stage = ?, experience = experience + ? WHERE id = ?',
                [stage_id + 1, stage_id * 10, session['player_id']]
            )
        
        # ステージクリア報酬アイテムを付与
        item = query_db('SELECT * FROM items WHERE stage_reward = ?', [stage_id], one=True)
        if item:
            execute_db(
                'INSERT INTO inventory (player_id, item_name, item_description) VALUES (?, ?, ?)',
                [session['player_id'], item['name'], item['description']]
            )
        
        # 知力アップ（ステージ2のみ）
        if stage_id == 2:
            execute_db(
                'UPDATE players SET intelligence = intelligence + 5 WHERE id = ?',
                [session['player_id']]
            )
        
        return jsonify({
            'success': True,
            'correct': True,
            'message': '正解です！次のステージへ進めます',
            'reward': dict(item) if item else None
        })
    else:
        return jsonify({
            'success': True,
            'correct': False,
            'message': '不正解です。もう一度考えてみましょう'
        })

@app.route('/api/puzzle/hint/<int:stage_id>', methods=['POST'])
@login_required
def get_hint(stage_id):
    """ヒントを取得"""
    # ヒント使用回数を増やす
    execute_db(
        'UPDATE game_progress SET hints_used = hints_used + 1 WHERE player_id = ? AND stage_id = ?',
        [session['player_id'], stage_id]
    )
    
    # ステージ別のヒント
    hints = {
        1: {
            1: '壁の文字をよく見てください。太陽の方向が鍵です。',
            2: '最初の文字を読んでみましょう。',
            3: '「太陽が昇る方向」を意味する言葉です。'
        },
        2: {
            1: '本の背表紙に色が付いています。',
            2: '虹の色の順番を思い出してください。',
            3: '答え: 赤、青、緑、黄の順番です。'
        },
        3: {
            1: '部屋の四隅に数字のヒントがあります。',
            2: '各数字を足し算してみましょう。',
            3: '7 + 3 + 9 + 2 = 21、答えは7392です。'
        },
        4: {
            1: 'これまでの3つのステージの答えを組み合わせます。',
            2: '最初のステージの答えに注目してください。',
            3: '「ひかり」に「永遠の」を付けた言葉です。'
        }
    }
    
    # 現在の使用回数を取得
    progress = query_db(
        'SELECT hints_used FROM game_progress WHERE player_id = ? AND stage_id = ?',
        [session['player_id'], stage_id], one=True
    )
    
    hints_used = progress['hints_used'] if progress else 1
    hint_text = hints.get(stage_id, {}).get(hints_used, 'ヒントがありません')
    
    return jsonify({
        'success': True,
        'hint': hint_text,
        'hints_used': hints_used
    })

# ================================================================================
# API: セーブ・ロード
# ================================================================================

@app.route('/api/game/save', methods=['POST'])
@login_required
def save_game():
    """ゲームを保存（自動的にDBに保存されているので特別な処理は不要）"""
    return jsonify({
        'success': True,
        'message': 'ゲームが保存されました'
    })

# ================================================================================
# エラーハンドラー
# ================================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'サーバーエラーが発生しました'}), 500

# ================================================================================
# アプリケーション起動
# ================================================================================

if __name__ == '__main__':
    # データベースの存在確認
    if not os.path.exists(DB_PATH):
        print(f"警告: データベースが見つかりません: {DB_PATH}")
        print("init_game_db.py を実行してデータベースを作成してください")
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🎮 RPG脱出ゲームサーバー起動中...")
    print(f"   URL: http://localhost:{port}")
    print(f"   デバッグモード: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
