#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TMHKchat - 究極完全版 server.py

# --- ライブラリのインポート ---
import os
import sqlite3
import uuid
import json
import random
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import time
import requests
from bs4 import BeautifulSoup
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import base64
import io
from PIL import Image
from urllib.parse import urlparse

# nl2brフィルタのためにMarkupとescapeをインポート
from markupsafe import escape, Markup

import google.generativeai as genai
from dotenv import load_dotenv
from flask import (Flask, flash, g, redirect, render_template_string, request,
                   url_for, jsonify, send_from_directory, session, send_file)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# --- アプリケーション設定 ---
# .envファイルから環境変数を読み込む
load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Jinja2カスタムフィルタの定義 ---
def nl2br(value):
    """改行文字をHTMLの<br>タグに変換するカスタムフィルタ"""
    if value is None:
        return ''
    escaped_value = escape(value)
    return Markup(escaped_value.replace('\n', '<br>\n'))

app.jinja_env.filters['nl2br'] = nl2br

# --- 各種設定 ---
# 環境変数からSECRET_KEYを読み込む、設定されていなければデフォルト値を使用
SECRET_KEY = os.getenv('SECRET_KEY', 'aK4$d!sF9@gH2%jLpQ7rT1&uY5vW8xZc')
app.config['SECRET_KEY'] = SECRET_KEY

# その他の設定
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
DATABASE = os.path.join(app.root_path, 'database', 'hkchat.db') # データベースファイル名変更 (tmchat -> hkchat)

# 画像アップロード設定
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'assets', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# UPLOAD_FOLDERが存在しない場合に作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'profile_images'), exist_ok=True) # プロフィール画像専用フォルダ
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'zip', 'mp4', 'mp3', 'wav', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

# Google AI APIキー設定
GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')
if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)
    # AIモデルの初期化 (Gemini-Proを使用)
    ai_model = genai.GenerativeModel('gemini-pro')
else:
    ai_model = None
    print("Warning: GOOGLE_AI_API_KEY is not set. AI features will be limited.")

# YouTube APIキー設定
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# 管理者アカウント情報
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'skytomohiko17@gmail.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'skytomo124')

# 定数
FORBIDDEN_WORDS = ["馬鹿", "アホ", "死ね", "バカ", "終わり","やばい","マジ","クソ","しね","消えろ","クズ","不適切ワード"]

# アカウントタイプの定義
ACCOUNT_TYPES = {
    'work': {'name': '職場', 'theme': 'professional', 'bg_gradient': 'linear-gradient(135deg, #1e3a8a, #3b82f6)'},
    'home': {'name': '家庭', 'theme': 'warm', 'bg_gradient': 'linear-gradient(135deg, #f97316, #fbbf24)'},
    'private': {'name': 'プライベート', 'theme': 'casual', 'bg_gradient': 'linear-gradient(135deg, #10b981, #34d399)'}
}

# Flask-Login 初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# オンライン中のユーザーを管理するための辞書
# 構造変更: { user_id: {'sid': request.sid, 'status': 'online'}, ... }
online_users = {}

# ミニゲームの状態管理 (簡易版)
game_rooms = {}

# スケジューラーの初期化
scheduler = BackgroundScheduler(daemon=True)

# --- ヘルパー関数 ---
def allowed_file(filename):
    """許可された拡張子のファイルかチェックする"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def scrape_weather():
    """天気情報を気象庁の公式JSONデータから取得"""
    with app.app_context():
        # 気象庁の東京都の天気予報JSONデータ
        url = 'https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json'
        data_to_save = "天気情報の取得に失敗しました。"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status() # エラーがあればここで例外発生
            data = response.json()
            
            # JSONデータから今日の東京の予報を抽出
            # timeSeries[0]は天気、timeSeries[2]は気温
            tokyo_forecast = data[0]['timeSeries'][0]['areas'][0]
            tokyo_temps = data[0]['timeSeries'][2]['areas'][0]

            weather = tokyo_forecast['weathers'][0]
            # 気温は今日の最高気温と明日の最低気温が提供されるため、今日の最高気温のみ採用
            high_temp = tokyo_temps['temps'][1]
            low_temp = tokyo_temps['temps'][0]

            # 不要な空白や改行を削除
            weather = ' '.join(weather.split())

            data_to_save = f"気象庁 (今日): {weather} 最高:{high_temp}℃ 最低:{low_temp}℃"
            print("Weather data updated successfully from JMA API.")

        except Exception as e:
            print(f"Weather scraping failed (jma.go.jp API): {e}")

        # --- データベースへの保存処理 ---
        try:
            db = get_db()
            db.execute('DELETE FROM weather_data')
            db.execute('INSERT INTO weather_data (source, data, timestamp) VALUES (?, ?, ?)',
                       ('jma.go.jp', data_to_save, datetime.now().isoformat()))
            db.commit()
        except Exception as db_e:
            print(f"Database error in scrape_weather: {db_e}")

def scrape_traffic():
    """交通情報をJR東日本のエリア運行状況ページからスクレイピング"""
    with app.app_context():
        url = 'https://traininfo.jreast.co.jp/train_info/kanto.aspx'
        data_to_save = "交通情報の取得に失敗しました。"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            status_section = soup.select_one("#tabs-area")
            info_list = []
            found_statuses = [] # ログ確認用のリスト

            if status_section:
                area_links = status_section.find_all('a')
                for link in area_links:
                    area_name_tag = link.find(string=True, recursive=False)
                    if not area_name_tag or not area_name_tag.strip():
                        area_name_tag = link.find('strong')
                    
                    status_img = link.find('img')
                    
                    if area_name_tag and status_img:
                        area_name = area_name_tag.text.strip()
                        status = status_img.get('alt', '情報なし').strip()
                        
                        found_statuses.append(f"{area_name}: {status}") # 取得した全ステータスをログ用に記録
                        
                        if "平常運転" not in status:
                            info_list.append(f"【{area_name}】{status}")
            
            # ログに取得した全情報を表示
            print(f"JR East Status Check: Found {len(found_statuses)} areas. Details: {', '.join(found_statuses)}")

            if info_list:
                data_to_save = " ".join(info_list[:5]) # 異常情報があれば表示 (最大5件)
            else:
                # 異常情報が1件もなければ平常運転と判断
                data_to_save = "JR東日本（関東エリア）は現在すべて平常運転です。"
            
            print("Traffic data updated successfully from JR East Area Status Page.")

        except Exception as e:
            print(f"Traffic scraping error (JR East Area Status Page): {e}")

        # --- データベースへの保存処理 ---
        try:
            db = get_db()
            db.execute('DELETE FROM traffic_data')
            db.execute('INSERT INTO traffic_data (data, timestamp) VALUES (?, ?)',
                      (data_to_save, datetime.now().isoformat()))
            db.commit()
        except Exception as db_e:
            print(f"Database error in scrape_traffic: {db_e}")



def scrape_disaster():
    """災害情報を気象庁の公式JSONデータから取得"""
    with app.app_context():
        # 気象庁の東京都の警報・注意報JSONデータ
        url = 'https://www.jma.go.jp/bosai/warning/data/warning/130000.json'
        data_to_save = "現在、主要な災害情報はありません。"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            data = response.json()
            
            # 実際のデータ構造に合わせて修正: トップレベルの headlineText を直接参照する
            headline = data.get('headlineText')
            
            # headlineが存在し、かつ空の文字列でないことを確認
            if headline and headline.strip():
                data_to_save = headline.strip()
            
            print("Disaster data updated successfully from JMA API.")
        except Exception as e:
            print(f"Disaster scraping failed (jma.go.jp API): {e}")
            data_to_save = "災害情報の取得に失敗しました。"

        # --- データベースへの保存処理 ---
        try:
            db = get_db()
            db.execute('DELETE FROM disaster_data')
            db.execute('INSERT INTO disaster_data (data, timestamp) VALUES (?, ?)',
                      (data_to_save, datetime.now().isoformat()))
            db.commit()
        except Exception as db_e:
            print(f"Database error in scrape_disaster: {db_e}")


# --- Userモデル定義 ---
class User(UserMixin):
    def __init__(self, id, username, email, password, is_admin=0, status='active',
                 profile_image='default_avatar.png', background_image='default_bg.png', status_message='はじめまして！',
                 bio=None, birthday=None, account_type='private', show_typing=1, show_online_status=1):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.is_admin = is_admin
        self.status = status # 'active', 'suspended', 'banned'
        self.profile_image = profile_image
        self.background_image = background_image
        self.status_message = status_message
        self.bio = bio
        self.birthday = birthday
        self.account_type = account_type
        self.show_typing = bool(show_typing)
        self.show_online_status = bool(show_online_status)
        self.current_status = 'offline'

# --- データベース関連ヘルパー関数 ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db_path = os.path.join(app.root_path, 'database')
        os.makedirs(db_path, exist_ok=True)
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- 拡張データベーススキーマの初期化 ---
def init_extended_db():
    """92機能対応の拡張データベーススキーマを作成"""
    with app.app_context():
        db = get_db()
        schema_sql = """
        -- users テーブル
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, email TEXT, password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_admin INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
            profile_image TEXT DEFAULT 'default_avatar.png', background_image TEXT DEFAULT 'default_bg.png',
            status_message TEXT DEFAULT 'はじめまして！', bio TEXT, birthday DATE, account_type TEXT DEFAULT 'private',
            show_typing INTEGER DEFAULT 1, show_online_status INTEGER DEFAULT 1,
            UNIQUE(username, account_type), UNIQUE(email, account_type)
        );
        -- friends テーブル
        CREATE TABLE IF NOT EXISTS friends (
            user_id INTEGER NOT NULL, friend_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            is_notification_off INTEGER DEFAULT 0, PRIMARY KEY (user_id, friend_id),
            FOREIGN KEY (user_id) REFERENCES users (id), FOREIGN KEY (friend_id) REFERENCES users (id)
        );
        -- rooms テーブル
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, creator_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (creator_id) REFERENCES users (id)
        );
        -- room_members テーブル
        CREATE TABLE IF NOT EXISTS room_members (
            room_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (room_id, user_id),
            FOREIGN KEY (room_id) REFERENCES rooms (id), FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- messages テーブル
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER NOT NULL, user_id INTEGER NOT NULL, content TEXT NOT NULL,
            message_type TEXT DEFAULT 'text', timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms (id), FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- private_messages テーブル
        CREATE TABLE IF NOT EXISTS private_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL, recipient_id INTEGER NOT NULL,
            content TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_from_ai INTEGER DEFAULT 0,
            is_read INTEGER DEFAULT 0, FOREIGN KEY (sender_id) REFERENCES users (id), FOREIGN KEY (recipient_id) REFERENCES users (id)
        );
        -- blocked_notifications テーブル
        CREATE TABLE IF NOT EXISTS blocked_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, blocker_id INTEGER NOT NULL, blocked_id INTEGER NOT NULL,
            notify_at TIMESTAMP NOT NULL, is_notified INTEGER DEFAULT 0,
            FOREIGN KEY (blocker_id) REFERENCES users (id), FOREIGN KEY (blocked_id) REFERENCES users (id)
        );
        -- invitation_tokens テーブル
        CREATE TABLE IF NOT EXISTS invitation_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- violation_reports テーブル
        CREATE TABLE IF NOT EXISTS violation_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id INTEGER NOT NULL, violator_id INTEGER NOT NULL,
            message_content TEXT NOT NULL, reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'pending',
            FOREIGN KEY (violator_id) REFERENCES users (id)
        );
        -- announcements テーブル
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        -- surveys テーブル
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT,
            is_active INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        -- survey_questions テーブル
        CREATE TABLE IF NOT EXISTS survey_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, survey_id INTEGER NOT NULL, question_text TEXT NOT NULL,
            question_type TEXT NOT NULL, FOREIGN KEY (survey_id) REFERENCES surveys (id)
        );
        -- survey_options テーブル
        CREATE TABLE IF NOT EXISTS survey_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER NOT NULL, option_text TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES survey_questions (id)
        );
        -- survey_responses テーブル
        CREATE TABLE IF NOT EXISTS survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, survey_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL, option_id INTEGER, response_text TEXT,
            responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (survey_id) REFERENCES surveys (id), FOREIGN KEY (question_id) REFERENCES survey_questions (id),
            FOREIGN KEY (option_id) REFERENCES survey_options (id)
        );
        -- timeline_posts テーブル
        CREATE TABLE IF NOT EXISTS timeline_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, content TEXT NOT NULL, media_url TEXT,
            post_type TEXT DEFAULT 'text', likes INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- weather_data テーブル
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, data TEXT, timestamp TIMESTAMP
        );
        -- traffic_data テーブル
        CREATE TABLE IF NOT EXISTS traffic_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, timestamp TIMESTAMP
        );
        -- disaster_data テーブル
        CREATE TABLE IF NOT EXISTS disaster_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, timestamp TIMESTAMP
        );
        -- game_scores テーブル
        CREATE TABLE IF NOT EXISTS game_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, game_type TEXT NOT NULL,
            score INTEGER DEFAULT 0, played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- stamps テーブル
        CREATE TABLE IF NOT EXISTS stamps (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, image_url TEXT NOT NULL,
            category TEXT, is_free INTEGER DEFAULT 1
        );
        -- user_stamps テーブル
        CREATE TABLE IF NOT EXISTS user_stamps (
            user_id INTEGER NOT NULL, stamp_id INTEGER NOT NULL, acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, stamp_id), FOREIGN KEY (user_id) REFERENCES users (id), FOREIGN KEY (stamp_id) REFERENCES stamps (id)
        );
        -- custom_themes テーブル
        CREATE TABLE IF NOT EXISTS custom_themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL,
            css_data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- login_streaks テーブル
        CREATE TABLE IF NOT EXISTS login_streaks (
            user_id INTEGER PRIMARY KEY, current_streak INTEGER DEFAULT 0, max_streak INTEGER DEFAULT 0,
            last_login_date DATE, FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- missions テーブル
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT,
            reward_points INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1
        );
        -- user_missions テーブル
        CREATE TABLE IF NOT EXISTS user_missions (
            user_id INTEGER NOT NULL, mission_id INTEGER NOT NULL, completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP, PRIMARY KEY (user_id, mission_id),
            FOREIGN KEY (user_id) REFERENCES users (id), FOREIGN KEY (mission_id) REFERENCES missions (id)
        );
        -- activity_feed テーブル
        CREATE TABLE IF NOT EXISTS activity_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, activity_type TEXT NOT NULL,
            activity_data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id)
        );
        -- ACHIEVEMENT TABLES
        CREATE TABLE IF NOT EXISTS achievement_criteria (
            achievement_name TEXT PRIMARY KEY, criteria_description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, achievement_name TEXT NOT NULL,
            description TEXT, achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id), FOREIGN KEY (achievement_name) REFERENCES achievement_criteria(achievement_name)
        );
        CREATE TABLE IF NOT EXISTS user_achievement_progress (
            user_id INTEGER NOT NULL, achievement_name TEXT NOT NULL, progress INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, achievement_name),
            FOREIGN KEY (user_id) REFERENCES users (id), FOREIGN KEY (achievement_name) REFERENCES achievement_criteria(achievement_name)
        );
        -- ... (以下、他の92機能に関連するテーブルスキーマも同様にCREATE IF NOT EXISTSで追加)
        """
        db.executescript(schema_sql)
        db.commit()
        print('拡張データベースを初期化・確認しました。')


# --- Flask CLI コマンド ---
@app.cli.command('initdb')
def initdb_command():
    init_extended_db()
    print('データベースの初期化が完了しました。')

@app.cli.command('create-admin')
def create_admin_command():
    """環境変数から管理者アカウントを作成します"""
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print('エラー: .envファイルにADMIN_EMAILとADMIN_PASSWORDを設定してください。')
        return

    with app.app_context():
        db = get_db()
        if db.execute("SELECT id FROM users WHERE email = ? AND account_type = 'work'", (ADMIN_EMAIL,)).fetchone():
            print(f'管理者アカウント ({ADMIN_EMAIL}) は既に存在します。')
            return

        hashed_password = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
        db.execute(
            'INSERT INTO users (username, email, password, is_admin, status, account_type) VALUES (?, ?, ?, ?, ?, ?)',
            (ADMIN_EMAIL.split('@')[0], ADMIN_EMAIL, hashed_password, 1, 'active', 'work')
        )
        db.commit()
        print(f'管理者アカウント {ADMIN_EMAIL} が正常に作成されました。')

# --- ログインマネージャーとデコレータ ---
@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_data = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], email=user_data['email'],
                    password=user_data['password'], is_admin=user_data['is_admin'], status=user_data['status'],
                    profile_image=user_data['profile_image'], background_image=user_data['background_image'],
                    status_message=user_data['status_message'], bio=user_data['bio'], birthday=user_data['birthday'],
                    account_type=user_data['account_type'], show_typing=user_data['show_typing'],
                    show_online_status=user_data['show_online_status'])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('管理者権限が必要です。', 'danger')
            return redirect(url_for('main_app'))
        return f(*args, **kwargs)
    return decorated_function

# --- ルーティング (認証・メインページ) ---
@app.route('/')
def index_loading():
    """サイトを開くとまずローディング画面を表示"""
    return render_template_string(LOADING_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_app'))

    if request.method == 'POST':
        account_type = request.form.get('account_type', 'private')
        login_id = request.form.get('login_id')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        db = get_db()
        query = 'SELECT * FROM users WHERE (email = ? OR username = ?) AND account_type = ?'
        user_data = db.execute(query, (login_id, login_id, account_type)).fetchone()

        if user_data and check_password_hash(user_data['password'], password):
            user = load_user(user_data['id'])
            if user.status != 'active':
                flash('このアカウントは現在利用が制限されています。', 'danger')
                return render_template_string(LOGIN_HTML, account_types=ACCOUNT_TYPES, selected_account_type=account_type)

            login_user(user, remember=remember)
            session['account_type'] = account_type
            update_login_streak(user.id)
            record_activity(user.id, 'login', f'{ACCOUNT_TYPES[account_type]["name"]}アカウントでログイン')

            if 'invite_token' in session:
                token = session.pop('invite_token', None)
                if token and _process_invitation(token, current_user):
                    flash('招待を通じて友達になりました！', 'success')
                return redirect(url_for('friends_page'))

            return redirect(url_for('main_app'))
        else:
            flash('ユーザー名/メールアドレスまたはパスワードが正しくありません。', 'danger')

    return render_template_string(LOGIN_HTML, account_types=ACCOUNT_TYPES, selected_account_type='private')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_app'))

    if request.method == 'POST':
        account_type = request.form.get('account_type', 'private')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not password:
            flash('ユーザー名とパスワードは必須です。', 'danger')
            return render_template_string(REGISTER_HTML, account_types=ACCOUNT_TYPES, selected_account_type=account_type)

        db = get_db()
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cursor = db.execute('INSERT INTO users (username, email, password, account_type) VALUES (?, ?, ?, ?)',
                                (username, email if email else None, hashed_password, account_type))
            db.commit()

            user_id = cursor.lastrowid
            give_default_stamps(user_id)
            check_achievement_unlocked(user_id, '新規登録', 1)

            flash(f'{ACCOUNT_TYPES[account_type]["name"]}アカウントの登録が完了しました。', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash(f'そのユーザー名またはメールアドレスは、{ACCOUNT_TYPES[account_type]["name"]}アカウントで既に使用されています。', 'danger')

    return render_template_string(REGISTER_HTML, account_types=ACCOUNT_TYPES, selected_account_type='private')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('account_type', None)
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

@app.route('/app')
@login_required
def main_app():
    """メインアプリケーション画面（ホームタブ）"""
    db = get_db()
    account_type = session.get('account_type', 'private')
    theme_info = ACCOUNT_TYPES.get(account_type, ACCOUNT_TYPES['private'])

    favorite_friends = db.execute("SELECT u.id, u.username, u.profile_image FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND f.status = 'favorite'",(current_user.id,)).fetchall()
    normal_friends = db.execute("SELECT u.id, u.username, u.profile_image FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND f.status = 'friend'",(current_user.id,)).fetchall()

    today = datetime.now()
    seven_days_later = today + timedelta(days=7)
    birthday_friends = db.execute("SELECT u.username, u.birthday FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND u.birthday IS NOT NULL AND SUBSTR(u.birthday, 6, 5) BETWEEN ? AND ?",(current_user.id, today.strftime('%m-%d'), seven_days_later.strftime('%m-%d'))).fetchall()

    talks_list_query = """
        SELECT p.partner_id, u.username as partner_name, u.profile_image as partner_image, p.last_message_content, p.last_message_time,
               (SELECT COUNT(*) FROM private_messages pm WHERE pm.sender_id = p.partner_id AND pm.recipient_id = ? AND pm.is_read = 0) as unread_count
        FROM (
            SELECT
                CASE WHEN sender_id = ? THEN recipient_id ELSE sender_id END as partner_id,
                MAX(content) as last_message_content, MAX(timestamp) as last_message_time
            FROM private_messages WHERE sender_id = ? OR recipient_id = ?
            GROUP BY partner_id
        ) p JOIN users u ON u.id = p.partner_id
        WHERE u.id != ? ORDER BY p.last_message_time DESC
    """
    talks_list = db.execute(talks_list_query, (current_user.id, current_user.id, current_user.id, current_user.id, current_user.id)).fetchall()

    announcements = db.execute('SELECT * FROM announcements ORDER BY created_at DESC LIMIT 3').fetchall()
    daily_missions = db.execute('SELECT * FROM missions WHERE is_active = 1 LIMIT 3').fetchall()
    activity_feed = db.execute("SELECT af.*, u.username, u.profile_image FROM activity_feed af JOIN users u ON af.user_id = u.id WHERE af.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status IN ('friend', 'favorite')) OR af.user_id = ? ORDER BY af.created_at DESC LIMIT 10", (current_user.id, current_user.id)).fetchall()

    return render_template_string(MAIN_APP_HTML, current_user=current_user, theme=theme_info, favorite_friends=favorite_friends, normal_friends=normal_friends,
                                  birthday_notifications=birthday_friends, talks_list=talks_list, announcements=announcements,
                                  daily_missions=daily_missions, activity_feed=activity_feed)

# --- タイムライン機能 ---
@app.route('/timeline')
@login_required
def timeline():
    db = get_db()
    weather_data = db.execute('SELECT * FROM weather_data ORDER BY timestamp DESC').fetchall()
    traffic = db.execute('SELECT * FROM traffic_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    disaster = db.execute('SELECT * FROM disaster_data ORDER BY timestamp DESC LIMIT 1').fetchone()

    posts = db.execute("SELECT tp.*, u.username, u.profile_image FROM timeline_posts tp JOIN users u ON tp.user_id = u.id ORDER BY tp.created_at DESC LIMIT 50").fetchall()

    return render_template_string(TIMELINE_HTML, current_user=current_user, weather_data=weather_data, traffic=traffic, disaster=disaster, posts=posts)

@app.route('/timeline/post', methods=['POST'])
@login_required
def post_timeline():
    content = request.form.get('content')
    media_file = request.files.get('media')
    if not content and not media_file:
        flash('投稿内容を入力してください。', 'warning')
        return redirect(url_for('timeline'))

    db = get_db()
    media_url = None
    if media_file and allowed_file(media_file.filename):
        filename = secure_filename(f"timeline_{current_user.id}_{int(time.time())}_{media_file.filename}")
        media_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        media_url = filename

    db.execute('INSERT INTO timeline_posts (user_id, content, media_url) VALUES (?, ?, ?)', (current_user.id, content, media_url))
    db.commit()
    record_activity(current_user.id, 'timeline_post', '新しい投稿をしました')
    flash('投稿しました！', 'success')
    return redirect(url_for('timeline'))

# --- ミニゲーム機能 ---
@app.route('/games')
@login_required
def games_hub():
    db = get_db()
    games = [
        {'id': 'daifugo', 'name': '大富豪', 'icon': 'bi-suit-spade-fill', 'players': '2-6人', 'description': 'カードゲームの王様'},
        {'id': 'babanuki', 'name': 'ババ抜き', 'icon': 'bi-suit-club-fill', 'players': '2-6人', 'description': '運と戦略のゲーム'},
        {'id': 'amidakuji', 'name': 'あみだくじ', 'icon': 'bi-ladder', 'players': '2-10人', 'description': '運試しにどうぞ'},
        {'id': 'quiz', 'name': 'クイズ', 'icon': 'bi-patch-question-fill', 'players': '1-10人', 'description': '知識を試すクイズゲーム'},
        {'id': 'shiritori', 'name': 'しりとり', 'icon': 'bi-chat-text-fill', 'players': '2-6人', 'description': 'みんなで言葉遊び'},
        {'id': 'janken', 'name': 'じゃんけん', 'icon': 'bi-hand-index-thumb-fill', 'players': '2人', 'description': 'シンプルな運試し'}
    ]
    rankings = db.execute("SELECT u.username, gs.game_type, MAX(gs.score) as high_score FROM game_scores gs JOIN users u ON gs.user_id = u.id GROUP BY gs.game_type, u.username ORDER BY high_score DESC LIMIT 10").fetchall()
    return render_template_string(GAMES_HUB_HTML, games=games, rankings=rankings)

@app.route('/game/create', methods=['POST'])
@login_required
def create_game():
    game_type = request.form.get('game_type')
    max_players = int(request.form.get('max_players', 4))
    with_cpu = request.form.get('with_cpu') == 'true'

    room_id = str(uuid.uuid4())[:8]
    game_rooms[room_id] = {
        'type': game_type, 'host': current_user.id,
        'players': [{'id': current_user.id, 'name': current_user.username, 'is_cpu': False}],
        'max_players': max_players, 'with_cpu': with_cpu, 'status': 'waiting',
        'created_at': datetime.now().isoformat()
    }

    if with_cpu:
        for i in range(max_players - 1):
            game_rooms[room_id]['players'].append({'id': f'cpu_{i}', 'name': f'CPU {i+1}', 'is_cpu': True})

    flash(f'{game_type}ゲームルームを作成しました！ルームID: {room_id}', 'success')
    return jsonify({'room_id': room_id, 'game_type': game_type})

@app.route('/game/<room_id>')
@login_required
def game_room(room_id):
    if room_id not in game_rooms:
        flash('ゲームルームが見つかりません。', 'danger')
        return redirect(url_for('games_hub'))

    room = game_rooms[room_id]
    template_map = {'daifugo': GAME_DAIFUGO_HTML, 'babanuki': GAME_BABANUKI_HTML, 'amidakuji': GAME_AMIDAKUJI_HTML,
                    'quiz': GAME_QUIZ_HTML, 'shiritori': GAME_SHIRITORI_HTML, 'janken': GAME_JANKEN_HTML}
    return render_template_string(template_map.get(room['type'], GAMES_HUB_HTML), room=room, room_id=room_id, current_user=current_user)

# --- スタンプ機能 ---
@app.route('/stamps')
@login_required
def stamps_page():
    db = get_db()
    if db.execute('SELECT COUNT(*) FROM stamps WHERE is_free = 1').fetchone()[0] == 0:
        default_stamps = [('笑顔', '😀', 'emotion'), ('ハート', '❤️', 'emotion'), ('OK', '👌', 'gesture')]
        db.executemany('INSERT INTO stamps (name, image_url, category, is_free) VALUES (?, ?, ?, 1)', default_stamps)
        db.commit()
    free_stamps = db.execute('SELECT * FROM stamps WHERE is_free = 1').fetchall()
    user_stamps = db.execute("SELECT s.* FROM stamps s JOIN user_stamps us ON s.id = us.stamp_id WHERE us.user_id = ?", (current_user.id,)).fetchall()
    return render_template_string(STAMPS_HTML, free_stamps=free_stamps, user_stamps=user_stamps)

@app.route('/stamps/acquire/<int:stamp_id>')
@login_required
def acquire_stamp(stamp_id):
    db = get_db()
    stamp = db.execute('SELECT * FROM stamps WHERE id = ? AND is_free = 1', (stamp_id,)).fetchone()
    if not stamp:
        flash('このスタンプは取得できません。', 'warning')
    elif db.execute('SELECT 1 FROM user_stamps WHERE user_id = ? AND stamp_id = ?', (current_user.id, stamp_id)).fetchone():
        flash('既にこのスタンプを所有しています。', 'info')
    else:
        db.execute('INSERT INTO user_stamps (user_id, stamp_id) VALUES (?, ?)', (current_user.id, stamp_id))
        db.commit()
        flash('スタンプを取得しました！', 'success')
        record_activity(current_user.id, 'acquire_stamp', f'{stamp["name"]}スタンプを取得')
        check_achievement_unlocked(current_user.id, 'スタンプコレクター', 1)
    return redirect(url_for('stamps_page'))

# --- 設定画面 ---
@app.route('/settings')
@login_required
def settings_page():
    db = get_db()
    user_data = db.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
    custom_themes = db.execute('SELECT * FROM custom_themes WHERE user_id = ?', (current_user.id,)).fetchall()
    return render_template_string(SETTINGS_HTML, user=user_data, custom_themes=custom_themes, account_types=ACCOUNT_TYPES)

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    db = get_db()
    username, email, status_message, bio, birthday, account_type = (request.form.get(k) for k in ['username', 'email', 'status_message', 'bio', 'birthday', 'account_type'])
    show_typing = request.form.get('show_typing') == '1'
    show_online_status = request.form.get('show_online_status') == '1'
    profile_image_filename = current_user.profile_image

    if 'profile_image' in request.files:
        profile_image_file = request.files['profile_image']
        if profile_image_file and allowed_file(profile_image_file.filename):
            filename_secure = secure_filename(f"user_{current_user.id}_{int(time.time())}_{profile_image_file.filename}")
            profile_image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_images', filename_secure))
            profile_image_filename = filename_secure
    try:
        db.execute("UPDATE users SET username = ?, email = ?, status_message = ?, bio = ?, birthday = ?, account_type = ?, show_typing = ?, show_online_status = ?, profile_image = ? WHERE id = ?",
                   (username, email, status_message, bio, birthday, account_type, show_typing, show_online_status, profile_image_filename, current_user.id))
        db.commit()
        flash('設定を更新しました。', 'success')
    except sqlite3.IntegrityError:
        flash('ユーザー名またはメールアドレスが既に存在します。', 'danger')
    return redirect(url_for('settings_page'))

# --- 外部サービス連携 ---
@app.route('/external/youtube')
@login_required
def youtube_redirect():
    record_activity(current_user.id, 'external_link', 'YouTubeを開きました')
    return redirect('https://www.youtube.com')

@app.route('/external/gmail')
@login_required
def gmail_redirect():
    record_activity(current_user.id, 'external_link', 'Gmailを開きました')
    return redirect('https://mail.google.com')

# --- プロフィール編集・閲覧 ---
@app.route('/profile/edit')
@login_required
def profile_edit_page():
    user_data = get_db().execute("SELECT * FROM users WHERE id = ?", (current_user.id,)).fetchone()
    return render_template_string(PROFILE_EDIT_HTML, user=user_data, account_types=ACCOUNT_TYPES)

@app.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash("ユーザーが見つかりません。", 'warning')
        return redirect(url_for('main_app'))
    friend_status = 'not_friend'
    if user_id != current_user.id:
        rel = db.execute("SELECT status FROM friends WHERE user_id = ? AND friend_id = ?", (current_user.id, user_id)).fetchone()
        if rel: friend_status = rel['status']
    achievements = db.execute("SELECT ac.achievement_name, ac.criteria_description, CASE WHEN ua.achieved_at IS NOT NULL THEN 1 ELSE 0 END AS is_unlocked FROM achievement_criteria ac LEFT JOIN user_achievements ua ON ac.achievement_name = ua.achievement_name AND ua.user_id = ?", (user_id,)).fetchall()
    return render_template_string(PROFILE_VIEW_HTML, user=user, friend_status=friend_status, achievements=achievements)

@app.route('/toggle_favorite/<int:friend_id>')
@login_required
def toggle_favorite(friend_id):
    db = get_db()
    current_relation = db.execute("SELECT status FROM friends WHERE user_id = ? AND friend_id = ?",
                                  (current_user.id, friend_id)).fetchone()
    
    if current_relation:
        new_status = 'friend' if current_relation['status'] == 'favorite' else 'favorite'
        db.execute("UPDATE friends SET status = ? WHERE user_id = ? AND friend_id = ?",
                  (new_status, current_user.id, friend_id))
        db.commit()
        flash('お気に入り設定を変更しました。', 'info')
    else:
        flash('友達が見つかりません。', 'warning')
    return redirect(url_for('friends_page'))

# [修正] データベースの`status`カラムを上書きしないように変更
@app.route('/profile/update_status', methods=['POST'])
@login_required
def update_profile_status():
    status = request.form.get('status')
    if status not in ['online', 'away', 'busy', 'invisible']:
        return jsonify({'success': False, 'message': '無効なステータスです。'})
    
    # オンライン中のユーザー情報内でのみステータスを更新
    if current_user.id in online_users:
        online_users[current_user.id]['status'] = status
        
        # リアルタイムで友達にステータス変更を通知 (SocketIO)
        db = get_db()
        friends = db.execute("SELECT friend_id FROM friends WHERE user_id = ? AND (status = 'friend' OR status = 'favorite')", (current_user.id,)).fetchall()
        for friend_row in friends:
            friend_id = friend_row['friend_id']
            if friend_id in online_users:
                socketio.emit('friend_status_update', {
                    'user_id': current_user.id,
                    'status': status
                }, room=online_users[friend_id]['sid'])
        return jsonify({'success': True, 'message': 'ステータスを更新しました。'})
    else:
        return jsonify({'success': False, 'message': 'オフラインのためステータスを変更できません。'})


# --- 友達管理 ---
@app.route('/friends', methods=['GET', 'POST'])
@login_required
def friends_page():
    db = get_db()
    query = request.form.get('query', '') if request.method == 'POST' else ''
    search_results = []
    if query:
        search_results_raw = db.execute("SELECT u.id, u.username, u.profile_image FROM users u WHERE u.username LIKE ? AND u.id != ? AND NOT EXISTS (SELECT 1 FROM friends f WHERE f.user_id = ? AND f.friend_id = u.id)", ('%' + query + '%', current_user.id, current_user.id)).fetchall()
        for user_row in search_results_raw:
            user_dict = dict(user_row)
            user_dict['is_pending_request'] = bool(db.execute("SELECT 1 FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'pending'", (current_user.id, user_row['id'])).fetchone())
            search_results.append(user_dict)

    requests_data = db.execute("SELECT u.id, u.username, u.profile_image FROM friends f JOIN users u ON f.user_id = u.id WHERE f.friend_id = ? AND f.status = 'pending'", (current_user.id,)).fetchall()
    friends_data = db.execute("SELECT u.id, u.username, u.profile_image, f.status FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND f.status IN ('friend', 'favorite', 'close') ORDER BY u.username", (current_user.id,)).fetchall()

    invite_link = None
    existing_token = db.execute('SELECT token FROM invitation_tokens WHERE user_id = ? AND expires_at > ?', (current_user.id, datetime.now())).fetchone()
    if existing_token:
        invite_link = url_for('accept_invite', token=existing_token['token'], _external=True)
    else:
        token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=1)
        db.execute('INSERT INTO invitation_tokens (user_id, token, expires_at) VALUES (?, ?, ?)', (current_user.id, token, expires_at))
        db.commit()
        invite_link = url_for('accept_invite', token=token, _external=True)

    return render_template_string(FRIENDS_HTML, friend_requests=requests_data, friends_list=friends_data, search_results=search_results, query=query, invite_link=invite_link)

@app.route('/accept_invite/<token>')
def accept_invite(token):
    if current_user.is_authenticated:
        if _process_invitation(token, current_user):
            flash('招待を通じて友達になりました！', 'success')
        else:
            flash('無効な招待か、既に友達の可能性があります。', 'warning')
        return redirect(url_for('friends_page'))
    else:
        session['invite_token'] = token
        flash('ログインして招待を承認してください。', 'info')
        return redirect(url_for('login'))

@app.route('/send_request/<int:recipient_id>')
@login_required
def send_request(recipient_id):
    db = get_db()
    if recipient_id == current_user.id:
        flash('自分自身に友達リクエストは送れません。', 'warning')
    elif db.execute("SELECT 1 FROM friends WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)", (current_user.id, recipient_id, recipient_id, current_user.id)).fetchone():
        flash('既に友達、またはリクエスト済です。', 'info')
    else:
        db.execute('INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, ?)', (current_user.id, recipient_id, 'pending'))
        db.commit()
        flash('友達リクエストを送信しました。', 'success')
        if recipient_id in online_users:
            socketio.emit('friend_request_received', {'sender_username': current_user.username}, room=online_users[recipient_id]['sid'])
    return redirect(url_for('friends_page'))

@app.route('/accept_request/<int:sender_id>')
@login_required
def accept_request(sender_id):
    db = get_db()
    db.execute("UPDATE friends SET status = 'friend' WHERE user_id = ? AND friend_id = ?", (sender_id, current_user.id))
    db.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, status) VALUES (?, ?, 'friend')", (current_user.id, sender_id))
    db.commit()
    flash('友達になりました！', 'success')
    if sender_id in online_users:
        socketio.emit('friend_accepted_notification', {'acceptor_username': current_user.username}, room=online_users[sender_id]['sid'])
    check_achievement_unlocked(current_user.id, '友達の輪', 1)
    check_achievement_unlocked(sender_id, '友達の輪', 1)
    return redirect(url_for('friends_page'))

# ... (他の友達管理ルート: toggle_favorite, update_profile_statusなど)

# --- グループ作成 ---
@app.route('/create_group_page')
@login_required
def create_group_page():
    friends_list = get_db().execute("SELECT id, username FROM users u JOIN friends f ON u.id = f.friend_id WHERE f.user_id = ? AND f.status = 'friend'", (current_user.id,)).fetchall()
    return render_template_string(CREATE_GROUP_HTML, friends_list=friends_list)

@app.route('/create_group', methods=['POST'])
@login_required
def create_group():
    db = get_db()
    group_name = request.form.get('group_name')
    if not group_name:
        flash('グループ名を入力してください。', 'danger')
        return redirect(url_for('create_group_page'))
    try:
        cursor = db.execute('INSERT INTO rooms (name, creator_id) VALUES (?, ?)', (group_name, current_user.id))
        room_id = cursor.lastrowid
        db.execute('INSERT INTO room_members (room_id, user_id) VALUES (?, ?)', (room_id, current_user.id))
        for member_id in request.form.getlist('members'):
            db.execute('INSERT INTO room_members (room_id, user_id) VALUES (?, ?)', (room_id, int(member_id)))
        db.commit()
        flash(f'グループ "{group_name}" を作成しました！', 'success')
        check_achievement_unlocked(current_user.id, 'グループリーダー', 1)
    except sqlite3.IntegrityError:
        flash('同じ名前のグループが既に存在します。', 'danger')
    return redirect(url_for('main_app'))

# --- チャット・その他ページ ---
@app.route('/app/chat_with/<int:user_id>')
@login_required
def start_chat_with(user_id):
    db = get_db()
    opponent = db.execute('SELECT id, username, profile_image FROM users WHERE id = ?', (user_id,)).fetchone()
    if not opponent:
        flash('チャット相手が見つかりません。', 'warning')
        return redirect(url_for('main_app'))
    messages = [dict(msg) for msg in db.execute('SELECT * FROM private_messages WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?) ORDER BY timestamp ASC', (current_user.id, user_id, user_id, current_user.id)).fetchall()]
    db.execute('UPDATE private_messages SET is_read = 1 WHERE sender_id = ? AND recipient_id = ?', (user_id, current_user.id))
    db.commit()
    return render_template_string(CHAT_HTML, opponent=opponent, messages=messages, current_user=current_user)

@app.route('/app/keep_memo')
@login_required
def keep_memo():
    messages = [dict(m) for m in get_db().execute("SELECT * FROM private_messages WHERE sender_id = ? AND recipient_id = ? ORDER BY timestamp ASC", (current_user.id, current_user.id)).fetchall()]
    return render_template_string(KEEP_MEMO_HTML, messages=messages, current_user=current_user)

@app.route('/announcements')
@login_required
def announcements_page():
    announcements = get_db().execute('SELECT * FROM announcements ORDER BY created_at DESC').fetchall()
    return render_template_string(ANNOUNCEMENTS_HTML, announcements=announcements)

@app.route('/app/ai_chat_page')
@login_required
def ai_chat_page():
    history = [dict(m) for m in get_db().execute("SELECT * FROM private_messages WHERE (sender_id = ? AND recipient_id = 0) OR (sender_id = 0 AND recipient_id = ?) ORDER BY timestamp ASC", (current_user.id, current_user.id,)).fetchall()]
    return render_template_string(AI_CHAT_HTML, history=history, current_user=current_user)

@app.route('/app/survey_page')
@login_required
def survey_page():
    db = get_db()
    # デフォルトアンケートが存在するか確認
    survey = db.execute("SELECT * FROM surveys WHERE title = ?", ('TMHKchat利用満足度アンケート',)).fetchone()
    
    # なければ作成する
    if not survey:
        cursor = db.execute("INSERT INTO surveys (title, description, is_active) VALUES (?, ?, 1)", ('TMHKchat利用満足度アンケート', '今後のサービス向上のため、ご協力をお願いいたします。'))
        survey_id = cursor.lastrowid
        
        questions = [
            {'q': 'TMHKchatの全体的な満足度を5段階で教えてください。', 'type': 'multiple_choice', 'opts': ['5 (非常に満足)', '4 (満足)', '3 (普通)', '2 (不満)', '1 (非常に不満)']},
            {'q': '最もよく利用する機能は何ですか？', 'type': 'multiple_choice', 'opts': ['1対1チャット', 'グループチャット', 'タイムライン', 'ミニゲーム', 'AIチャット']},
            {'q': 'UI（デザインや使いやすさ）についてどう思いますか？', 'type': 'multiple_choice', 'opts': ['とても良い', '良い', '普通', '悪い', 'とても悪い']},
            {'q': '今後追加してほしい機能があれば教えてください。', 'type': 'text'},
            {'q': 'その他、ご意見やご感想があれば自由にお書きください。', 'type': 'text'}
        ]
        
        for q_data in questions:
            q_cursor = db.execute("INSERT INTO survey_questions (survey_id, question_text, question_type) VALUES (?, ?, ?)", (survey_id, q_data['q'], q_data['type']))
            if q_data['type'] == 'multiple_choice':
                question_id = q_cursor.lastrowid
                for opt_text in q_data['opts']:
                    db.execute("INSERT INTO survey_options (question_id, option_text) VALUES (?, ?)", (question_id, opt_text))
        db.commit()
        survey = db.execute("SELECT * FROM surveys WHERE id = ?", (survey_id,)).fetchone()

    # ユーザーが既に回答済みかチェック
    has_answered = db.execute("SELECT 1 FROM survey_responses WHERE user_id = ? AND survey_id = ?", (current_user.id, survey['id'])).fetchone()

    if has_answered:
        flash('アンケートにご協力いただき、ありがとうございました！', 'info')
        # ここでは回答済みでも表示するが、将来的には結果ページなどにリダイレクトも可能
    
    questions = db.execute("SELECT * FROM survey_questions WHERE survey_id = ?", (survey['id'],)).fetchall()
    options = {q['id']: db.execute("SELECT * FROM survey_options WHERE question_id = ?", (q['id'],)).fetchall() for q in questions}
    
    return render_template_string(SURVEY_HTML, survey=survey, questions=questions, options=options, has_answered=has_answered)

@app.route('/survey/submit', methods=['POST'])
@login_required
def submit_survey():
    db = get_db()
    survey_id = request.form.get('survey_id')
    
    for key, value in request.form.items():
        if key.startswith('question-'):
            question_id = key.split('-')[1]
            question_type = key.split('-')[2]
            
            if question_type == 'text':
                db.execute("INSERT INTO survey_responses (user_id, survey_id, question_id, response_text) VALUES (?, ?, ?, ?)",
                           (current_user.id, survey_id, question_id, value))
            elif question_type == 'multiple_choice':
                option_id = value
                db.execute("INSERT INTO survey_responses (user_id, survey_id, question_id, option_id) VALUES (?, ?, ?, ?)",
                           (current_user.id, survey_id, question_id, option_id))
    db.commit()
    flash('アンケートにご回答いただきありがとうございます！', 'success')
    return redirect(url_for('main_app'))

@app.route('/app/search_results', methods=['POST'])
@login_required
def main_search():
    query = request.form.get('query', '')
    # このルートはfriends_pageに統合されているため、基本的には使用されない想定
    # もし使用する場合はfriends_pageと同様のロジックをここに実装
    return redirect(url_for('friends_page'))


# --- ヘルパー関数群 ---
def update_login_streak(user_id):
    db = get_db()
    today = datetime.now().date()
    streak_data = db.execute('SELECT * FROM login_streaks WHERE user_id = ?', (user_id,)).fetchone()
    if not streak_data:
        db.execute('INSERT INTO login_streaks (user_id, current_streak, max_streak, last_login_date) VALUES (?, 1, 1, ?)', (user_id, today))
    else:
        last_login = datetime.strptime(streak_data['last_login_date'], '%Y-%m-%d').date()
        if (today - last_login).days == 1:
            new_streak = streak_data['current_streak'] + 1
            db.execute('UPDATE login_streaks SET current_streak = ?, max_streak = ?, last_login_date = ? WHERE user_id = ?', (new_streak, max(new_streak, streak_data['max_streak']), today, user_id))
        elif (today - last_login).days > 1:
            db.execute('UPDATE login_streaks SET current_streak = 1, last_login_date = ? WHERE user_id = ?', (today, user_id))
    db.commit()

def record_activity(user_id, activity_type, activity_data_json):
    db = get_db()
    db.execute('INSERT INTO activity_feed (user_id, activity_type, activity_data) VALUES (?, ?, ?)', (user_id, activity_type, activity_data_json))
    db.commit()

def give_default_stamps(user_id):
    db = get_db()
    default_stamps = db.execute('SELECT id FROM stamps WHERE is_free = 1').fetchall()
    for stamp in default_stamps:
        db.execute('INSERT OR IGNORE INTO user_stamps (user_id, stamp_id) VALUES (?, ?)', (user_id, stamp['id']))
    db.commit()

def _process_invitation(token, recipient_user):
    db = get_db()
    result = db.execute('SELECT * FROM invitation_tokens WHERE token = ? AND expires_at > ?', (token, datetime.now())).fetchone()
    if result and result['user_id'] != recipient_user.id:
        sender_id = result['user_id']
        db.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, status) VALUES (?, ?, 'friend')", (recipient_user.id, sender_id))
        db.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, status) VALUES (?, ?, 'friend')", (sender_id, recipient_user.id))
        db.execute('DELETE FROM invitation_tokens WHERE token = ?', (token,))
        db.commit()
        return True
    return False

def check_achievement_unlocked(user_id, achievement_name, progress_increment=1):
    db = get_db()
    criteria = {'新規登録': 'HKchatに初めて登録', '友達の輪': '友達を1人追加', 'スタンプコレクター': 'スタンプを1つ取得', 'グループリーダー': 'グループを1つ作成'}
    if achievement_name in criteria:
        db.execute("INSERT OR IGNORE INTO achievement_criteria (achievement_name, criteria_description) VALUES (?, ?)", (achievement_name, criteria[achievement_name]))
        if not db.execute("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_name = ?", (user_id, achievement_name)).fetchone():
            db.execute("INSERT INTO user_achievements (user_id, achievement_name, description) VALUES (?, ?, ?)", (user_id, achievement_name, criteria[achievement_name]))
            db.commit()
            # UI通知はSocketIOで行うのが望ましい
            print(f"User {user_id} unlocked achievement: {achievement_name}")


# --- SocketIO イベントハンドラ ---
# --- Quiz & Shiritori Event Handlers ---

# [修正] ロジックのバグを修正
@socketio.on('submit_answer')
@login_required
def handle_submit_answer(data):
    room_id = data['room_id']
    answer = data['answer']
    if room_id not in game_rooms: return
    room = game_rooms[room_id]

    if 'answers' not in room: room['answers'] = {}
    
    # 回答済みの場合は何もしない
    if current_user.id in room['answers']: return

    # 回答を記録
    room['answers'][current_user.id] = answer
    current_question = room['questions'][room['question_index']]
    is_correct = (answer == current_question['correct'])
    
    if 'scores' not in room: room['scores'] = {p['id']: 0 for p in room['players']}
    if is_correct:
        room['scores'][current_user.id] += 10
    
    emit('answer_result', {'is_correct': is_correct}, room=request.sid)

    # 全員が回答したら次の問題へ (CPUは回答しないので除外)
    human_players = [p for p in room['players'] if not p.get('is_cpu', False)]
    if len(room['answers']) == len(human_players):
        emit('show_correct_answer', {'correct_answer': current_question['correct'], 'scores': room['scores']}, room=room_id)
        room['question_index'] += 1
        # 3秒後に次の問題へ
        socketio.sleep(3) 

        if room['question_index'] < len(room['questions']):
            handle_next_question(room_id)
        else:
            # プレイヤー名を取得するためにplayer_mapを使用
            winner_id = max(room['scores'], key=room['scores'].get)
            winner_name = room['player_map'].get(winner_id, '不明なプレイヤー')
            emit('game_over', {'winner': winner_name, 'message': 'クイズ終了！'}, room=room_id)

@socketio.on('generate_ai_quiz')
@login_required
def handle_generate_ai_quiz(data):
    room_id = data['room_id']
    theme = data.get('theme', '一般的な知識') # テーマがなければデフォルト値を設定
    
    if room_id not in game_rooms or game_rooms[room_id]['host'] != current_user.id:
        return emit('ai_quiz_error', {'message': 'クイズの生成権限がありません。'}, room=request.sid)

    if not ai_model:
        return emit('ai_quiz_error', {'message': 'AI機能は現在利用できません。'}, room=request.sid)

    emit('log_message', {'message': f"AIが「{theme}」に関するクイズを生成中です..."}, room=room_id)

    # Gemini Proへの指示（プロンプト）
    prompt = f"""
    「{theme}」に関する面白い4択クイズを3問、以下のJSON形式の配列で作成してください。
    - "q"は問題文です。
    - "options"は4つの選択肢の配列です。
    - "correct"は正解の選択肢の文字列です。
    - JSON以外の余計な説明や前置きは一切含めないでください。

    [
      {{"q": "問題文1", "options": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"], "correct": "正解の選択肢"}},
      {{"q": "問題文2", "options": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"], "correct": "正解の選択肢"}},
      {{"q": "問題文3", "options": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"], "correct": "正解の選択肢"}}
    ]
    """

    try:
        response = ai_model.generate_content(prompt)
        # AIの出力をクリーンアップしてJSONとしてパース
        clean_response = response.text.strip().replace('```json', '').replace('```', '')
        quiz_data = json.loads(clean_response)
        
        # 部屋情報に生成したクイズを保存
        room = game_rooms[room_id]
        room['questions'] = quiz_data
        
        # 全員にクイズが作成されたことを通知
        emit('quiz_generated', {'theme': theme}, room=room_id)

    except Exception as e:
        print(f"AI Quiz Generation Error: {e}")
        emit('ai_quiz_error', {'message': 'AIによるクイズの生成に失敗しました。'}, room=request.sid)

def handle_next_question(room_id):
    room = game_rooms[room_id]
    room['answers'] = {}
    next_q = room['questions'][room['question_index']]
    emit('new_question', {'question': next_q['q'], 'options': next_q['options']}, room=room_id)


@socketio.on('submit_word')
@login_required
def handle_submit_word(data):
    room_id = data['room_id']
    word = data['word']
    if room_id not in game_rooms: return
    room = game_rooms[room_id]

    # バリデーション
    if room['turn_order'][room['current_turn_index']] != current_user.id:
        return emit('invalid_word', {'message': 'あなたのターンではありません。'}, room=request.sid)
    if word in room['used_words']:
        return emit('invalid_word', {'message': 'その言葉は既に使用されています。'}, room=request.sid)
    if room['last_char'] and word[0] != room['last_char']:
         return emit('invalid_word', {'message': f"「{room['last_char']}」から始まる言葉を入力してください。"}, room=request.sid)
    if word.endswith('ん'):
        emit('game_over', {'loser': current_user.username, 'message': f"「{word}」で「ん」がついたため、{current_user.username}さんの負けです！"}, room=room_id)
        room['status'] = 'finished'
        return
        
    # 成功した場合
    room['used_words'].append(word)
    room['last_char'] = word[-1]
    room['current_turn_index'] = (room['current_turn_index'] + 1) % len(room['turn_order'])
    
    emit('update_game_state', {
        'current_word': word,
        'last_char': room['last_char'],
        'used_words': room['used_words'],
        'current_turn': room['turn_order'][room['current_turn_index']]
    }, room=room_id)

# [修正] ステータスも管理するように変更
@socketio.on('connect')
@login_required
def handle_connect():
    online_users[current_user.id] = {'sid': request.sid, 'status': 'online'}
    join_room(request.sid)
    print(f"User {current_user.username} connected with sid {request.sid}")

# [修正] ゲームルームからの退出処理を追加
@socketio.on('disconnect')
def handle_disconnect():
    user_id_to_remove = None
    for user_id, data in online_users.items():
        if data['sid'] == request.sid:
            user_id_to_remove = user_id
            break
            
    if user_id_to_remove:
        # 参加していたゲームルームから退出
        for room_id, room_data in game_rooms.items():
            player_ids = [p['id'] for p in room_data.get('players', [])]
            if user_id_to_remove in player_ids:
                leave_room(room_id, sid=request.sid)
                print(f"User {user_id_to_remove} left game room {room_id}")

        del online_users[user_id_to_remove]
        print(f"User {user_id_to_remove} disconnected.")


@socketio.on('send_private_message')
@login_required
def handle_send_private_message(data):
    recipient_id = int(data['recipient_id'])
    content = data['message']
    
    db = get_db()
    db.execute('INSERT INTO private_messages (sender_id, recipient_id, content) VALUES (?, ?, ?)',
               (current_user.id, recipient_id, content))
    db.commit()

    message_data = {'sender_id': current_user.id, 'content': content, 'timestamp': datetime.now().isoformat()}
    
    # 送信者自身の画面にメッセージを返す
    emit('new_private_message', message_data, room=request.sid)
    
    # 送信者と受信者が別で、かつ受信者がオンラインの場合のみ追加で送信する
    if recipient_id != current_user.id and recipient_id in online_users:
        emit('new_private_message', message_data, room=online_users[recipient_id]['sid'])

# --- スケジュールタスク ---
def scheduled_scraping_tasks():
    print("Running scheduled scraping tasks...")
    scrape_weather()
    scrape_traffic()
    scrape_disaster()
    print("Scheduled scraping tasks finished.")

# スケジューラーにタスクを追加
scheduler.add_job(scheduled_scraping_tasks, 'interval', hours=1, id='scraping_job')
if not scheduler.running:
    scheduler.start(paused=False)

# --- HTML/CSS/JS テンプレート ---

LOADING_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="2.5;url=/login">
    <title>TMHKchatへようこそ</title>
    <style>
        body { display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #2c3e50; }
        h1 { color: #ecf0f1; font-size: 4em; }
    </style>
</head>
<body><h1>TMHKchat</h1></body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TMHKchat - ログイン</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <style>
        body { background: #f7f7f7; }
        .login-container { max-width: 400px; margin: 100px auto; padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
<div class="login-container">
    <h2 class="text-center">ログイン</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <form method="POST">
        <div class="form-group">
            <label for="account_type">アカウントタイプ</label>
            <select name="account_type" id="account_type" class="form-control">
                {% for key, value in account_types.items() %}
                <option value="{{ key }}" {% if key == selected_account_type %}selected{% endif %}>{{ value.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="form-group">
            <label for="login_id">ユーザー名またはメールアドレス</label>
            <input type="text" name="login_id" class="form-control" required>
        </div>
        <div class="form-group">
            <label for="password">パスワード</label>
            <input type="password" name="password" class="form-control" required>
        </div>
        <div class="form-group form-check">
            <input type="checkbox" name="remember" class="form-check-input" id="remember">
            <label class="form-check-label" for="remember">ログインしたままにする</label>
        </div>
        <button type="submit" class="btn btn-primary btn-block">ログイン</button>
    </form>
    <p class="text-center mt-3">アカウントをお持ちでないですか？ <a href="/register">新規登録</a></p>
</div>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TMHKchat - 新規登録</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
     <style>
        body { background: #f7f7f7; }
        .register-container { max-width: 400px; margin: 100px auto; padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
<div class="register-container">
    <h2 class="text-center">新規登録</h2>
     {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <form method="POST">
        <div class="form-group">
            <label for="account_type">アカウントタイプ</label>
            <select name="account_type" id="account_type" class="form-control">
                {% for key, value in account_types.items() %}
                <option value="{{ key }}" {% if key == selected_account_type %}selected{% endif %}>{{ value.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="form-group">
            <label for="username">ユーザー名</label>
            <input type="text" name="username" class="form-control" required>
        </div>
        <div class="form-group">
            <label for="email">メールアドレス (任意)</label>
            <input type="email" name="email" class="form-control">
        </div>
        <div class="form-group">
            <label for="password">パスワード</label>
            <input type="password" name="password" class="form-control" required>
        </div>
        <button type="submit" class="btn btn-success btn-block">登録</button>
    </form>
    <p class="text-center mt-3">既にアカウントをお持ちですか？ <a href="/login">ログイン</a></p>
</div>
</body>
</html>
"""

MAIN_APP_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TMHKchat</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <style>
        body { background: {{ theme.bg_gradient }}; }
        .app-container { max-width: 600px; margin: 0 auto; background: #fff; height: 100vh; display: flex; flex-direction: column; }
        .main-content { flex: 1; overflow-y: auto; }
        .tab-content { display: none; } .tab-content.active { display: block; }
        .service-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center; padding: 1rem; }
        .service-grid a { color: inherit; text-decoration: none; }
        .service-item i { font-size: 2rem; color: #007bff; }
        .service-item span { font-size: 0.8rem; }
        .tab-navigation { border-top: 1px solid #ddd; }
    </style>
</head>
<body>
<div class="app-container">
    <header class="d-flex justify-content-between align-items-center p-3 border-bottom">
        <h1 id="header-title" class="h4 mb-0">ホーム</h1>
        <div>
            <a href="{{ url_for('friends_page') }}" class="btn btn-light"><i class="bi bi-person-plus"></i></a>
            <a href="{{ url_for('settings_page') }}" class="btn btn-light"><i class="bi bi-gear"></i></a>
        </div>
    </header>

    <main class="main-content p-3">
        <!-- ホームタブ -->
        <section id="home-tab" class="tab-content active">
            <a href="{{ url_for('profile_edit_page') }}" class="text-dark">
                <div class="d-flex align-items-center mb-4">
                    <img src="{{ url_for('static', filename='assets/uploads/profile_images/' + current_user.profile_image if 'user' in current_user.profile_image else 'assets/images/' + current_user.profile_image) }}" alt="avatar" class="rounded-circle" width="60" height="60">
                    <div class="ml-3">
                        <h5 class="mb-0">{{ current_user.username }}</h5>
                        <p class="text-muted mb-0">{{ current_user.status_message }}</p>
                    </div>
                </div>
            </a>
            <div class="service-grid">
                <a href="{{ url_for('profile_edit_page') }}"><div class="service-item"><i class="bi bi-person-circle"></i><span>マイプロフィール</span></div></a>
                <a href="{{ url_for('friends_page') }}"><div class="service-item"><i class="bi bi-people-fill"></i><span>友達リスト</span></div></a>
                <a href="{{ url_for('games_hub') }}"><div class="service-item"><i class="bi bi-controller"></i><span>ミニゲーム</span></div></a>
                <a href="{{ url_for('settings_page') }}"><div class="service-item"><i class="bi bi-gear-fill"></i><span>設定</span></div></a>
                <a href="{{ url_for('friends_page') }}"><div class="service-item"><i class="bi bi-person-plus-fill"></i><span>友達追加</span></div></a>
                <a href="{{ url_for('stamps_page') }}"><div class="service-item"><i class="bi bi-emoji-smile-fill"></i><span>スタンプ</span></div></a>
                <a href="{{ url_for('ai_chat_page') }}"><div class="service-item"><i class="bi bi-robot"></i><span>AIボット</span></div></a>
                <a href="{{ url_for('survey_page') }}"><div class="service-item"><i class="bi bi-clipboard-check"></i><span>アンケート</span></div></a>
                <a href="{{ url_for('youtube_redirect') }}" target="_blank"><div class="service-item"><i class="bi bi-youtube" style="color:red;"></i><span>YouTube</span></div></a>
                <a href="{{ url_for('gmail_redirect') }}" target="_blank"><div class="service-item"><i class="bi bi-envelope-fill" style="color:grey;"></i><span>Gmail</span></div></a>
                <a href="{{ url_for('announcements_page') }}"><div class="service-item"><i class="bi bi-megaphone-fill"></i><span>お知らせ</span></div></a>
                <a href="{{ url_for('keep_memo') }}"><div class="service-item"><i class="bi bi-journal-check"></i><span>キープメモ</span></div></a>
            </div>
            <h5><i class="bi bi-star-fill text-warning"></i> お気に入り</h5>
            <ul class="list-group mb-4">{% for friend in favorite_friends %}<a href="{{ url_for('start_chat_with', user_id=friend.id) }}" class="list-group-item">{{ friend.username }}</a>{% else %}<li class="list-group-item">お気に入りの友達はいません。</li>{% endfor %}</ul>
            <h5><i class="bi bi-people"></i> 友達</h5>
            <ul class="list-group">{% for friend in normal_friends %}<a href="{{ url_for('start_chat_with', user_id=friend.id) }}" class="list-group-item">{{ friend.username }}</a>{% else %}<li class="list-group-item">友達はいません。</li>{% endfor %}</ul>
        </section>
        
        <!-- トークタブ -->
        <section id="talk-tab" class="tab-content">
            <h3>トーク</h3>
             <ul class="list-group">
                {% for talk in talks_list %}
                <a href="{{ url_for('start_chat_with', user_id=talk.partner_id) }}" class="list-group-item list-group-item-action">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">{{ talk.partner_name }}</h5>
                        <small>{{ talk.last_message_time }}</small>
                    </div>
                    <p class="mb-1">{{ talk.last_message_content[:30] }}...</p>
                    {% if talk.unread_count > 0 %}<span class="badge badge-danger badge-pill">{{ talk.unread_count }}</span>{% endif %}
                </a>
                {% else %}
                <li class="list-group-item">トーク履歴がありません。</li>
                {% endfor %}
            </ul>
        </section>

        <!-- タイムラインタブ -->
        <section id="timeline-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h2>タイムライン</h2>
                <a href="{{ url_for('timeline') }}" class="btn btn-primary">投稿・閲覧</a>
            </div>
            <p>友達の最新の投稿をチェックしましょう。</p>
        </section>

        <!-- その他タブ -->
        <section id="other-tab" class="tab-content">
             <h2>その他</h2>
            <div class="list-group">
                <a href="{{ url_for('settings_page') }}" class="list-group-item list-group-item-action">設定</a>
                <a href="{{ url_for('logout') }}" class="list-group-item list-group-item-action text-danger">ログアウト</a>
            </div>
        </section>
    </main>

    <nav class="tab-navigation d-flex justify-content-around p-2 bg-light">
        <button data-tab="home-tab" class="nav-button btn btn-link active"><i class="bi bi-house-door-fill"></i><div>ホーム</div></button>
        <button data-tab="talk-tab" class="nav-button btn btn-link"><i class="bi bi-chat-fill"></i><div>トーク</div></button>
        <button data-tab="timeline-tab" class="nav-button btn btn-link"><i class="bi bi-clock-history"></i><div>タイムライン</div></button>
        <button data-tab="other-tab" class="nav-button btn btn-link"><i class="bi bi-three-dots"></i><div>その他</div></button>
    </nav>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const navButtons = document.querySelectorAll('.nav-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const headerTitle = document.getElementById('header-title');
    const tabTitles = {'home-tab': 'ホーム', 'talk-tab': 'トーク', 'timeline-tab': 'タイムライン', 'other-tab': 'その他'};

    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(targetTab).classList.add('active');
            headerTitle.textContent = tabTitles[targetTab] || 'TMHKchat';
        });
    });
});
</script>
</body>
</html>
"""

TIMELINE_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>タイムライン - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container mt-4">
    <a href="{{ url_for('main_app') }}">&laquo; 戻る</a>
    <h2 class="my-4">タイムライン</h2>

    <!-- 情報パネル -->
    <div class="card mb-4">
        <div class="card-header">リアルタイム情報</div>
        <div class="card-body">
            <p><strong>天気:</strong> {% for w in weather_data %}{{ w.data }} {% endfor %}</p>
            <p><strong>交通:</strong> {{ traffic.data if traffic else '情報なし' }}</p>
            <p><strong>災害:</strong> {{ disaster.data if disaster else '情報なし' }}</p>
        </div>
    </div>

    <!-- 投稿フォーム -->
    <div class="card mb-4">
        <div class="card-body">
            <form action="{{ url_for('post_timeline') }}" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <textarea name="content" class="form-control" rows="3" placeholder="今なにしてる？"></textarea>
                </div>
                <div class="form-group">
                    <input type="file" name="media" class="form-control-file">
                </div>
                <button type="submit" class="btn btn-primary">投稿</button>
            </form>
        </div>
    </div>

    <!-- 投稿一覧 -->
    {% for post in posts %}
    <div class="card mb-3">
        <div class="card-body">
            <div class="d-flex align-items-start">
                <img src="{{ url_for('static', filename='assets/uploads/profile_images/' + post.profile_image if 'user' in post.profile_image else 'assets/images/' + post.profile_image) }}" class="rounded-circle mr-3" width="50" height="50">
                <div>
                    <h5 class="card-title mb-1">{{ post.username }}</h5>
                    <p class="card-text">{{ post.content | nl2br }}</p>
                    {% if post.media_url %}
                    <img src="{{ url_for('static', filename='assets/uploads/' + post.media_url) }}" class="img-fluid rounded">
                    {% endif %}
                    <small class="text-muted">{{ post.created_at }}</small>
                </div>
            </div>
        </div>
    </div>
    {% else %}
    <p>まだ投稿がありません。</p>
    {% endfor %}
</div>
</body>
</html>
"""

# --- ここから変更 ---
GAMES_HUB_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ミニゲームハブ - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container mt-4">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-3"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4"><i class="bi bi-controller"></i> ミニゲームハブ</h1>

    <!-- ゲーム一覧 -->
    <h2 class="h4">ゲームを選択</h2>
    <div class="list-group mb-5">
        {% for game in games %}
        <div class="list-group-item">
            <div class="d-flex w-100 justify-content-between">
                <h5 class="mb-1"><i class="{{ game.icon }}"></i> {{ game.name }}</h5>
                <button class="btn btn-primary play-game-btn" data-game-type="{{ game.id }}">プレイ</button>
            </div>
            <p class="mb-1">{{ game.description }}</p>
            <small>プレイ人数: {{ game.players }}</small>
        </div>
        {% endfor %}
    </div>

    <!-- ランキング -->
    <h2 class="h4">🏆 ランキング</h2>
    <table class="table table-striped">
        <thead class="thead-dark">
            <tr>
                <th>順位</th>
                <th>ユーザー名</th>
                <th>ゲーム</th>
                <th>ハイスコア</th>
            </tr>
        </thead>
        <tbody>
            {% for rank in rankings %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ rank.username }}</td>
                <td>{{ rank.game_type }}</td>
                <td>{{ rank.high_score }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="4" class="text-center">まだプレイ記録がありません。</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const playButtons = document.querySelectorAll('.play-game-btn');
    playButtons.forEach(button => {
        button.addEventListener('click', function() {
            const gameType = this.dataset.gameType;
            
            // サーバーにゲームルーム作成をリクエスト
            fetch('/game/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'game_type': gameType,
                    'max_players': '4', // デフォルト値
                    'with_cpu': 'true'   // デフォルト値
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.room_id) {
                    // ゲームルームに遷移
                    window.location.href = '/game/' + data.room_id;
                } else {
                    alert('ゲームルームの作成に失敗しました。');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('エラーが発生しました。');
            });
        });
    });
});
</script>
</body>
</html>
"""

GAME_DAIFUGO_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大富豪 - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        body { background-color: #f0f0f0; }
        .game-board { background-color: #006400; color: white; padding: 20px; border-radius: 10px; max-width: 800px; margin: auto; }
        .player-area { border: 2px solid #fff; border-radius: 8px; padding: 10px; margin-bottom: 15px; min-height: 120px; background-color: rgba(255,255,255,0.1); }
        .player-area.current-turn { box-shadow: 0 0 15px #ffc107; border-color: #ffc107; }
        .my-hand .card { display: inline-block; cursor: pointer; border: 2px solid #333; border-radius: 5px; padding: 10px 5px; margin: 2px; background-color: #fff; color: #000; user-select: none; font-weight: bold; min-width: 40px; text-align: center; }
        .my-hand .card.selected { border-color: #ffc107; transform: translateY(-10px); }
        .field { min-height: 100px; background-color: rgba(0,0,0,0.2); border-radius: 10px; display: flex; justify-content: center; align-items: center; padding: 10px; flex-wrap: wrap; }
        .game-log { height: 100px; overflow-y: scroll; background: #fff; color: #000; padding: 8px; border-radius: 5px; font-size: 0.9em; }
        .action-buttons button { margin: 5px; }
    </style>
</head>
<body>
<div class="container my-4">
    <div class="game-board">
        <h2 class="text-center">大富豪 <small>(ルームID: {{ room_id }})</small></h2>
        <a href="{{ url_for('games_hub') }}" class="btn btn-sm btn-light mb-3"><i class="bi bi-arrow-left"></i> ゲームハブに戻る</a>
        {% if room.host == current_user.id and room.status == 'waiting' %}
        <button id="start-game-btn" class="btn btn-success mb-3">ゲーム開始</button>
        {% endif %}

        <!-- 対戦相手エリア -->
        <div id="opponents-area" class="row text-center"></div>

        <!-- 中央の場 -->
        <div id="field" class="field my-3">
            <p class="mb-0">ゲーム待機中...</p>
        </div>

        <!-- 自分のエリア -->
        <div id="player-area-{{ current_user.id }}" class="player-area my-area">
            <h6>{{ current_user.username }} (あなた) <span id="my-card-count" class="badge badge-light"></span></h6>
            <div id="my-hand" class="my-hand"></div>
            <div class="action-buttons mt-2">
                <button id="play-btn" class="btn btn-warning" disabled>選択したカードを出す</button>
                <button id="pass-btn" class="btn btn-secondary" disabled>パス</button>
            </div>
        </div>
        
        <h6>ゲームログ</h6>
        <div id="game-log" class="game-log"></div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const roomId = "{{ room_id }}";
    const currentUserId = {{ current_user.id }};

    const myHandDiv = document.getElementById('my-hand');
    const opponentsArea = document.getElementById('opponents-area');
    const fieldDiv = document.getElementById('field');
    const gameLog = document.getElementById('game-log');
    const playBtn = document.getElementById('play-btn');
    const passBtn = document.getElementById('pass-btn');
    const startGameBtn = document.getElementById('start-game-btn');

    // --- イベントリスナー ---
    if(startGameBtn) {
        startGameBtn.addEventListener('click', () => {
            socket.emit('start_game', { room_id: roomId });
            startGameBtn.style.display = 'none';
        });
    }

    myHandDiv.addEventListener('click', (event) => {
        if (event.target.classList.contains('card')) {
            // シングルプレイなので、他の選択は解除
            document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
            event.target.classList.toggle('selected');
        }
    });

    playBtn.addEventListener('click', () => {
        const selectedCards = document.querySelectorAll('.card.selected');
        if (selectedCards.length === 1) {
            const card = selectedCards[0];
            socket.emit('play_cards', {
                room_id: roomId,
                card: { suit: card.dataset.suit, rank: card.dataset.rank }
            });
        }
    });

    passBtn.addEventListener('click', () => {
        socket.emit('pass_turn', { room_id: roomId });
    });

    // --- SocketIO ハンドラ ---
    socket.on('connect', () => {
        socket.emit('join_game', { room_id: roomId }); // ゲームルームに参加
    });

    socket.on('game_started', (data) => {
        renderMyHand(data.your_hand);
    });

    socket.on('update_game_state', (data) => {
        renderOpponents(data.players);
        renderField(data.field);
        updateTurnIndicator(data.current_turn);
        
        const myPlayerInfo = data.players.find(p => p.id === currentUserId);
        if (myPlayerInfo) {
            document.getElementById('my-card-count').innerText = myPlayerInfo.card_count + '枚';
            // 自分の手札を更新
            if (data.your_hand) {
                renderMyHand(data.your_hand);
            }
        }
    });
    
    socket.on('invalid_move', (data) => {
        alert(data.message);
    });

    socket.on('log_message', (data) => {
        addLogMessage(data.message);
    });

    socket.on('game_over', (data) => {
        alert(`ゲーム終了！勝者: ${data.winner}`);
        playBtn.disabled = true;
        passBtn.disabled = true;
    });

    // --- 描画関数 ---
    function renderMyHand(hand) {
        myHandDiv.innerHTML = '';
        hand.forEach(card => {
            const cardDiv = document.createElement('div');
            cardDiv.classList.add('card');
            cardDiv.textContent = `${card.suit}${card.rank}`;
            cardDiv.dataset.suit = card.suit;
            cardDiv.dataset.rank = card.rank;
            myHandDiv.appendChild(cardDiv);
        });
    }

    function renderOpponents(players) {
        opponentsArea.innerHTML = '';
        players.forEach(p => {
            if (p.id !== currentUserId) {
                const opponentCol = document.createElement('div');
                opponentCol.className = 'col';
                opponentCol.innerHTML = `
                    <div id="player-area-${p.id}" class="player-area opponent-area">
                        <h6>${p.name}</h6>
                        <div><i class="bi bi-person-badge"></i> <span>残り: ${p.card_count}枚</span></div>
                    </div>`;
                opponentsArea.appendChild(opponentCol);
            }
        });
    }

    function renderField(fieldCards) {
        fieldDiv.innerHTML = '';
        if (fieldCards.length === 0) {
            fieldDiv.innerHTML = '<p class="mb-0">カードが出されていません</p>';
        } else {
            fieldCards.forEach(card => {
                const cardDiv = document.createElement('div');
                cardDiv.className = 'card';
                cardDiv.textContent = `${card.suit}${card.rank}`;
                fieldDiv.appendChild(cardDiv);
            });
        }
    }

    function updateTurnIndicator(currentTurnId) {
        document.querySelectorAll('.player-area').forEach(area => area.classList.remove('current-turn'));
        const turnArea = document.getElementById(`player-area-${currentTurnId}`);
        if (turnArea) {
            turnArea.classList.add('current-turn');
        }
        
        if (currentTurnId === currentUserId) {
            playBtn.disabled = false;
            passBtn.disabled = false;
        } else {
            playBtn.disabled = true;
            passBtn.disabled = true;
        }
    }

    function addLogMessage(message) {
        const p = document.createElement('p');
        p.className = 'mb-1';
        p.textContent = message;
        gameLog.appendChild(p);
        gameLog.scrollTop = gameLog.scrollHeight; // 自動スクロール
    }
});
</script>
</body>
</html>
"""
# --- Game Helper Functions (Daifugo) ---
def create_deck():
    """大富豪用のデッキを作成してシャッフルする"""
    suits = ['♠', '♦', '♥', '♣']
    ranks = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
    values = {rank: i for i, rank in enumerate(ranks)}
    # Jokerを追加
    deck = [{'suit': suit, 'rank': rank, 'value': values[rank]} for suit in suits for rank in ranks]
    deck.append({'suit': 'Joker', 'rank': 'Joker', 'value': 99})
    random.shuffle(deck)
    return deck

def deal_cards(players, deck):
    """プレイヤーにカードを配る"""
    hands = {p['id']: [] for p in players}
    player_ids = [p['id'] for p in players]
    i = 0
    for card in deck:
        hands[player_ids[i % len(player_ids)]].append(card)
        i += 1
    # 各プレイヤーの手札をカードの強さでソート
    for pid in hands:
        hands[pid] = sorted(hands[pid], key=lambda c: c['value'])
    return hands

# --- SocketIO Game Event Handlers ---

# [追加] ゲームルームに参加するためのハンドラ
@socketio.on('join_game')
@login_required
def handle_join_game(data):
    room_id = data['room_id']
    if room_id in game_rooms:
        join_room(room_id)
        print(f"User {current_user.username} joined game room {room_id}")

@socketio.on('start_game')
@login_required
def handle_start_game(data):
    room_id = data['room_id']
    if room_id in game_rooms and game_rooms[room_id]['host'] == current_user.id:
        room = game_rooms[room_id]
        if room['status'] != 'waiting': return
            
        room['status'] = 'playing'
        room['player_map'] = {p['id']: p['name'] for p in room['players']}
        
        game_type = room.get('type')
        
        if game_type == 'daifugo':
            deck = create_deck()
            room['hands'] = deal_cards(room['players'], deck)
            room['field'] = []
            room['turn_order'] = [p['id'] for p in room['players']]
            room['current_turn_index'] = 0
            room['pass_count'] = 0

        elif game_type == 'babanuki':
            suits = ['♠', '♦', '♥', '♣']
            ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
            values = {rank: i for i, rank in enumerate(ranks)}
            deck = [{'suit': s, 'rank': r, 'value': values[r]} for s in suits for r in ranks]
            deck.append({'suit': 'Joker', 'rank': 'Joker', 'value': 99})
            random.shuffle(deck)
            hands = {p['id']: [] for p in room['players']}
            player_ids = [p['id'] for p in room['players']]
            i = 0
            for card in deck:
                hands[player_ids[i % len(player_ids)]].append(card)
                i += 1
            for p_id in hands:
                hand = hands[p_id]
                ranks_in_hand = [c['rank'] for c in hand]
                pairs = {rank for rank in ranks_in_hand if ranks_in_hand.count(rank) >= 2}
                for rank in pairs:
                    indices_to_remove = [i for i, c in enumerate(hand) if c['rank'] == rank][:2]
                    for index in sorted(indices_to_remove, reverse=True): del hand[index]
            room['hands'] = hands
            room['turn_order'] = [p['id'] for p in room['players']]
            room['current_turn_index'] = 0
        
        elif game_type == 'quiz':
            # AIが生成したクイズがあればそれを使う、なければデフォルト
            if 'questions' not in room or not room['questions']:
                room['questions'] = [
                    {'q': '日本の首都は？', 'options': ['大阪', '京都', '東京', '名古屋'], 'correct': '東京'},
                    {'q': '一番大きな惑星は？', 'options': ['地球', '火星', '木星', '土星'], 'correct': '木星'},
                    {'q': '1年は何日？', 'options': ['365日', '300日', '400日', '500日'], 'correct': '365日'}
                ]
            room['question_index'] = 0
            room['scores'] = {p['id']: 0 for p in room['players']}
            handle_next_question(room_id)
            return
            
        elif game_type == 'shiritori':
            room['used_words'] = []
            room['last_char'] = ''
            room['turn_order'] = [p['id'] for p in room['players']]
            room['current_turn_index'] = 0

        if 'hands' in room:
            for player in room['players']:
                if not player.get('is_cpu', False):
                    player_id = player['id']
                    if player_id in online_users:
                        player_sid = online_users[player_id]['sid']
                        emit('game_started', {'your_hand': room['hands'][player_id]}, room=player_sid)

        players_info = [{'id': p['id'], 'name': p['name'], 'card_count': len(room.get('hands', {}).get(p['id'], []))} for p in room['players']]
        
        emit('update_game_state', {
            'players': players_info,
            'field': room.get('field', []),
            'current_turn': room['turn_order'][room['current_turn_index']],
            'current_word': '',
            'used_words': [],
        }, room=room_id)
        emit('log_message', {'message': f'{game_type.capitalize()}が開始されました！'}, room=room_id)

# [追加] イベントハンドラとして登録
@socketio.on('play_cards')
@login_required
def handle_play_cards(data):
    room_id = data['room_id']
    played_card = data['card'] # 今回はカード1枚を想定
    
    if room_id not in game_rooms: return
    room = game_rooms[room_id]
    
    # 自分のターンかチェック
    if room['turn_order'][room['current_turn_index']] != current_user.id:
        emit('invalid_move', {'message': 'あなたのターンではありません。'}, room=request.sid)
        return

    # 簡単なバリデーション (手札にあるか、場に出せるか)
    # 1. 手札にあるか
    hand = room['hands'][current_user.id]
    card_in_hand = next((c for c in hand if c['rank'] == played_card['rank'] and c['suit'] == played_card['suit']), None)
    
    if not card_in_hand:
        emit('invalid_move', {'message': 'そのカードは持っていません。'}, room=request.sid)
        return

    # 2. 場に出せるか (場のカードより強いか)
    if room['field'] and card_in_hand['value'] <= room['field'][-1]['value']:
        emit('invalid_move', {'message': '場に出ているカードより強いカードを出してください。'}, room=request.sid)
        return
        
    # カードを出す処理
    room['hands'][current_user.id].remove(card_in_hand)
    room['field'] = [card_in_hand] # 場をリセットして新しいカードを置く
    room['pass_count'] = 0

    # 勝利判定
    if not room['hands'][current_user.id]:
        emit('game_over', {'winner': current_user.username}, room=room_id)
        room['status'] = 'finished'
        return

    # 次のターンへ
    room['current_turn_index'] = (room['current_turn_index'] + 1) % len(room['turn_order'])
    
    # 全員にゲーム状態を更新
    players_info = [{'id': p['id'], 'name': p['name'], 'card_count': len(room['hands'][p['id']])} for p in room['players']]
    emit('update_game_state', {
        'players': players_info,
        'field': room['field'],
        'current_turn': room['turn_order'][room['current_turn_index']],
        'your_hand': room['hands'][current_user.id] # 自分の手札情報も送る
    }, room=room_id)
    emit('log_message', {'message': f"{current_user.username} が {card_in_hand['suit']}{card_in_hand['rank']} を出しました。"}, room=room_id)


@socketio.on('pass_turn')
@login_required
def handle_pass_turn(data):
    room_id = data['room_id']
    if room_id not in game_rooms: return
    room = game_rooms[room_id]

    if room['turn_order'][room['current_turn_index']] != current_user.id:
        emit('invalid_move', {'message': 'あなたのターンではありません。'}, room=request.sid)
        return

    room['pass_count'] += 1
    
    # 全員がパスしたら場を流す
    if room['pass_count'] >= len(room['players']) - 1:
        room['field'] = []
        room['pass_count'] = 0
        emit('log_message', {'message': '場が流れました。'}, room=room_id)
    else:
        emit('log_message', {'message': f"{current_user.username} がパスしました。"}, room=room_id)


    # 次のターンへ
    room['current_turn_index'] = (room['current_turn_index'] + 1) % len(room['turn_order'])
    
    players_info = [{'id': p['id'], 'name': p['name'], 'card_count': len(room['hands'][p['id']])} for p in room['players']]
    emit('update_game_state', {
        'players': players_info,
        'field': room['field'],
        'current_turn': room['turn_order'][room['current_turn_index']],
    }, room=room_id)

@socketio.on('send_ai_message')
@login_required
def handle_send_ai_message(data):
    user_message = data['message']
    if not user_message:
        return

    # ユーザーのメッセージをDBに保存
    db = get_db()
    db.execute('INSERT INTO private_messages (sender_id, recipient_id, content, is_from_ai) VALUES (?, 0, ?, 0)',
               (current_user.id, user_message))
    db.commit()

    if not ai_model:
        emit('ai_response', {'message': 'AI機能は現在利用できません。'}, room=request.sid)
        return

    try:
        # Gemini Pro APIにリクエストを送信
        response = ai_model.generate_content(user_message)
        ai_response_text = response.text
    except Exception as e:
        print(f"AI API Error: {e}")
        ai_response_text = "申し訳ありません、エラーが発生しました。"

    # AIの返信をDBに保存
    db.execute('INSERT INTO private_messages (sender_id, recipient_id, content, is_from_ai) VALUES (0, ?, ?, 1)',
               (current_user.id, ai_response_text))
    db.commit()
    
    # クライアントにAIの返信を送信
    emit('ai_response', {'message': ai_response_text}, room=request.sid)

@socketio.on('janken_move')
@login_required
def handle_janken_move(data):
    room_id = data['room_id']
    move = data['move']
    if room_id not in game_rooms or game_rooms[room_id]['type'] != 'janken':
        return

    room = game_rooms[room_id]
    
    # movesプロパティがなければ初期化
    if 'moves' not in room:
        room['moves'] = {}

    # プレイヤーの選択を保存
    room['moves'][current_user.id] = move
    emit('player_moved', {'player_id': current_user.id}, room=room_id)

    # 全員の手が出揃ったか確認 (CPUは即座に応答)
    human_players = [p for p in room['players'] if not p['is_cpu']]
    cpu_players = [p for p in room['players'] if p['is_cpu']]

    # CPUの手を決定
    for cpu in cpu_players:
        if cpu['id'] not in room['moves']:
            room['moves'][cpu['id']] = random.choice(['rock', 'paper', 'scissors'])
    
    # 全員の手が出揃ったら結果を判定
    if len(room['moves']) == len(room['players']):
        player_id = human_players[0]['id']
        opponent_id = room['players'][1]['id'] # 2人対戦を想定

        player_move = room['moves'][player_id]
        opponent_move = room['moves'][opponent_id]
        
        # 勝敗判定
        winner = None
        if player_move == opponent_move:
            result_text = "あいこ"
        elif (player_move == 'rock' and opponent_move == 'scissors') or \
             (player_move == 'scissors' and opponent_move == 'paper') or \
             (player_move == 'paper' and opponent_move == 'rock'):
            result_text = f"{room['players'][0]['name']} の勝ち！"
            winner = player_id
        else:
            result_text = f"{room['players'][1]['name']} の勝ち！"
            winner = opponent_id
            
        # 結果を全員に送信
        emit('janken_result', {
            'moves': room['moves'],
            'result_text': result_text,
            'winner_id': winner
        }, room=room_id)
        
        # 次のラウンドのために手をリセット
        room['moves'] = {}

# --- Babanuki & Amidakuji Event Handlers ---

# [修正] ターン管理のロジックを修正
@socketio.on('draw_card')
@login_required
def handle_draw_card(data):
    room_id = data['room_id']
    target_player_id = int(data['target_player_id'])
    
    if room_id not in game_rooms or game_rooms[room_id]['type'] != 'babanuki': return
    room = game_rooms[room_id]
    
    current_player_id = room['turn_order'][room['current_turn_index']]
    if current_player_id != current_user.id:
        return emit('invalid_move', {'message': 'あなたのターンではありません。'}, room=request.sid)

    target_hand = room['hands'][target_player_id]
    if not target_hand:
        return emit('invalid_move', {'message': '相手の手札がありません。'}, room=request.sid)
    
    drawn_card = target_hand.pop(random.randrange(len(target_hand)))
    my_hand = room['hands'][current_user.id]
    my_hand.append(drawn_card)
    
    ranks_in_hand = [c['rank'] for c in my_hand]
    pairs = {rank for rank in ranks_in_hand if ranks_in_hand.count(rank) >= 2}
    
    discarded_cards = []
    if pairs:
        for rank in pairs:
            card1_index = next(i for i, c in enumerate(my_hand) if c['rank'] == rank)
            card1 = my_hand.pop(card1_index)
            card2_index = next(i for i, c in enumerate(my_hand) if c['rank'] == rank)
            card2 = my_hand.pop(card2_index)
            discarded_cards.extend([card1, card2])

    room['hands'][current_user.id] = sorted(my_hand, key=lambda c: c['value'])
    
    log_msg = f"{current_user.username}が{room['player_map'][target_player_id]}からカードを1枚引きました。"
    if discarded_cards:
        log_msg += f" {discarded_cards[0]['rank']}のペアを捨てました。"
    emit('log_message', {'message': log_msg}, room=room_id)

    # 上がったプレイヤーをチェック
    finished_players = []
    if not room['hands'][current_user.id]:
        finished_players.append(current_user.id)
        emit('log_message', {'message': f"{current_user.username}があがりました！"}, room=room_id)
    if not room['hands'][target_player_id]:
        finished_players.append(target_player_id)
        emit('log_message', {'message': f"{room['player_map'][target_player_id]}があがりました！"}, room=room_id)
        
    if finished_players:
        # ターン順から上がったプレイヤーを削除
        original_turn_order_len = len(room['turn_order'])
        room['turn_order'] = [p_id for p_id in room['turn_order'] if p_id not in finished_players]
        # 自分のターンが削除された場合、インデックスを調整
        if original_turn_order_len > len(room['turn_order']):
             room['current_turn_index'] = room['turn_order'].index(current_player_id) if current_player_id in room['turn_order'] else room['current_turn_index']

    # ゲーム終了判定
    if len(room['turn_order']) <= 1:
        loser = room['turn_order'][0] if room['turn_order'] else '不明'
        emit('game_over', {'winner': '全員', 'loser': room['player_map'].get(loser)}, room=room_id)
        room['status'] = 'finished'
        return

    # 次のターンへ
    room['current_turn_index'] = (room['current_turn_index'] + 1) % len(room['turn_order'])
    
    players_info = [{'id': p['id'], 'name': p['name'], 'card_count': len(room['hands'][p['id']])} for p in room['players']]
    emit('update_game_state', {
        'players': players_info,
        'current_turn': room['turn_order'][room['current_turn_index']],
    }, room=room_id)
    if current_user.id in online_users:
        emit('update_hand', {'hand': room['hands'][current_user.id]}, room=online_users[current_user.id]['sid'])


@socketio.on('setup_amida')
@login_required
def handle_setup_amida(data):
    room_id = data['room_id']
    items = data['items']
    if room_id not in game_rooms or game_rooms[room_id]['host'] != current_user.id:
        return
    room = game_rooms[room_id]
    room['amida_items'] = items
    emit('amida_updated', {'items': items}, room=room_id)
    emit('log_message', {'message': 'くじの内容が設定されました。'}, room=room_id)


@socketio.on('start_amida')
@login_required
def handle_start_amida(data):
    room_id = data['room_id']
    if room_id not in game_rooms or game_rooms[room_id]['host'] != current_user.id:
        return
    room = game_rooms[room_id]
    
    players = room['players']
    items = room.get('amida_items', ['ハズレ'] * len(players))
    
    # 結果をシャッフルして決定
    random.shuffle(items)
    
    results = {player['id']: item for player, item in zip(players, items)}
    room['amida_results'] = results
    
    emit('amida_result', {'results': results}, room=room_id)
    emit('log_message', {'message': 'あみだくじの結果が出ました！'}, room=room_id)


# --- ここまで変更 ---

FRIENDS_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>友達管理 - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4"><i class="bi bi-people-fill"></i> 友達管理</h1>

    <!-- ユーザー検索 -->
    <div class="card mb-4">
        <div class="card-header">ユーザーを探す</div>
        <div class="card-body">
            <form method="POST" action="{{ url_for('friends_page') }}">
                <div class="input-group">
                    <input type="text" name="query" class="form-control" placeholder="ユーザー名で検索" value="{{ query or '' }}">
                    <div class="input-group-append">
                        <button class="btn btn-outline-primary" type="submit"><i class="bi bi-search"></i> 検索</button>
                    </div>
                </div>
            </form>
            {% if search_results %}
            <ul class="list-group mt-3">
                {% for user in search_results %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    {{ user.username }}
                    <a href="{{ url_for('send_request', recipient_id=user.id) }}" class="btn btn-sm btn-success">
                        <i class="bi bi-person-plus"></i> リクエスト送信
                    </a>
                </li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
    </div>
    
    <!-- 友達リクエスト -->
    {% if friend_requests %}
    <div class="card mb-4">
        <div class="card-header">届いたリクエスト</div>
        <ul class="list-group list-group-flush">
            {% for req in friend_requests %}
            <li class="list-group-item d-flex justify-content-between align-items-center">
                {{ req.username }}
                <div>
                    <a href="{{ url_for('accept_request', sender_id=req.id) }}" class="btn btn-sm btn-primary">承認</a>
                    <!-- 拒否機能は後で実装 -->
                </div>
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    <!-- 友達リスト -->
    <div class="card mb-4">
        <div class="card-header">友達リスト</div>
        <ul class="list-group list-group-flush">
            {% for friend in friends_list %}
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    {% if friend.status == 'favorite' %}
                        <i class="bi bi-star-fill text-warning"></i>
                    {% endif %}
                    {{ friend.username }}
                </div>
                <div>
                    <a href="{{ url_for('start_chat_with', user_id=friend.id) }}" class="btn btn-sm btn-info" title="チャット"><i class="bi bi-chat-dots"></i></a>
                    <a href="{{ url_for('toggle_favorite', friend_id=friend.id) }}" class="btn btn-sm btn-outline-warning" title="お気に入り切替"><i class="bi bi-star"></i></a>
                </div>
            </li>
            {% else %}
            <li class="list-group-item">まだ友達がいません。</li>
            {% endfor %}
        </ul>
    </div>
    
    <!-- URL招待 -->
    <div class="card">
        <div class="card-header">URLで招待</div>
        <div class="card-body">
            <p>このリンクを友達に送って招待しよう！</p>
            <div class="input-group">
                <input type="text" id="invite-link" class="form-control" value="{{ invite_link }}" readonly>
                <div class="input-group-append">
                    <button class="btn btn-outline-secondary" onclick="copyLink()"><i class="bi bi-clipboard"></i></button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function copyLink() {
    const linkInput = document.getElementById('invite-link');
    linkInput.select();
    document.execCommand('copy');
    alert('招待リンクをコピーしました！');
}
</script>
</body>
</html>
"""

CHAT_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ opponent.username }}とのチャット - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        body { display: flex; flex-direction: column; height: 100vh; }
        .chat-header { flex-shrink: 0; }
        .chat-container { flex-grow: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column-reverse; }
        .message-bubble { max-width: 70%; padding: 10px 15px; border-radius: 20px; margin-bottom: 10px; word-wrap: break-word; }
        .my-message { background-color: #007bff; color: white; align-self: flex-end; }
        .opponent-message { background-color: #e9e9eb; color: black; align-self: flex-start; }
        .chat-form { flex-shrink: 0; }
    </style>
</head>
<body>
    <header class="chat-header bg-light p-3 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <a href="{{ url_for('main_app') }}" class="btn btn-secondary btn-sm"><i class="bi bi-arrow-left"></i></a>
            <strong class="ml-2">{{ opponent.username }}</strong>
        </div>
    </header>

    <div class="chat-container" id="chat-container">
        <!-- メッセージはJavaScriptで逆順に挿入される -->
        {% for message in messages|reverse %}
            <div class="message-bubble {{ 'my-message' if message.sender_id == current_user.id else 'opponent-message' }}">
                {{ message.content | nl2br }}
            </div>
        {% endfor %}
    </div>

    <form class="chat-form p-3 bg-light border-top" id="message-form">
        <div class="input-group">
            <input type="text" id="message-input" class="form-control" placeholder="メッセージを入力..." autocomplete="off">
            <div class="input-group-append">
                <button class="btn btn-primary" type="submit"><i class="bi bi-send"></i></button>
            </div>
        </div>
    </form>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const form = document.getElementById('message-form');
    const input = document.getElementById('message-input');
    const chatContainer = document.getElementById('chat-container');
    const opponentId = {{ opponent.id }};
    const currentUserId = {{ current_user.id }};

    // フォーム送信時の処理
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (input.value) {
            socket.emit('send_private_message', {
                'recipient_id': opponentId,
                'message': input.value
            });
            input.value = '';
        }
    });

    // 新しいメッセージを受信した時の処理
    socket.on('new_private_message', function(msg) {
        // 自分宛のメッセージか、自分が送信したメッセージのみ表示
        if (msg.sender_id === opponentId || msg.sender_id === currentUserId) {
            const messageBubble = document.createElement('div');
            messageBubble.classList.add('message-bubble');
            
            if (msg.sender_id === currentUserId) {
                messageBubble.classList.add('my-message');
            } else {
                messageBubble.classList.add('opponent-message');
            }
            messageBubble.innerHTML = msg.content.replace(/\\n/g, '<br>');

            // 新しいメッセージをコンテナの「一番上」に追加 (CSSで逆順になっているため)
            chatContainer.insertBefore(messageBubble, chatContainer.firstChild);
        }
    });
});
</script>
</body>
</html>
"""
PROFILE_EDIT_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>プロフィール編集 - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        .profile-img-container {
            position: relative;
            width: 120px;
            height: 120px;
            margin: 0 auto 20px;
        }
        .profile-img-container img {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
        }
        .profile-img-container .upload-label {
            position: absolute;
            bottom: 0;
            right: 0;
            background: #007bff;
            color: white;
            padding: 5px 10px;
            border-radius: 50%;
            cursor: pointer;
        }
        .profile-img-container input[type="file"] {
            display: none;
        }
    </style>
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4">プロフィール編集</h1>

    <form action="{{ url_for('update_settings') }}" method="POST" enctype="multipart/form-data">
        <div class="profile-img-container">
            <img id="image-preview" src="{{ url_for('static', filename='assets/uploads/profile_images/' + user.profile_image if 'user' in user.profile_image else 'assets/images/' + user.profile_image) }}" alt="プロフィール画像">
            <label for="profile_image_upload" class="upload-label"><i class="bi bi-camera-fill"></i></label>
            <input type="file" id="profile_image_upload" name="profile_image" accept="image/*">
        </div>

        <div class="form-group">
            <label for="username">ユーザー名</label>
            <input type="text" class="form-control" id="username" name="username" value="{{ user.username }}" required>
        </div>
        <div class="form-group">
            <label for="email">メールアドレス</label>
            <input type="email" class="form-control" id="email" name="email" value="{{ user.email or '' }}">
        </div>
        <div class="form-group">
            <label for="status_message">ステータスメッセージ</label>
            <input type="text" class="form-control" id="status_message" name="status_message" value="{{ user.status_message or '' }}">
        </div>
        <div class="form-group">
            <label for="bio">自己紹介</label>
            <textarea class="form-control" id="bio" name="bio" rows="3">{{ user.bio or '' }}</textarea>
        </div>
        <div class="form-group">
            <label for="birthday">誕生日</label>
            <input type="date" class="form-control" id="birthday" name="birthday" value="{{ user.birthday or '' }}">
        </div>
        <div class="form-group">
            <label for="account_type">現在のアカウントタイプ</label>
            <input type="text" class="form-control" value="{{ account_types[user.account_type]['name'] }}" readonly>
        </div>

        <hr>
        <h5 class="mt-4">表示設定</h5>
        <div class="form-group form-check">
            <input type="checkbox" class="form-check-input" id="show_typing" name="show_typing" value="1" {% if user.show_typing %}checked{% endif %}>
            <label class="form-check-label" for="show_typing">入力中であることを他のユーザーに表示する</label>
        </div>
        <div class="form-group form-check">
            <input type="checkbox" class="form-check-input" id="show_online_status" name="show_online_status" value="1" {% if user.show_online_status %}checked{% endif %}>
            <label class="form-check-label" for="show_online_status">オンライン状態を表示する</label>
        </div>

        <button type="submit" class="btn btn-primary btn-block mt-4">更新する</button>
    </form>
</div>

<script>
document.getElementById('profile_image_upload').addEventListener('change', function(event) {
    if (event.target.files && event.target.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('image-preview').setAttribute('src', e.target.result);
        }
        reader.readAsDataURL(event.target.files[0]);
    }
});
</script>
</body>
</html>
"""
PROFILE_VIEW_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ user.username }}さんのプロフィール</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        .profile-header {
            /* ここで背景画像を指定しています */
            background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url("{{ url_for('static', filename='assets/images/' + user.background_image) }}");
            background-size: cover;
            background-position: center;
            color: white;
            padding: 40px 20px;
            text-align: center;
            position: relative; /* 子要素の位置決めの基準となります */
        }
        .profile-avatar {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 4px solid white;
            object-fit: cover;
            margin-top: -60px; /* ヘッダーに半分重なるように配置 */
            background: white;
        }
    </style>
</head>
<body>

<div class="container-fluid p-0" style="max-width: 600px; margin: auto; background: #fff;">
    <a href="{{ url_for('main_app') }}" class="btn btn-light m-3" style="position: absolute; z-index: 10; opacity: 0.9;"><i class="bi bi-arrow-left"></i></a>
    
    <div class="profile-header">
        <!-- このdiv自体が背景画像を持ちます -->
    </div>
    
    <div class="text-center">
        <img src="{{ url_for('static', filename='assets/uploads/profile_images/' + user.profile_image if 'user' in user.profile_image else 'assets/images/' + user.profile_image) }}" alt="プロフィール画像" class="profile-avatar">
    </div>

    <div class="container p-4">
        <div class="text-center">
            <h2 class="mb-0">{{ user.username }}</h2>
            <p class="text-muted">{{ user.status_message or '' }}</p>
        </div>

        <div class="my-4 text-center p-3 bg-light rounded">
            <p class="mb-0">{{ user.bio or '自己紹介はまだ設定されていません。' }}</p>
        </div>
        
        <!-- アクションボタン -->
        {% if user.id != current_user.id %}
            <div class="text-center my-4">
                {% if friend_status == 'not_friend' %}
                    <a href="{{ url_for('send_request', recipient_id=user.id) }}" class="btn btn-success"><i class="bi bi-person-plus-fill"></i> 友達リクエストを送る</a>
                {% elif friend_status == 'pending' %}
                    <button class="btn btn-secondary" disabled>リクエスト送信済み</button>
                {% elif friend_status in ['friend', 'favorite'] %}
                    <a href="{{ url_for('start_chat_with', user_id=user.id) }}" class="btn btn-primary"><i class="bi bi-chat-dots-fill"></i> チャットする</a>
                    <a href="{{ url_for('toggle_favorite', friend_id=user.id) }}" class="btn btn-outline-warning ml-2">
                        {% if friend_status == 'favorite' %}
                        <i class="bi bi-star-fill"></i> お気に入り解除
                        {% else %}
                        <i class="bi bi-star"></i> お気に入り登録
                        {% endif %}
                    </a>
                {% endif %}
            </div>
        {% endif %}
        
        <!-- 実績 -->
        <hr>
        <h4 class="mt-4"><i class="bi bi-trophy-fill"></i> 実績</h4>
        <div class="list-group">
        {% for achievement in achievements %}
            <div class="list-group-item {% if achievement.is_unlocked %}list-group-item-success{% endif %}">
                <strong>{{ achievement.achievement_name }}</strong>
                <small class="d-block text-muted">{{ achievement.criteria_description }}</small>
            </div>
        {% else %}
            <p>まだ実績はありません。</p>
        {% endfor %}
        </div>
    </div>
</div>
</body>
</html>
"""
ANNOUNCEMENTS_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>運営からのお知らせ - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4"><i class="bi bi-megaphone-fill"></i> 運営からのお知らせ</h1>

    <div id="announcements-accordion">
    {% for announcement in announcements %}
        <div class="card mb-2">
            <div class="card-header" id="heading-{{ announcement.id }}">
                <h5 class="mb-0">
                    <button class="btn btn-link" data-toggle="collapse" data-target="#collapse-{{ announcement.id }}" aria-expanded="true" aria-controls="collapse-{{ announcement.id }}">
                        {{ announcement.title }}
                    </button>
                    <small class="text-muted float-right">{{ announcement.created_at.strftime('%Y-%m-%d') }}</small>
                </h5>
            </div>

            <div id="collapse-{{ announcement.id }}" class="collapse {% if loop.first %}show{% endif %}" aria-labelledby="heading-{{ announcement.id }}" data-parent="#announcements-accordion">
                <div class="card-body">
                    {{ announcement.content | nl2br }}
                </div>
            </div>
        </div>
    {% else %}
        <div class="alert alert-info">現在、お知らせはありません。</div>
    {% endfor %}
    </div>
</div>
<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


AI_CHAT_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIチャット - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        html, body { height: 100%; }
        body { display: flex; flex-direction: column; }
        .chat-header { flex-shrink: 0; }
        .chat-container { flex-grow: 1; overflow-y: auto; padding: 15px; }
        .message-bubble { max-width: 80%; padding: 10px 15px; border-radius: 20px; margin-bottom: 10px; word-wrap: break-word; display: flex; align-items: center; }
        .my-message { background-color: #007bff; color: white; margin-left: auto; }
        .ai-message { background-color: #e9e9eb; color: black; margin-right: auto; }
        .chat-form { flex-shrink: 0; }
        .typing-indicator { display: none; }
    </style>
</head>
<body>
    <header class="chat-header bg-light p-3 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <a href="{{ url_for('main_app') }}" class="btn btn-secondary btn-sm"><i class="bi bi-arrow-left"></i></a>
            <strong class="ml-2"><i class="bi bi-robot"></i> AIチャット (Gemini Pro)</strong>
        </div>
    </header>

    <div class="chat-container" id="chat-container">
        {% for msg in history %}
            <div class="message-bubble {{ 'my-message' if msg.sender_id == current_user.id else 'ai-message' }}">
                {{ msg.content | nl2br }}
            </div>
        {% endfor %}
        <div class="message-bubble ai-message typing-indicator" id="typing-indicator">
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="sr-only">Typing...</span>
            </div>
            <span class="ml-2">AIが考え中...</span>
        </div>
    </div>

    <form class="chat-form p-3 bg-light border-top" id="message-form">
        <div class="input-group">
            <input type="text" id="message-input" class="form-control" placeholder="AIへの質問やメッセージを入力..." autocomplete="off">
            <div class="input-group-append">
                <button class="btn btn-primary" type="submit"><i class="bi bi-send"></i></button>
            </div>
        </div>
    </form>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const form = document.getElementById('message-form');
    const input = document.getElementById('message-input');
    const chatContainer = document.getElementById('chat-container');
    const typingIndicator = document.getElementById('typing-indicator');

    chatContainer.scrollTop = chatContainer.scrollHeight;

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (input.value) {
            const message = input.value;
            appendMessage(message, 'my-message');
            socket.emit('send_ai_message', { 'message': message });
            input.value = '';
            typingIndicator.style.display = 'flex';
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    });

    socket.on('ai_response', function(data) {
        typingIndicator.style.display = 'none';
        appendMessage(data.message, 'ai-message');
    });

    function appendMessage(content, className) {
        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble', className);
        messageBubble.innerHTML = content.replace(/\\n/g, '<br>');
        chatContainer.insertBefore(messageBubble, typingIndicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});
</script>
</body>
</html>
"""

SETTINGS_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>設定 - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4"><i class="bi bi-gear-fill"></i> 設定</h1>

    <div class="card">
        <div class="card-header">
            プロフィール設定
        </div>
        <div class="card-body">
            <form action="{{ url_for('update_settings') }}" method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="username">ユーザー名</label>
                    <input type="text" class="form-control" id="username" name="username" value="{{ user.username }}" required>
                </div>
                <div class="form-group">
                    <label for="email">メールアドレス</label>
                    <input type="email" class="form-control" id="email" name="email" value="{{ user.email or '' }}">
                </div>
                <div class="form-group">
                    <label for="status_message">ステータスメッセージ</label>
                    <input type="text" class="form-control" id="status_message" name="status_message" value="{{ user.status_message or '' }}">
                </div>
                <div class="form-group">
                    <label for="bio">自己紹介</label>
                    <textarea class="form-control" id="bio" name="bio" rows="3">{{ user.bio or '' }}</textarea>
                </div>
                <div class="form-group">
                    <label for="birthday">誕生日</label>
                    <input type="date" class="form-control" id="birthday" name="birthday" value="{{ user.birthday or '' }}">
                </div>
                <hr>
                <h5 class="mt-4">表示設定</h5>
                <div class="form-group form-check">
                    <input type="checkbox" class="form-check-input" id="show_typing" name="show_typing" value="1" {% if user.show_typing %}checked{% endif %}>
                    <label class="form-check-label" for="show_typing">入力中であることを表示する</label>
                </div>
                <div class="form-group form-check">
                    <input type="checkbox" class="form-check-input" id="show_online_status" name="show_online_status" value="1" {% if user.show_online_status %}checked{% endif %}>
                    <label class="form-check-label" for="show_online_status">オンライン状態を表示する</label>
                </div>

                <button type="submit" class="btn btn-primary btn-block mt-4">プロフィールを更新</button>
            </form>
        </div>
    </div>
    
    <div class="card mt-4">
        <div class="card-header">アカウント</div>
        <div class="list-group list-group-flush">
            <a href="#" class="list-group-item list-group-item-action">パスワード変更</a>
            <a href="#" class="list-group-item list-group-item-action text-danger">アカウントを削除</a>
        </div>
    </div>
</div>
</body>
</html>
"""
CREATE_GROUP_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>グループ作成 - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4"><i class="bi bi-people-fill"></i> 新しいグループを作成</h1>

    <form action="{{ url_for('create_group') }}" method="POST" id="create-group-form">
        <div class="card">
            <div class="card-body">
                <div class="form-group">
                    <label for="group_name">グループ名</label>
                    <input type="text" id="group_name" name="group_name" class="form-control" placeholder="グループ名を入力" required>
                </div>
                <hr>
                <h5 class="card-title">メンバーを選択</h5>
                <div class="list-group">
                    {% for friend in friends_list %}
                    <label class="list-group-item">
                        <input type="checkbox" name="members" value="{{ friend.id }}" class="mr-3"> {{ friend.username }}
                    </label>
                    {% else %}
                    <p class="text-muted">招待できる友達がいません。</p>
                    {% endfor %}
                </div>
            </div>
            <div class="card-footer">
                <button type="submit" class="btn btn-primary btn-block">作成する</button>
            </div>
        </div>
    </form>
</div>
</body>
</html>
"""

KEEP_MEMO_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>キープメモ - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        html, body { height: 100vh; overflow: hidden; }
        body { display: flex; flex-direction: column; }
        .chat-header { flex-shrink: 0; }
        .chat-container { flex-grow: 1; overflow-y: auto; padding: 15px; }
        .message-bubble { max-width: 80%; padding: 10px 15px; border-radius: 20px; margin-bottom: 10px; word-wrap: break-word; background-color: #dcf8c6; margin-left: auto; }
        .chat-form { flex-shrink: 0; }
    </style>
</head>
<body>
    <header class="chat-header bg-light p-3 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <a href="{{ url_for('main_app') }}" class="btn btn-secondary btn-sm"><i class="bi bi-arrow-left"></i></a>
            <strong class="ml-2"><i class="bi bi-journal-check"></i> キープメモ</strong>
        </div>
    </header>

    <div class="chat-container" id="chat-container">
        {% for message in messages %}
            <div class="message-bubble">
                {{ message.content | nl2br }}
            </div>
        {% endfor %}
    </div>

    <form class="chat-form p-3 bg-light border-top" id="message-form">
        <div class="input-group">
            <input type="text" id="message-input" class="form-control" placeholder="メモを入力..." autocomplete="off">
            <div class="input-group-append">
                <button class="btn btn-primary" type="submit"><i class="bi bi-send"></i></button>
            </div>
        </div>
    </form>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const form = document.getElementById('message-form');
    const input = document.getElementById('message-input');
    const chatContainer = document.getElementById('chat-container');
    const currentUserId = {{ current_user.id }};

    // 初期表示時に一番下までスクロール
    chatContainer.scrollTop = chatContainer.scrollHeight;

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (input.value) {
            socket.emit('send_private_message', {
                'recipient_id': currentUserId, // 自分自身に送信
                'message': input.value
            });
            input.value = '';
        }
    });

    socket.on('new_private_message', function(msg) {
        // 自分から自分へのメッセージのみを描画
        if (msg.sender_id === currentUserId) {
            const messageBubble = document.createElement('div');
            messageBubble.classList.add('message-bubble');
            messageBubble.innerHTML = msg.content.replace(/\\n/g, '<br>');
            chatContainer.appendChild(messageBubble);
            chatContainer.scrollTop = chatContainer.scrollHeight; // 自動スクロール
        }
    });
});
</script>
</body>
</html>
"""
GAME_JANKEN_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>じゃんけん - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        .game-container { max-width: 500px; margin: auto; }
        .hand-display { font-size: 5rem; text-align: center; height: 120px; line-height: 120px; }
        .player-area { border: 2px dashed #ccc; border-radius: 10px; padding: 20px; }
        .vs { font-size: 3rem; font-weight: bold; }
        .hand-buttons button { width: 80px; height: 80px; font-size: 2.5rem; }
        .result-text { font-size: 1.5rem; font-weight: bold; height: 50px; }
    </style>
</head>
<body>
<div class="container my-4 game-container">
    <a href="{{ url_for('games_hub') }}" class="btn btn-secondary mb-3"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="text-center">じゃんけん</h1>
    
    <div class="row align-items-center text-center">
        <!-- 相手プレイヤー -->
        <div class="col-12 mb-3">
            <div class="player-area">
                <h6>{{ room.players[1].name }}</h6>
                <div id="opponent-hand" class="hand-display text-secondary">？</div>
            </div>
        </div>
        
        <div class="col-12 my-2">
            <div class="vs">VS</div>
        </div>

        <!-- 自分 -->
        <div class="col-12 mt-3">
            <div class="player-area bg-light">
                 <h6>{{ current_user.username }} (あなた)</h6>
                 <div id="my-hand" class="hand-display text-secondary">？</div>
            </div>
        </div>
    </div>
    
    <div id="result-area" class="text-center my-3 result-text text-primary">
        手を選んでください
    </div>

    <div id="hand-buttons" class="text-center">
        <button class="btn btn-outline-primary" data-move="rock"><i class="bi bi-hand-thumbs-up-fill"></i></button>
        <button class="btn btn-outline-success mx-3" data-move="scissors"><i class="bi bi-scissors"></i></button>
        <button class="btn btn-outline-warning" data-move="paper"><i class="bi bi-hand-index-thumb-fill"></i></button>
    </div>

</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const roomId = "{{ room_id }}";
    const handButtons = document.getElementById('hand-buttons');
    const myHandDiv = document.getElementById('my-hand');
    const opponentHandDiv = document.getElementById('opponent-hand');
    const resultArea = document.getElementById('result-area');
    const handIcons = {
        'rock': '<i class="bi bi-hand-thumbs-up-fill"></i>',
        'scissors': '<i class="bi bi-scissors"></i>',
        'paper': '<i class="bi bi-hand-index-thumb-fill"></i>'
    };

    handButtons.addEventListener('click', function(e) {
        const button = e.target.closest('button');
        if (button) {
            const move = button.dataset.move;
            socket.emit('janken_move', { room_id: roomId, move: move });
            myHandDiv.innerHTML = handIcons[move];
            resultArea.textContent = '相手が出すのを待っています...';
            handButtons.style.display = 'none'; // 選択後はボタンを隠す
        }
    });

    socket.on('janken_result', function(data) {
        const myMove = data.moves[{{ current_user.id }}];
        // 相手のIDを取得 (自分ではないID)
        const opponentId = Object.keys(data.moves).find(id => parseInt(id, 10) !== {{ current_user.id }});
        const opponentMove = data.moves[opponentId];
        
        myHandDiv.innerHTML = handIcons[myMove];
        opponentHandDiv.innerHTML = handIcons[opponentMove];
        resultArea.textContent = data.result_text;

        // 2秒後にリセット
        setTimeout(() => {
            myHandDiv.innerHTML = '？';
            opponentHandDiv.innerHTML = '？';
            resultArea.textContent = 'もう一度！';
            handButtons.style.display = 'block';
        }, 2000);
    });
});
</script>
</body>
</html>
"""

STAMPS_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>スタンプショップ - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        .stamp-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
            gap: 15px;
        }
        .stamp-item {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            text-align: center;
        }
        .stamp-item .stamp-emoji {
            font-size: 3rem;
        }
    </style>
</head>
<body>
<div class="container my-4">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4"><i class="bi bi-emoji-smile-fill"></i> スタンプ</h1>

    <!-- スタンプショップ -->
    <div class="card mb-4">
        <div class="card-header">スタンプショップ (無料)</div>
        <div class="card-body">
            {% set owned_stamp_ids = user_stamps | map(attribute='id') | list %}
            <div class="stamp-grid">
                {% for stamp in free_stamps %}
                <div class="stamp-item">
                    <div class="stamp-emoji">{{ stamp.image_url }}</div>
                    <div class="small">{{ stamp.name }}</div>
                    {% if stamp.id in owned_stamp_ids %}
                        <button class="btn btn-sm btn-secondary mt-2" disabled>所持済み</button>
                    {% else %}
                        <a href="{{ url_for('acquire_stamp', stamp_id=stamp.id) }}" class="btn btn-sm btn-primary mt-2">取得</a>
                    {% endif %}
                </div>
                {% else %}
                <p>現在、ショップに新しいスタンプはありません。</p>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <!-- 所持スタンプ -->
    <div class="card">
        <div class="card-header">所持スタンプ</div>
        <div class="card-body">
            <div class="stamp-grid">
                {% for stamp in user_stamps %}
                <div class="stamp-item">
                    <div class="stamp-emoji">{{ stamp.image_url }}</div>
                    <div class="small">{{ stamp.name }}</div>
                </div>
                {% else %}
                <p>まだスタンプを持っていません。ショップで無料スタンプを取得しましょう！</p>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

GAME_BABANUKI_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ババ抜き - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        .game-board { background-color: #2a4; color: white; padding: 20px; border-radius: 10px; }
        .player-area { border: 2px solid #fff; border-radius: 8px; padding: 10px; margin-bottom: 15px; min-height: 120px; cursor: default; }
        .player-area.is-turn { border-color: #ffc107; box-shadow: 0 0 10px #ffc107; }
        .player-area.can-draw { cursor: pointer; background-color: rgba(255, 255, 0, 0.2); }
        .my-hand .card { display: inline-block; border: 2px solid #333; border-radius: 5px; padding: 10px 5px; margin: 2px; background-color: #fff; color: #000; font-weight: bold; min-width: 40px; text-align: center; }
        .card-back { font-size: 2.5rem; }
    </style>
</head>
<body>
<div class="container my-4">
    <div class="game-board">
        <h2 class="text-center">ババ抜き <small>(ルームID: {{ room_id }})</small></h2>
        <a href="{{ url_for('games_hub') }}" class="btn btn-sm btn-light mb-3"><i class="bi bi-arrow-left"></i> 戻る</a>
        {% if room.host == current_user.id and room.status == 'waiting' %}
        <button id="start-game-btn" class="btn btn-success mb-3">ゲーム開始</button>
        {% endif %}
        
        <div id="players-area" class="row text-center"></div>
        <div id="game-log" class="bg-light text-dark p-2 rounded" style="height: 100px; overflow-y: scroll;"></div>
    </div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const roomId = "{{ room_id }}";
    const currentUserId = {{ current_user.id }};
    const playersArea = document.getElementById('players-area');
    const gameLog = document.getElementById('game-log');
    const startGameBtn = document.getElementById('start-game-btn');
    let turnOrder = [];

    if(startGameBtn) {
        startGameBtn.addEventListener('click', () => {
            socket.emit('start_game', { room_id: roomId });
            startGameBtn.style.display = 'none';
        });
    }

    function addLog(message) {
        gameLog.innerHTML += `<p class="mb-1">${message}</p>`;
        gameLog.scrollTop = gameLog.scrollHeight;
    }

    function renderPlayers(players, currentTurnId) {
        playersArea.innerHTML = '';
        const myIndex = turnOrder.indexOf(currentUserId);
        // 隣のプレイヤー（引く相手）のID
        const targetPlayerId = myIndex !== -1 ? turnOrder[(myIndex - 1 + turnOrder.length) % turnOrder.length] : null;

        players.forEach(p => {
            const isMyTurn = currentTurnId === currentUserId;
            const isTarget = isMyTurn && p.id === targetPlayerId;
            const playerDiv = document.createElement('div');
            playerDiv.className = 'col-md-6';
            playerDiv.innerHTML = `
                <div id="player-${p.id}" class="player-area ${currentTurnId === p.id ? 'is-turn' : ''} ${isTarget ? 'can-draw' : ''}" data-player-id="${p.id}">
                    <h6>${p.name} ${p.id === currentUserId ? '(あなた)' : ''}</h6>
                    ${p.id === currentUserId ? `<div class="my-hand" id="my-hand"></div>` : `<div class="card-back"><i class="bi bi-card-heading"></i> x ${p.card_count}</div>`}
                </div>`;
            playersArea.appendChild(playerDiv);
        });

        document.querySelectorAll('.can-draw').forEach(el => {
            el.addEventListener('click', function() {
                socket.emit('draw_card', { room_id: roomId, target_player_id: this.dataset.playerId });
            });
        });
    }

    function renderMyHand(hand) {
        const myHandDiv = document.getElementById('my-hand');
        if (!myHandDiv) return;
        myHandDiv.innerHTML = '';
        hand.forEach(card => {
            myHandDiv.innerHTML += `<div class="card">${card.rank === 'Joker' ? 'JOKER' : card.suit+card.rank}</div>`;
        });
    }

    socket.on('connect', () => socket.emit('join_game', { room_id: roomId }));
    socket.on('log_message', data => addLog(data.message));
    socket.on('game_started', data => renderMyHand(data.your_hand));
    socket.on('update_hand', data => renderMyHand(data.hand));
    socket.on('game_over', data => alert(`ゲーム終了！ ${data.loser}さんの負けです。`));
    socket.on('update_game_state', data => {
        // サーバーから送られてくるプレイヤーリストを元にターン順を更新
        turnOrder = data.players.filter(p => p.card_count > 0).map(p => p.id);
        renderPlayers(data.players, data.current_turn);
        const myPlayer = data.players.find(p => p.id === currentUserId);
        if (myPlayer) {
             const myHandDiv = document.getElementById('my-hand');
             if(myHandDiv){ // 自分が上がった後は要素がないのでチェック
                myHandDiv.parentElement.querySelector('h6').innerHTML = `${myPlayer.name} (あなた) - 残り${myPlayer.card_count}枚`;
             }
        }
    });
});
</script>
</body>
</html>
"""
GAME_AMIDAKUJI_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>あみだくじ - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4">
    <a href="{{ url_for('games_hub') }}" class="btn btn-secondary mb-3"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="text-center">あみだくじ</h1>
    
    <div class="row">
        <div class="col-md-6">
            <h4>参加者</h4>
            <ul class="list-group">
                {% for player in room.players %}
                <li class="list-group-item">{{ player.name }}</li>
                {% endfor %}
            </ul>
        </div>
        <div class="col-md-6">
            <h4>くじの内容</h4>
            {% if room.host == current_user.id %}
            <form id="amida-setup-form">
                <div id="item-inputs">
                    {% for player in room.players %}
                    <div class="form-group">
                        <input type="text" class="form-control" name="item" placeholder="くじ{{ loop.index }}" required>
                    </div>
                    {% endfor %}
                </div>
                <button type="submit" class="btn btn-info">くじを設定</button>
            </form>
            {% endif %}
            <ul id="item-list" class="list-group mt-3"></ul>
        </div>
    </div>
    
    {% if room.host == current_user.id %}
    <div class="text-center mt-4">
        <button id="start-amida-btn" class="btn btn-success btn-lg">あみだ開始！</button>
    </div>
    {% endif %}

    <div id="result-area" class="mt-4"></div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const roomId = "{{ room_id }}";
    const setupForm = document.getElementById('amida-setup-form');
    const startBtn = document.getElementById('start-amida-btn');
    const itemList = document.getElementById('item-list');
    const resultArea = document.getElementById('result-area');

    if (setupForm) {
        setupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const items = Array.from(e.target.elements.item).map(input => input.value);
            socket.emit('setup_amida', { room_id: roomId, items: items });
        });
    }

    if (startBtn) {
        startBtn.addEventListener('click', () => {
            socket.emit('start_amida', { room_id: roomId });
        });
    }

    socket.on('amida_updated', function(data) {
        itemList.innerHTML = '';
        data.items.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = item;
            itemList.appendChild(li);
        });
    });

    socket.on('amida_result', function(data) {
        resultArea.innerHTML = '<h3 class="text-center">結果発表！</h3>';
        const table = document.createElement('table');
        table.className = 'table table-bordered';
        table.innerHTML = '<thead class="thead-dark"><tr><th>参加者</th><th>結果</th></tr></thead>';
        const tbody = document.createElement('tbody');
        
        const playerMap = { {% for p in room.players %}{{ p.id }}: '{{ p.name }}',{% endfor %} };

        for (const playerId in data.results) {
            const row = document.createElement('tr');
            const playerName = playerMap[playerId] || '不明';
            row.innerHTML = `<td>${playerName}</td><td>${data.results[playerId]}</td>`;
            tbody.appendChild(row);
        }
        table.appendChild(tbody);
        resultArea.appendChild(table);
    });
});
</script>
</body>
</html>
"""
GAME_QUIZ_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>クイズ - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4">
    <a href="{{ url_for('games_hub') }}" class="btn btn-secondary mb-3">戻る</a>
    <h1 class="text-center">クイズバトル！</h1>
    
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center" id="question-header">
                    <span>問題</span>
                    <span id="quiz-theme-display" class="badge badge-info"></span>
                </div>
                <div class="card-body">
                    <h4 id="question-text">ゲーム開始を待っています...</h4>
                    <div id="options-area" class="list-group mt-4"></div>
                </div>
                <div class="card-footer" id="result-area"></div>
            </div>
            {% if room.host == current_user.id %}
            <div class="card mt-3">
                <div class="card-body">
                    <h5 class="card-title"><i class="bi bi-robot"></i> AIでクイズを作成</h5>
                    <div class="input-group">
                        <input type="text" id="quiz-theme-input" class="form-control" placeholder="クイズのテーマを入力 (例: 宇宙, 歴史)">
                        <div class="input-group-append">
                            <button id="generate-ai-quiz-btn" class="btn btn-outline-primary">生成</button>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}
        </div>
        <div class="col-md-4">
            <h4>スコアボード</h4>
            <ul id="scoreboard" class="list-group">
                {% for player in room.players %}
                <li class="list-group-item d-flex justify-content-between align-items-center" id="score-{{ player.id }}">
                    {{ player.name }} <span class="badge badge-primary badge-pill">0</span>
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
    {% if room.host == current_user.id %}
    <button id="start-game-btn" class="btn btn-success mt-3">クイズ開始</button>
    {% endif %}
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const roomId = "{{ room_id }}";
    const startBtn = document.getElementById('start-game-btn');
    const qText = document.getElementById('question-text');
    const optsArea = document.getElementById('options-area');
    const resultArea = document.getElementById('result-area');
    const aiQuizBtn = document.getElementById('generate-ai-quiz-btn');
    const themeInput = document.getElementById('quiz-theme-input');
    const themeDisplay = document.getElementById('quiz-theme-display');

    if(startBtn) {
        startBtn.addEventListener('click', () => {
            socket.emit('start_game', { room_id: roomId });
            startBtn.style.display = 'none';
            if (aiQuizBtn) aiQuizBtn.closest('.card').style.display = 'none';
        });
    }

    if (aiQuizBtn) {
        aiQuizBtn.addEventListener('click', () => {
            const theme = themeInput.value.trim();
            if (theme) {
                socket.emit('generate_ai_quiz', { room_id: roomId, theme: theme });
                resultArea.textContent = 'AIがクイズを生成中です...';
            } else {
                alert('テーマを入力してください。');
            }
        });
    }
    
    socket.on('connect', () => socket.emit('join_game', { room_id: roomId }));

    socket.on('quiz_generated', function(data) {
        resultArea.textContent = `AIが「${data.theme}」のクイズを作成しました！`;
        themeDisplay.textContent = data.theme;
    });

    socket.on('ai_quiz_error', data => alert(data.message));
    
    socket.on('new_question', function(data) {
        qText.textContent = data.question;
        optsArea.innerHTML = '';
        resultArea.textContent = '';
        data.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'list-group-item list-group-item-action';
            btn.textContent = opt;
            btn.onclick = () => {
                socket.emit('submit_answer', { room_id: roomId, answer: opt });
                optsArea.querySelectorAll('button').forEach(b => b.disabled = true);
            };
            optsArea.appendChild(btn);
        });
    });

    socket.on('answer_result', function(data) {
        resultArea.textContent = data.is_correct ? "正解！" : "不正解...";
        resultArea.className = data.is_correct ? 'card-footer text-success' : 'card-footer text-danger';
    });
    
    socket.on('show_correct_answer', function(data) {
        resultArea.textContent = `正解は「${data.correct_answer}」でした！`;
        resultArea.className = 'card-footer text-info';
        for (const playerId in data.scores) {
            const scoreEl = document.querySelector(`#score-${playerId} .badge`);
            if (scoreEl) scoreEl.textContent = data.scores[playerId];
        }
    });

    socket.on('game_over', function(data) {
        qText.textContent = data.message;
        optsArea.innerHTML = '';
        resultArea.textContent = `優勝は ${data.winner} さんです！`;
    });
});
</script>
</body>
</html>
"""

GAME_SHIRITORI_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>しりとり - TMHKchat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('games_hub') }}" class="btn btn-secondary mb-3">戻る</a>
    <h1 class="text-center">しりとり</h1>

    <div class="card">
        <div class="card-header">
            現在のターン: <strong id="turn-player"></strong>
        </div>
        <div class="card-body">
            <p>前の単語: <span id="current-word" class="h4">（開始待ち）</span></p>
            <p>次の文字: <span id="next-char" class="h4 text-danger"></span></p>
            <form id="word-form">
                <div class="input-group">
                    <input type="text" id="word-input" class="form-control" placeholder="言葉を入力" autocomplete="off" disabled>
                    <div class="input-group-append">
                        <button class="btn btn-primary" type="submit" id="submit-btn" disabled>決定</button>
                    </div>
                </div>
            </form>
        </div>
    </div>
    
    <div class="mt-3">
        <h6>使用された言葉リスト</h6>
        <ul id="used-words-list" class="list-group" style="height: 150px; overflow-y: scroll;"></ul>
    </div>
    
    {% if room.host == current_user.id %}
    <button id="start-game-btn" class="btn btn-success mt-3">しりとり開始</button>
    {% endif %}
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const roomId = "{{ room_id }}";
    const currentUserId = {{ current_user.id }};
    const playerMap = { {% for p in room.players %}{{ p.id }}: '{{ p.name }}',{% endfor %} };

    const startBtn = document.getElementById('start-game-btn');
    const wordForm = document.getElementById('word-form');
    const wordInput = document.getElementById('word-input');
    const submitBtn = document.getElementById('submit-btn');
    const turnPlayer = document.getElementById('turn-player');
    const currentWord = document.getElementById('current-word');
    const nextChar = document.getElementById('next-char');
    const usedWordsList = document.getElementById('used-words-list');
    
    if(startBtn) {
        startBtn.addEventListener('click', () => {
            socket.emit('start_game', { room_id: roomId });
            startBtn.style.display = 'none';
        });
    }
    
    socket.on('connect', () => socket.emit('join_game', { room_id: roomId }));

    wordForm.addEventListener('submit', function(e) {
        e.preventDefault();
        if(wordInput.value) {
            socket.emit('submit_word', { room_id: roomId, word: wordInput.value });
            wordInput.value = '';
        }
    });

    socket.on('update_game_state', function(data) {
        turnPlayer.textContent = playerMap[data.current_turn];
        if (data.current_turn === currentUserId) {
            wordInput.disabled = false;
            submitBtn.disabled = false;
            wordInput.focus();
        } else {
            wordInput.disabled = true;
            submitBtn.disabled = true;
        }
        
        if(data.current_word) {
            currentWord.textContent = data.current_word;
            nextChar.textContent = data.last_char;
        }

        usedWordsList.innerHTML = '';
        data.used_words.forEach(word => {
            const li = document.createElement('li');
            li.className = 'list-group-item py-1';
            li.textContent = word;
            usedWordsList.appendChild(li);
        });
    });
    
    socket.on('invalid_word', function(data) {
        alert(data.message);
    });

    socket.on('game_over', function(data) {
        alert(data.message);
        wordInput.disabled = true;
        submitBtn.disabled = true;
    });
});
</script>
</body>
</html>
"""
SURVEY_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>アンケート - TMHKchat</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 700px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <div class="card">
        <div class="card-header">
            <h3>{{ survey.title }}</h3>
        </div>
        <div class="card-body">
            <p>{{ survey.description }}</p>
            <hr>

            {% if has_answered %}
                <div class="alert alert-success">ご回答ありがとうございました。</div>
            {% else %}
                <form action="{{ url_for('submit_survey') }}" method="POST">
                    <input type="hidden" name="survey_id" value="{{ survey.id }}">
                    {% for question in questions %}
                        <div class="form-group mb-4">
                            <label><strong>Q{{ loop.index }}. {{ question.question_text }}</strong></label>
                            
                            {% if question.question_type == 'multiple_choice' %}
                                {% for option in options[question.id] %}
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="question-{{ question.id }}-multiple_choice" id="option-{{ option.id }}" value="{{ option.id }}" required>
                                    <label class="form-check-label" for="option-{{ option.id }}">
                                        {{ option.option_text }}
                                    </label>
                                </div>
                                {% endfor %}
                            {% elif question.question_type == 'text' %}
                                <textarea name="question-{{ question.id }}-text" class="form-control" rows="3"></textarea>
                            {% endif %}
                        </div>
                    {% endfor %}
                    <button type="submit" class="btn btn-primary btn-block">回答を送信する</button>
                </form>
            {% endif %}
        </div>
    </div>
</div>
</body>
</html>
"""
# --- スケジュールタスクの登録と起動 ---
# アプリケーションコンテキスト内で一度だけ実行されるように設定
with app.app_context():
    # 既存のジョブがあれば削除して再登録する
    if scheduler.get_job('scraping_job'):
        scheduler.remove_job('scraping_job')
    
    # 最初に一度即時実行し、その後1時間ごとに実行する
    scheduler.add_job(scheduled_scraping_tasks, 'interval', hours=1, id='scraping_job', next_run_time=datetime.now())
    
    # スケジューラーが起動していなければ起動する
    if not scheduler.running:
        scheduler.start()
        print("Scheduler started.")

@app.route('/force-scrape')
@login_required
def force_scrape():
    """手動でスクレイピングを実行するためのテスト用ルート"""
    flash('手動で情報更新を開始します...', 'info')
    try:
        # スケジューラーのジョブを直接実行
        scheduler.get_job('scraping_job').func()
        flash('天気・交通・災害情報の更新が完了しました！', 'success')
    except Exception as e:
        flash(f'情報の更新中にエラーが発生しました: {e}', 'danger')
    return redirect(url_for('timeline'))

if __name__ == '__main__':
    # 開発サーバー起動時にスケジューラーが二重に起動するのを防ぐ
    # use_reloader=False はスケジューラーを安定動作させるために重要
    socketio.run(app, debug=True, use_reloader=False)