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
from flask import (Flask, flash, g, redirect, render_template, request,
                   url_for, jsonify, send_from_directory, session, send_file, make_response)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

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

def format_datetime_str(value, format='%Y-%m-%d %H:%M'):
    """ISOフォーマットの文字列やDBのタイムスタンプ文字列を日付オブジェクトに変換してフォーマットする"""
    if not value:
        return ""
    try:
        # SQLiteのデフォルトタイムスタンプ形式 'YYYY-MM-DD HH:MM:SS' に対応
        dt_obj = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return dt_obj.strftime(format)
    except (ValueError, TypeError):
        # isoformat() などの他の形式にも対応
        try:
            dt_obj = datetime.fromisoformat(value)
            return dt_obj.strftime(format)
        except (ValueError, TypeError):
            return value # 変換できない場合は元の文字列をそのまま返す

app.jinja_env.filters['format_datetime'] = format_datetime_str

# --- 各種設定 ---
# 環境変数からSECRET_KEYを読み込む、設定されていなければデフォルト値を使用
SECRET_KEY = os.getenv('SECRET_KEY', 'aK4$d!sF9@gH2%jLpQ7rT1&uY5vW8xZc')
app.config['SECRET_KEY'] = SECRET_KEY

# その他の設定
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
DATABASE = os.path.join(app.root_path, 'database', 'tmhk.db')

# 画像アップロード設定
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'assets', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# UPLOAD_FOLDERが存在しない場合に作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'profile_images'), exist_ok=True) # プロフィール画像専用フォルダ
os.makedirs(os.path.join(UPLOAD_FOLDER, 'voices'), exist_ok=True) # ボイスメッセージ用フォルダ
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'zip', 'mp4', 'mp3', 'wav', 'm4a', 'webm', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

# Google AI APIキー設定
GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')
if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-pro-latest')
else:
    ai_model = None
    print("Warning: GOOGLE_AI_API_KEY is not set. AI features will be limited.")

QA_DATA_PATH = os.path.join(app.root_path, 'qa_data.json')
qa_list = []
try:
    with open(QA_DATA_PATH, 'r', encoding='utf-8') as f:
        qa_list = json.load(f)
    print("Successfully loaded qa_data.json for rule-based chat.")
except Exception as e:
    print(f"Warning: Could not load qa_data.json. Rule-based chat will be limited. Error: {e}")

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
    'private': {'name': 'プライベート', 'theme': 'casual', 'bg_gradient': 'linear-gradient(135deg, #10b981, #34d399)'},
    'other': {'name': 'その他', 'theme': 'custom', 'bg_gradient': 'linear-gradient(135deg, #6c757d, #343a40)'} # 「その他」を追加
}

# Flask-Login 初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# オンライン中のユーザーを管理するための辞書
online_users = {}

# ミニゲームの状態管理
game_rooms = {}

# スケジューラーの初期化
scheduler = BackgroundScheduler(daemon=True)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # セッションに is_admin がない、または1でない場合は管理者ではない
        if not session.get('is_admin'):
            flash('管理者権限が必要です。', 'danger')
            return redirect(url_for('main_app')) # メインアプリのURLにリダイレクト
        return f(*args, **kwargs)
    return decorated_function

    
# --- ヘルパー関数 ---
def allowed_file(filename):
    """許可された拡張子のファイルかチェックする"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def scrape_weather():
    """天気情報を気象庁の公式JSONデータから取得"""
    with app.app_context():
        url = 'https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json'
        data_to_save = "天気情報の取得に失敗しました。"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            data = response.json()
            
            tokyo_forecast = data[0]['timeSeries'][0]['areas'][0]
            tokyo_temps = data[0]['timeSeries'][2]['areas'][0]

            weather = tokyo_forecast['weathers'][0]
            high_temp = tokyo_temps['temps'][1]
            low_temp = tokyo_temps['temps'][0]

            weather = ' '.join(weather.split())
            data_to_save = f"気象庁 (今日): {weather} 最高:{high_temp}℃ 最低:{low_temp}℃"
            print("Weather data updated successfully from JMA API.")
        except Exception as e:
            print(f"Weather scraping failed (jma.go.jp API): {e}")

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
            found_statuses = []

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
                        
                        found_statuses.append(f"{area_name}: {status}")
                        
                        if "平常運転" not in status:
                            info_list.append(f"【{area_name}】{status}")
            
            print(f"JR East Status Check: Found {len(found_statuses)} areas. Details: {', '.join(found_statuses)}")

            if info_list:
                data_to_save = " ".join(info_list[:5])
            else:
                data_to_save = "JR東日本（関東エリア）は現在すべて平常運転です。"
            
            print("Traffic data updated successfully from JR East Area Status Page.")
        except Exception as e:
            print(f"Traffic scraping error (JR East Area Status Page): {e}")

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
        url = 'https://www.jma.go.jp/bosai/warning/data/warning/130000.json'
        data_to_save = "現在、主要な災害情報はありません。"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            data = response.json()
            
            headline = data.get('headlineText')
            if headline and headline.strip():
                data_to_save = headline.strip()
            
            print("Disaster data updated successfully from JMA API.")
        except Exception as e:
            print(f"Disaster scraping failed (jma.go.jp API): {e}")
            data_to_save = "災害情報の取得に失敗しました。"

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
        self.status = status
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

def is_system_admin():
    """現在のユーザーがシステム管理者かチェック"""
    return (current_user.is_authenticated and 
            current_user.is_admin and 
            session.get('is_system_admin', False))

def init_extended_db():
    """database/tmhk.sqlファイルからスキーマを読み込みデータベースを構築する"""
    with app.app_context():
        db = get_db()
        sql_file_path = os.path.join(app.root_path, 'database', 'tmhk.sql')
        
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            db.executescript(schema_sql)
            db.commit()
            print('データベースをtmhk.sqlから初期化・確認しました。')
        except FileNotFoundError:
            print(f"エラー: {sql_file_path} が見つかりません。")
        except Exception as e:
            print(f"データベース初期化中にエラーが発生しました: {e}")

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
        if db.execute("SELECT id FROM users WHERE email = ? AND account_type = 'admin'", (ADMIN_EMAIL,)).fetchone():
            print(f'管理者アカウント ({ADMIN_EMAIL}) は既に存在します。')
            return

        hashed_password = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
        db.execute(
            'INSERT INTO users (username, email, password, is_admin, status, account_type) VALUES (?, ?, ?, ?, ?, ?)',
            ('admin_system', ADMIN_EMAIL, hashed_password, 1, 'active', 'admin')
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
    return render_template('loading.html')

@app.route('/login', methods=['GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_app'))

    # Cookieから保存されたアカウント情報を読み込む
    saved_accounts_json = request.cookies.get('saved_accounts', '{}')
    saved_accounts_dict = json.loads(saved_accounts_json)
    
    # テンプレートに渡しやすいようにリストに変換
    saved_accounts_list = list(saved_accounts_dict.values())

    return render_template('login.html', saved_accounts=saved_accounts_list)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_app'))

    if request.method == 'POST':
        account_type = request.form.get('account_type', 'private')
        custom_account_name = request.form.get('custom_account_name', '').strip()
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        account_type_to_db = custom_account_name if account_type == 'other' and custom_account_name else account_type

        if not username or not password:
            flash('ユーザー名とパスワードは必須です。', 'danger')
            return render_template('register.html', account_types=ACCOUNT_TYPES, selected_account_type=account_type)

        db = get_db()
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cursor = db.execute('INSERT INTO users (username, email, password, account_type) VALUES (?, ?, ?, ?)',
                                (username, email if email else None, hashed_password, account_type_to_db))
            db.commit()

            user_id = cursor.lastrowid
            give_default_stamps(user_id)
            check_achievement_unlocked(user_id, '新規登録', 1)

            flash('アカウントの登録が完了しました。', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('そのユーザー名またはメールアドレスは既に使用されています。', 'danger')

    return render_template('register.html', account_types=ACCOUNT_TYPES, selected_account_type='private')

@app.route('/logout')
@login_required
def logout():
    # もし代理ログイン中なら、管理者アカウントに戻る
    if session.get('_impersonating'):
        db = get_db()
        admin_id = session.get('_admin_user_id')
        
        # 念のため、代理ログインセッションをクリア
        session.clear()

        # 元の管理者として再ログイン
        admin_user = load_user(admin_id)
        if admin_user:
            login_user(admin_user)
            session['is_admin'] = admin_user.is_admin # セッションも復元
            flash('管理者アカウントに戻りました。', 'success')
            return redirect(url_for('admin_dashboard'))

    # 通常のログアウト
    logout_user()
    session.clear()
    flash('ログアウトしました。')
    return redirect(url_for('login'))


@app.route('/app')
@login_required
def main_app():
    """メインアプリケーション画面（ホームタブ）"""
    db = get_db()
    talk_filter = request.args.get('talk_filter', 'individual')
    
    account_type = current_user.account_type
    theme_info = ACCOUNT_TYPES.get(account_type) or ACCOUNT_TYPES['other']

    favorite_friends = db.execute("SELECT u.id, u.username, u.profile_image FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND f.status = 'favorite' AND u.account_type = ?",(current_user.id, current_user.account_type)).fetchall()
    normal_friends = db.execute("SELECT u.id, u.username, u.profile_image FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND f.status = 'friend' AND u.account_type = ?",(current_user.id, current_user.account_type)).fetchall()
    
    talks_list = []
    groups_list = []
    
    base_private_message_query = """
        SELECT p.partner_id, u.username as partner_name, u.profile_image as partner_image, p.last_message_content, p.last_message_time,
               (SELECT COUNT(*) FROM private_messages pm WHERE pm.sender_id = p.partner_id AND pm.recipient_id = ? AND pm.is_read = 0) as unread_count
        FROM (
            SELECT
                CASE WHEN sender_id = ? THEN recipient_id ELSE sender_id END as partner_id,
                MAX(content) as last_message_content, MAX(timestamp) as last_message_time
            FROM private_messages WHERE sender_id = ? OR recipient_id = ?
            GROUP BY partner_id
        ) p JOIN users u ON u.id = p.partner_id
        WHERE u.id != ? AND u.account_type = ?
    """
    params = [current_user.id, current_user.id, current_user.id, current_user.id, current_user.id, current_user.account_type]

    if talk_filter == 'individual':
        talks_list = db.execute(f"{base_private_message_query} ORDER BY p.last_message_time DESC", params).fetchall()
    elif talk_filter == 'close_friends':
        talks_list = db.execute(f"{base_private_message_query} AND u.id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'favorite') ORDER BY p.last_message_time DESC", params + [current_user.id]).fetchall()
    elif talk_filter == 'acquaintances':
        talks_list = db.execute(f"{base_private_message_query} AND u.id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'friend') ORDER BY p.last_message_time DESC", params + [current_user.id]).fetchall()
    elif talk_filter == 'groups':
        groups_list = db.execute("""
            SELECT r.id, r.name, (SELECT content FROM messages WHERE room_id = r.id ORDER BY timestamp DESC LIMIT 1) as last_message
            FROM rooms r JOIN room_members rm ON r.id = rm.room_id WHERE rm.user_id = ?
        """, (current_user.id,)).fetchall()
    elif talk_filter.startswith('custom_'):
        list_id = talk_filter.split('_')[1]
        talks_list = db.execute(f"{base_private_message_query} AND u.id IN (SELECT friend_id FROM custom_list_members WHERE list_id = ?) ORDER BY p.last_message_time DESC", params + [list_id]).fetchall()

    weather_data = db.execute('SELECT * FROM weather_data ORDER BY timestamp DESC').fetchall()
    traffic = db.execute('SELECT * FROM traffic_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    disaster = db.execute('SELECT * FROM disaster_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    posts = db.execute("SELECT tp.*, u.username, u.profile_image FROM timeline_posts tp JOIN users u ON tp.user_id = u.id WHERE u.account_type = ? ORDER BY tp.created_at DESC LIMIT 50", (current_user.account_type,)).fetchall()
    announcements = db.execute('SELECT * FROM announcements ORDER BY created_at DESC LIMIT 3').fetchall()
    daily_missions = db.execute('SELECT * FROM missions WHERE is_active = 1 LIMIT 3').fetchall()
    activity_feed = db.execute("SELECT af.*, u.username, u.profile_image FROM activity_feed af JOIN users u ON af.user_id = u.id WHERE af.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status IN ('friend', 'favorite')) OR af.user_id = ? ORDER BY af.created_at DESC LIMIT 10", (current_user.id, current_user.id)).fetchall()
    custom_lists = db.execute("SELECT * FROM custom_friend_lists WHERE user_id = ?", (current_user.id,)).fetchall()

    return render_template('main_app.html', current_user=current_user, theme=theme_info, 
                                  favorite_friends=favorite_friends, normal_friends=normal_friends,
                                  talks_list=talks_list, groups_list=groups_list, announcements=announcements,
                                  daily_missions=daily_missions, activity_feed=activity_feed,
                                  weather_data=weather_data, traffic=traffic, disaster=disaster, posts=posts,
                                  custom_lists=custom_lists, current_filter=talk_filter)

@app.route('/forget_account/<int:user_id>')
def forget_account(user_id):
    resp = make_response(redirect(url_for('login')))
    saved_accounts = json.loads(request.cookies.get('saved_accounts', '{}'))
    
    # 該当するuser_idを辞書から削除
    if str(user_id) in saved_accounts:
        del saved_accounts[str(user_id)]
    
    # 更新された辞書をCookieに保存
    resp.set_cookie('saved_accounts', json.dumps(saved_accounts), max_age=365*24*60*60)
    flash('アカウントを一覧から削除しました。', 'info')
    return resp


@app.route('/login_with_id', methods=['POST'])
def login_with_id():
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    remember = bool(request.form.get('remember'))

    db = get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if user_data and check_password_hash(user_data['password'], password):
        # データベースから取得した情報で User オブジェクトを正しく生成
        user = load_user(user_data['id'])
        
        if user.status != 'active':
            flash('このアカウントは現在利用が制限されています。', 'danger')
            return redirect(url_for('login'))
            
        # Flask-Loginにユーザー情報を登録 (is_admin の情報もここで引き継がれる)
        login_user(user, remember=remember)

        if user.is_admin:
            try:
                db = get_db()
                title = "管理者ステータス通知"
                content = f"管理者 '{user.username}' がオンラインになりました。"
                db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (title, content))
                db.commit()
            except Exception as e:
                print(f"Failed to create admin online announcement: {e}")

        resp = make_response(redirect(url_for('main_app')))
        saved_accounts = json.loads(request.cookies.get('saved_accounts', '{}'))
        account_info = {
            'id': user.id,
            'username': user.username,
            'profile_image': user.profile_image,
            'account_type_name': ACCOUNT_TYPES.get(user.account_type, {}).get('name', user.account_type)
        }
        saved_accounts[str(user.id)] = account_info
        resp.set_cookie('saved_accounts', json.dumps(saved_accounts), max_age=365*24*60*60)
        
        update_login_streak(user.id)
        record_activity(user.id, 'login', f'{account_info["account_type_name"]}アカウントでログイン')
        return resp
    else:
        flash('パスワードが正しくありません。', 'danger')
        return redirect(url_for('login'))

@app.route('/login/auth', methods=['POST'])
def login_auth():
    account_type = request.form.get('account_type', 'private')
    custom_account_name = request.form.get('custom_account_name', '').strip()
    login_id = request.form.get('login_id')
    password = request.form.get('password')
    remember = bool(request.form.get('remember'))

    db = get_db()
    user_data = None

    # 管理者かどうかを is_admin=1 で判定する
    if login_id == ADMIN_EMAIL:
        user_data = db.execute("SELECT * FROM users WHERE email = ? AND is_admin = 1", (login_id,)).fetchone()
    
    if not user_data:
        account_type_for_query = custom_account_name if account_type == 'other' and custom_account_name else account_type
        query = 'SELECT * FROM users WHERE (email = ? OR username = ?) AND account_type = ?'
        user_data = db.execute(query, (login_id, login_id, account_type_for_query)).fetchone()

    if user_data and check_password_hash(user_data['password'], password):
        # データベースから取得した情報で User オブジェクトを正しく生成
        user = load_user(user_data['id'])
        
        if user.status != 'active':
            flash('このアカウントは現在利用が制限されています。', 'danger')
            return redirect(url_for('login_classic'))
            
        # Flask-Loginにユーザー情報を登録 (is_admin の情報もここで引き継がれる)
        login_user(user, remember=remember)
        
        resp = make_response(redirect(url_for('main_app')))
        saved_accounts = json.loads(request.cookies.get('saved_accounts', '{}'))
        account_info = {
            'id': user.id,
            'username': user.username,
            'profile_image': user.profile_image,
            'account_type_name': ACCOUNT_TYPES.get(user.account_type, {}).get('name', user.account_type) if not user.is_admin else 'システム管理者'
        }
        saved_accounts[str(user.id)] = account_info
        resp.set_cookie('saved_accounts', json.dumps(saved_accounts), max_age=365*24*60*60)
        
        if user.is_admin:
            try:
                title = "管理者ステータス通知"
                content = f"管理者 '{user.username}' がオンラインになりました。"
                db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (title, content))
                db.commit()
            except Exception as e:
                print(f"Failed to create admin online announcement: {e}")
        
        update_login_streak(user.id)
        record_activity(user.id, 'login', f'{account_info["account_type_name"]}アカウントでログイン')
        return resp
    else:
        flash('ユーザー名/メールアドレスまたはパスワードが正しくありません。', 'danger')
        return redirect(url_for('login_classic'))



@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    db = get_db()
    # is_admin=0 の一般ユーザーのみ表示
    users = db.execute("SELECT * FROM users WHERE is_admin = 0 ORDER BY id").fetchall()
    return render_template('admin_dashboard.html', users=users, user_to_edit=None)


@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    db = get_db()
    
    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_password = request.form.get('password')

        try:
            if new_password:
                hashed_password = generate_password_hash(new_password)
                db.execute("UPDATE users SET username = ?, email = ?, password = ? WHERE id = ?", 
                           (new_username, new_email, hashed_password, user_id))
            else:
                db.execute("UPDATE users SET username = ?, email = ? WHERE id = ?", 
                           (new_username, new_email, user_id))
            db.commit()
            flash(f"ユーザー '{new_username}' の情報を更新しました。", 'success')
            return redirect(url_for('admin_dashboard'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash('そのユーザー名またはメールアドレスは既に使用されています。', 'danger')
            user_to_edit = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            users = db.execute("SELECT * FROM users WHERE is_admin = 0 ORDER BY id").fetchall()
            return render_template('admin_dashboard.html', user_to_edit=user_to_edit, users=users)
    
    # GETリクエストの場合
    user_to_edit = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user_to_edit:
        flash('編集対象のユーザーが見つかりません。', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    users = db.execute("SELECT * FROM users WHERE is_admin = 0 ORDER BY id").fetchall()
    return render_template('admin_dashboard.html', user_to_edit=user_to_edit, users=users)


@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        # ステータスを 'inactive' に変更
        db.execute("UPDATE users SET status = 'inactive' WHERE id = ?", (user_id,))
        db.commit()
        flash(f'ユーザー "{user["username"]}" のアカウントを無効化しました。', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/impersonate/<int:user_id>')
@login_required
@admin_required
def admin_impersonate(user_id):
    db = get_db()
    user_to_impersonate = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if user_to_impersonate:
        # 元の管理者IDをセッションに退避
        session['_admin_user_id'] = session['user_id']
        session['_impersonating'] = True

        # セッション情報を代理ログイン対象ユーザーのもので上書き
        session['user_id'] = user_to_impersonate['id']
        session['username'] = user_to_impersonate['username']
        session['is_admin'] = user_to_impersonate['is_admin']
        
        flash(f'"{session["username"]}" として代理ログインしました。', 'info')
        # 代理ログイン後は、Flask-Loginのcurrent_userを更新するために一度リロードするのが確実
        return redirect(url_for('main_app'))
    
    flash('代理ログインに失敗しました。', 'danger')
    return redirect(url_for('admin_dashboard'))

# --- タイムライン機能 ---
@app.route('/timeline')
@login_required
def timeline():
    db = get_db()
    weather_data = db.execute('SELECT * FROM weather_data ORDER BY timestamp DESC').fetchall()
    traffic = db.execute('SELECT * FROM traffic_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    disaster = db.execute('SELECT * FROM disaster_data ORDER BY timestamp DESC LIMIT 1').fetchone()

    posts = db.execute("SELECT tp.*, u.username, u.profile_image FROM timeline_posts tp JOIN users u ON tp.user_id = u.id ORDER BY tp.created_at DESC LIMIT 50").fetchall()

    return render_template('timeline.html', current_user=current_user, weather_data=weather_data, traffic=traffic, disaster=disaster, posts=posts)

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
# --- 直接入力用のログインページ ---

@app.route('/login/classic', methods=['GET'])
def login_classic():
    """
    メールアドレスとパスワードを直接入力するクラシックなログインページを表示する。
    管理者や、Cookieに保存されていないアカウントがここからログインする。
    """
    if current_user.is_authenticated:
        return redirect(url_for('main_app'))
    return render_template('login_classic.html', account_types=ACCOUNT_TYPES, selected_account_type='private')



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
    
    saved_games = db.execute("""
        SELECT sg.room_id, sg.game_type, sg.last_updated_at FROM saved_games sg
        JOIN saved_game_players sgp ON sg.id = sgp.game_id
        WHERE sgp.user_id = ?
    """, (current_user.id,)).fetchall()

    return render_template('games_hub.html', games=games, rankings=rankings, saved_games=saved_games)

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
    template_map = {'daifugo': 'game_daifugo.html', 'babanuki': 'game_babanuki.html', 'amidakuji': 'game_amidakuji.html',
                    'quiz': 'game_quiz.html', 'shiritori': 'game_shiritori.html', 'janken': 'game_janken.html'}
    template_file = template_map.get(room['type'], 'games_hub.html')
    return render_template(template_file, room=room, room_id=room_id, current_user=current_user)

@app.route('/stamps')
@login_required
def stamps_page():
    db = get_db()
    if db.execute('SELECT COUNT(*) FROM stamps WHERE is_free = 1').fetchone()[0] == 0:
        default_stamps = [
            ('スマイル', '😊', 'emotion'), ('泣き顔', '😭', 'emotion'), ('ハート', '❤️', 'emotion'),
            ('いいね', '👍', 'gesture'), ('OK', '👌', 'gesture'), ('ありがとう', '🙏', 'gesture'),
            ('おめでとう', '🎉', 'event'), ('びっくり', '😮', 'emotion'), ('汗', '😅', 'emotion'),
            ('よろしくお願いします', '🙇', 'gesture')
        ]
        db.executemany('INSERT INTO stamps (name, image_url, category, is_free) VALUES (?, ?, ?, 1)', default_stamps)
        db.commit()

    free_stamps = db.execute('SELECT * FROM stamps WHERE is_free = 1').fetchall()
    user_stamps = db.execute("SELECT s.* FROM stamps s JOIN user_stamps us ON s.id = us.stamp_id WHERE us.user_id = ?", (current_user.id,)).fetchall()
    return render_template('stamps.html', free_stamps=free_stamps, user_stamps=user_stamps)

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
    return render_template('settings.html', user=user_data, custom_themes=custom_themes, account_types=ACCOUNT_TYPES)

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
        db.execute("UPDATE users SET username = ?, email = ?, status_message = ?, bio = ?, birthday = ?, show_typing = ?, show_online_status = ?, profile_image = ? WHERE id = ?",
                   (username, email, status_message, bio, birthday, show_typing, show_online_status, profile_image_filename, current_user.id))
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
    db = get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (current_user.id,)).fetchone()
    youtube_links = db.execute("SELECT * FROM user_youtube_links WHERE user_id = ? ORDER BY created_at DESC", (current_user.id,)).fetchall()
    return render_template('profile_edit.html', user=user_data, account_types=ACCOUNT_TYPES, youtube_links=youtube_links)

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
    youtube_links = db.execute("SELECT * FROM user_youtube_links WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    
    return render_template('profile_view.html', user=user, friend_status=friend_status, achievements=achievements, youtube_links=youtube_links)

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

@app.route('/profile/add_youtube', methods=['POST'])
@login_required
def add_youtube_link():
    url = request.form.get('url')
    title = request.form.get('title')

    if not url or not (url.startswith('https://www.youtube.com/') or url.startswith('https://youtu.be/')):
        flash('有効なYouTubeのURLを入力してください。', 'danger')
        return redirect(url_for('profile_edit_page'))

    db = get_db()
    db.execute("INSERT INTO user_youtube_links (user_id, url, title) VALUES (?, ?, ?)",
               (current_user.id, url, title))
    db.commit()
    flash('YouTubeリンクを追加しました。', 'success')
    return redirect(url_for('profile_edit_page'))

@app.route('/profile/delete_youtube/<int:link_id>')
@login_required
def delete_youtube_link(link_id):
    db = get_db()
    link = db.execute("SELECT * FROM user_youtube_links WHERE id = ? AND user_id = ?", (link_id, current_user.id)).fetchone()
    if link:
        db.execute("DELETE FROM user_youtube_links WHERE id = ?", (link_id,))
        db.commit()
        flash('YouTubeリンクを削除しました。', 'success')
    else:
        flash('リンクが見つからないか、削除する権限がありません。', 'danger')
    return redirect(url_for('profile_edit_page'))

# --- 友達管理 ---
@app.route('/friends', methods=['GET', 'POST'])
@login_required
def friends_page():
    db = get_db()
    search_results = []
    query = ''

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        
        base_query = """
            SELECT u.id, u.username, u.profile_image 
            FROM users u 
            WHERE u.id != ? 
            AND u.account_type = ? 
            AND u.is_admin = 0
            AND NOT EXISTS (SELECT 1 FROM friends f WHERE (f.user_id = ? AND f.friend_id = u.id) OR (f.user_id = u.id AND f.friend_id = ?))
        """
        params = [current_user.id, current_user.account_type, current_user.id, current_user.id]

        if query:
            base_query += " AND u.username LIKE ?"
            params.append(f'%{query}%')
            search_results_raw = db.execute(base_query, params).fetchall()
        else:
            search_results_raw = db.execute(base_query, params).fetchall()

        for user_row in search_results_raw:
            search_results.append(dict(user_row))

    friends_list = db.execute("""
        SELECT u.id, u.username, u.profile_image, f.status 
        FROM friends f JOIN users u ON f.friend_id = u.id 
        WHERE f.user_id = ? AND f.status IN ('friend', 'favorite') AND u.account_type = ?
        ORDER BY f.status DESC, u.username
    """, (current_user.id, current_user.account_type)).fetchall()

    friend_requests = db.execute("""
        SELECT u.id, u.username, u.profile_image 
        FROM friends f JOIN users u ON f.user_id = u.id 
        WHERE f.friend_id = ? AND f.status = 'pending' AND u.account_type = ?
    """, (current_user.id, current_user.account_type)).fetchall()

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

    return render_template('friends.html', 
                                  friend_requests=friend_requests, 
                                  friends_list=friends_list, 
                                  search_results=search_results, 
                                  query=query, 
                                  invite_link=invite_link)

@app.route('/search_users')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    db = get_db()
    users = db.execute("""
        SELECT id, username, profile_image, status_message 
        FROM users 
        WHERE (username LIKE ? OR email LIKE ?) 
        AND id != ? 
        AND account_type = ? 
        AND is_admin = 0 
        AND status = 'active'
        LIMIT 10
    """, (f'%{query}%', f'%{query}%', current_user.id, current_user.account_type)).fetchall()
    
    return jsonify([dict(user) for user in users])

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
    
    recipient = db.execute("SELECT account_type FROM users WHERE id = ?", (recipient_id,)).fetchone()
    if not recipient or recipient['account_type'] != current_user.account_type:
        flash('このユーザーにリクエストを送信することはできません。', 'danger')
        return redirect(url_for('friends_page'))
    
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

@app.route('/reject_request/<int:sender_id>')
@login_required
def reject_request(sender_id):
    db = get_db()
    db.execute("DELETE FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'pending'", 
               (sender_id, current_user.id))
    db.commit()
    flash('友達リクエストを拒否しました。', 'info')
    
    if sender_id in online_users:
        socketio.emit('friend_request_rejected', 
                      {'rejector_username': current_user.username}, 
                      room=online_users[sender_id]['sid'])
        
    return redirect(url_for('friends_page'))

# --- グループ作成 ---
@app.route('/create_group_page')
@login_required
def create_group_page():
    friends_list = get_db().execute("SELECT id, username FROM users u JOIN friends f ON u.id = f.friend_id WHERE f.user_id = ? AND f.status = 'friend'", (current_user.id,)).fetchall()
    return render_template('create_group.html', friends_list=friends_list)

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
    opponent = db.execute('SELECT id, username, profile_image FROM users WHERE id = ? AND account_type = ?', (user_id, current_user.account_type)).fetchone()
    if not opponent:
        flash('チャット相手が見つからないか、アクセス権がありません。', 'warning')
        return redirect(url_for('main_app'))
    
    messages = [dict(msg) for msg in db.execute('SELECT * FROM private_messages WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?) ORDER BY timestamp ASC', (current_user.id, user_id, user_id, current_user.id)).fetchall()]
    db.execute('UPDATE private_messages SET is_read = 1 WHERE sender_id = ? AND recipient_id = ?', (user_id, current_user.id))
    db.commit()
    return render_template('chat.html', opponent=opponent, messages=messages, current_user=current_user)

@app.route('/app/keep_memo')
@login_required
def keep_memo():
    messages = [dict(m) for m in get_db().execute("SELECT * FROM private_messages WHERE sender_id = ? AND recipient_id = ? ORDER BY timestamp ASC", (current_user.id, current_user.id)).fetchall()]
    return render_template('keep_memo.html', messages=messages, current_user=current_user)

@app.route('/announcements')
@login_required
def announcements_page():
    announcements = get_db().execute('SELECT * FROM announcements ORDER BY created_at DESC').fetchall()
    return render_template('announcements.html', announcements=announcements)

@app.route('/app/ai_chat_page')
@login_required
def ai_chat_page():
    history = [dict(m) for m in get_db().execute("SELECT * FROM private_messages WHERE (sender_id = ? AND recipient_id = 0) OR (sender_id = 0 AND recipient_id = ?) ORDER BY timestamp ASC", (current_user.id, current_user.id,)).fetchall()]
    return render_template('ai_chat.html', history=history, current_user=current_user)

@app.route('/app/survey_page')
@login_required
def survey_page():
    db = get_db()
    survey = db.execute("SELECT * FROM surveys WHERE title = ?", ('TMHKchat利用満足度アンケート',)).fetchone()
    
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

    has_answered = db.execute("SELECT 1 FROM survey_responses WHERE user_id = ? AND survey_id = ?", (current_user.id, survey['id'])).fetchone()

    if has_answered:
        flash('以前にもご回答いただき、ありがとうございます！何度でもご意見をお寄せいただけます。', 'info')
    
    questions = db.execute("SELECT * FROM survey_questions WHERE survey_id = ?", (survey['id'],)).fetchall()
    options = {q['id']: db.execute("SELECT * FROM survey_options WHERE question_id = ?", (q['id'],)).fetchall() for q in questions}
    
    return render_template('survey.html', survey=survey, questions=questions, options=options, has_answered=has_answered)

@app.route('/survey/submit', methods=['POST'])
@login_required
def submit_survey():
    db = get_db()
    survey_id = request.form.get('survey_id')
    survey = db.execute("SELECT title FROM surveys WHERE id = ?", (survey_id,)).fetchone()
    survey_title = survey['title'] if survey else "アンケート"
    
    for key, value in request.form.items():
        if key.startswith('question-'):
            question_id = key.split('-')[1]
            question_type = key.split('-')[2]
            
            if question_type == 'text' and value:
                db.execute("INSERT INTO survey_responses (user_id, survey_id, question_id, response_text) VALUES (?, ?, ?, ?)",
                           (current_user.id, survey_id, question_id, value))
            elif question_type == 'multiple_choice':
                option_id = value
                db.execute("INSERT INTO survey_responses (user_id, survey_id, question_id, option_id) VALUES (?, ?, ?, ?)",
                           (current_user.id, survey_id, question_id, option_id))

    try:
        admin_user = db.execute("SELECT id FROM users WHERE is_admin = 1 AND status = 'active' LIMIT 1").fetchone()
        if admin_user:
            admin_id = admin_user['id']
            SYSTEM_USER_ID_SURVEY = -1
            notification_content = f"ユーザー「{current_user.username}」さんが「{survey_title}」に回答しました。"
            
            db.execute("INSERT INTO private_messages (sender_id, recipient_id, content) VALUES (?, ?, ?)",
                       (SYSTEM_USER_ID_SURVEY, admin_id, notification_content))
            
            if admin_id in online_users:
                 socketio.emit('new_private_message', {
                               'sender_id': SYSTEM_USER_ID_SURVEY,
                               'content': notification_content, 
                               'timestamp': datetime.now().isoformat()
                               }, room=online_users[admin_id]['sid'])
    except Exception as e:
        print(f"Error sending survey notification to admin: {e}")
        
    db.commit()
    flash('アンケートにご回答いただきありがとうございます！', 'success')
    return redirect(url_for('main_app'))

@app.route('/app/search_results', methods=['POST'])
@login_required
def main_search():
    return redirect(url_for('friends_page'))

# --- 「その他」タブ関連のルート ---
@app.route('/settings/auto_replies')
@login_required
def auto_replies_page():
    items = get_db().execute("SELECT * FROM auto_replies WHERE user_id = ? ORDER BY id DESC", (current_user.id,)).fetchall()
    return render_template('auto_replies.html', items=items)

@app.route('/settings/auto_replies/add', methods=['POST'])
@login_required
def add_auto_reply():
    keyword = request.form.get('keyword')
    response_message = request.form.get('response_message')
    if keyword and response_message:
        db = get_db()
        db.execute("INSERT INTO auto_replies (user_id, keyword, response_message) VALUES (?, ?, ?)",
                   (current_user.id, keyword, response_message))
        db.commit()
        flash('自動応答メッセージを追加しました。', 'success')
    return redirect(url_for('auto_replies_page'))

@app.route('/settings/auto_replies/delete/<int:item_id>')
@login_required
def delete_auto_reply(item_id):
    db = get_db()
    db.execute("DELETE FROM auto_replies WHERE id = ? AND user_id = ?", (item_id, current_user.id))
    db.commit()
    flash('自動応答メッセージを削除しました。', 'info')
    return redirect(url_for('auto_replies_page'))

@app.route('/settings/canned_messages')
@login_required
def canned_messages_page():
    items = get_db().execute("SELECT * FROM canned_messages WHERE user_id = ? ORDER BY id DESC", (current_user.id,)).fetchall()
    return render_template('canned_messages.html', items=items)

@app.route('/settings/canned_messages/add', methods=['POST'])
@login_required
def add_canned_message():
    title = request.form.get('title')
    content = request.form.get('content')
    if title and content:
        db = get_db()
        db.execute("INSERT INTO canned_messages (user_id, title, content) VALUES (?, ?, ?)",
                   (current_user.id, title, content))
        db.commit()
        flash('定型文を追加しました。', 'success')
    return redirect(url_for('canned_messages_page'))

@app.route('/settings/canned_messages/delete/<int:item_id>')
@login_required
def delete_canned_message(item_id):
    db = get_db()
    db.execute("DELETE FROM canned_messages WHERE id = ? AND user_id = ?", (item_id, current_user.id))
    db.commit()
    flash('定型文を削除しました。', 'info')
    return redirect(url_for('canned_messages_page'))

@app.route('/settings/block_list')
@login_required
def block_list_page():
    return render_template('block_list.html', users=[])

@app.route('/settings/hidden_list')
@login_required
def hidden_list_page():
    return render_template('hidden_list.html', users=[])

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
            print(f"User {user_id} unlocked achievement: {achievement_name}")

@app.route('/settings/custom_lists')
@login_required
def custom_lists_page():
    custom_lists = get_db().execute("SELECT * FROM custom_friend_lists WHERE user_id = ?", (current_user.id,)).fetchall()
    return render_template('custom_lists.html', custom_lists=custom_lists)

@app.route('/settings/custom_lists/create', methods=['POST'])
@login_required
def create_custom_list():
    list_name = request.form.get('list_name')
    if list_name:
        db = get_db()
        db.execute("INSERT INTO custom_friend_lists (user_id, list_name) VALUES (?, ?)", (current_user.id, list_name))
        db.commit()
    return redirect(url_for('custom_lists_page'))

@app.route('/settings/custom_lists/delete/<int:list_id>')
@login_required
def delete_custom_list(list_id):
    db = get_db()
    db.execute("DELETE FROM custom_friend_lists WHERE id = ? AND user_id = ?", (list_id, current_user.id))
    db.commit()
    return redirect(url_for('custom_lists_page'))

@app.route('/settings/custom_lists/update/<int:list_id>', methods=['POST'])
@login_required
def update_list_members(list_id):
    db = get_db()
    
    if not db.execute("SELECT 1 FROM custom_friend_lists WHERE id = ? AND user_id = ?", (list_id, current_user.id)).fetchone():
        flash('更新する権限がありません。', 'danger')
        return redirect(url_for('custom_lists_page'))

    db.execute("DELETE FROM custom_list_members WHERE list_id = ?", (list_id,))
    
    selected_members = request.form.getlist('members')
    
    for member_id in selected_members:
        db.execute("INSERT INTO custom_list_members (list_id, friend_id) VALUES (?, ?)", (list_id, int(member_id)))
    
    db.commit()
    
    flash('カスタムリストのメンバーを更新しました。', 'success')
    return redirect(url_for('custom_lists_page'))

# --- 管理者専用機能 ---
@app.route('/admin/survey_viewer', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_survey_viewer():
    db = get_db()
    users = db.execute("""
        SELECT DISTINCT u.id, u.username 
        FROM users u JOIN survey_responses sr ON u.id = sr.user_id 
        WHERE u.is_admin = 0 ORDER BY u.username
    """).fetchall()
    
    responses = []
    selected_user_id = None
    selected_user_name = None

    if request.method == 'POST':
        selected_user_id_str = request.form.get('user_id')
        if selected_user_id_str:
            selected_user_id = int(selected_user_id_str)
            responses = db.execute("""
                SELECT s.title as survey_title, sq.question_text, sr.response_text, so.option_text, sr.created_at
                FROM survey_responses sr
                JOIN surveys s ON sr.survey_id = s.id
                JOIN survey_questions sq ON sr.question_id = sq.id
                LEFT JOIN survey_options so ON sr.option_id = so.id
                WHERE sr.user_id = ?
                ORDER BY sr.created_at DESC
            """, (selected_user_id,)).fetchall()
            
            user_info = db.execute("SELECT username FROM users WHERE id = ?", (selected_user_id,)).fetchone()
            if user_info:
                selected_user_name = user_info['username']

    return render_template('admin_survey_viewer.html', 
                                  users=users, 
                                  responses=responses, 
                                  selected_user_id=selected_user_id,
                                  selected_user_name=selected_user_name)

@app.route('/admin/message_viewer', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_message_viewer():
    db = get_db()
    users = db.execute("SELECT id, username FROM users WHERE is_admin = 0 AND id > 0 ORDER BY username").fetchall()
    
    messages = []
    selected_user_id = None
    selected_user_name = None

    if request.method == 'POST':
        selected_user_id_str = request.form.get('user_id')
        if selected_user_id_str:
            selected_user_id = int(selected_user_id_str)
            messages_raw = db.execute("""
                SELECT p.*, s.username as sender_name, r.username as recipient_name
                FROM private_messages p
                LEFT JOIN users s ON p.sender_id = s.id
                LEFT JOIN users r ON p.recipient_id = r.id
                WHERE p.sender_id = ? OR p.recipient_id = ?
                ORDER BY p.timestamp ASC
            """, (selected_user_id, selected_user_id)).fetchall()
            
            for msg in messages_raw:
                msg_dict = dict(msg)
                if msg_dict['sender_id'] == -1:
                    msg_dict['sender_name'] = 'アンケート回答'
                if msg_dict['recipient_id'] == 0:
                    msg_dict['recipient_name'] = 'AIチャット'
                messages.append(msg_dict)
                
            selected_user = next((u for u in users if u['id'] == selected_user_id), None)
            if selected_user:
                selected_user_name = selected_user['username']

    return render_template('admin_message_viewer.html', 
                                  users=users, 
                                  messages=messages, 
                                  selected_user_id=selected_user_id,
                                  selected_user_name=selected_user_name)

@app.route('/upload_voice', methods=['POST'])
@login_required
def upload_voice():
    if 'voice_file' not in request.files:
        return jsonify({'success': False, 'message': 'ファイルが見つかりません'}), 400
    
    file = request.files['voice_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'ファイルが選択されていません'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(f"voice_{current_user.id}_{int(time.time())}.webm")
        voice_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'voices')
        os.makedirs(voice_folder, exist_ok=True)
        filepath = os.path.join(voice_folder, filename)
        file.save(filepath)
        file_url = f'voices/{filename}'
        return jsonify({'success': True, 'file_url': file_url})

    return jsonify({'success': False, 'message': '許可されていないファイル形式です'}), 400

# --- SocketIO イベントハンドラ ---
@socketio.on('send_private_message')
@login_required
def handle_send_private_message(data):
    recipient_id = int(data['recipient_id'])
    content = data['message']
    message_type = data.get('message_type', 'text')
    
    db = get_db()
    cursor = db.execute('INSERT INTO private_messages (sender_id, recipient_id, content, message_type) VALUES (?, ?, ?, ?)',
               (current_user.id, recipient_id, content, message_type))
    db.commit()

    message_id = cursor.lastrowid
    timestamp = datetime.now().isoformat()

    message_data = {
        'id': message_id,
        'sender_id': current_user.id, 
        'recipient_id': recipient_id,
        'content': content, 
        'message_type': message_type,
        'timestamp': timestamp,
        'username': current_user.username
    }
    
    emit('new_private_message', message_data, room=request.sid)
    
    if recipient_id != current_user.id and recipient_id in online_users:
        emit('new_private_message', message_data, room=online_users[recipient_id]['sid'])

@socketio.on('send_ai_message')
@login_required
def handle_send_ai_message(data):
    user_message = data['message'].strip()
    if not user_message: return

    db = get_db()
    db.execute('INSERT INTO private_messages (sender_id, recipient_id, content, is_from_ai) VALUES (?, 0, ?, 0)',
               (current_user.id, user_message))
    db.commit()

    response_text = None
    if ai_model:
        try:
            history_rows = db.execute("""
                SELECT content, is_from_ai FROM private_messages 
                WHERE ((sender_id = ? AND recipient_id = 0) OR (sender_id = 0 AND recipient_id = ?))
                ORDER BY timestamp ASC
            """, (current_user.id, current_user.id)).fetchall()

            full_prompt = ["### 会話履歴"]
            for row in history_rows:
                role = "AI" if row['is_from_ai'] else "あなた"
                full_prompt.append(f"{role}: {row['content']}")
            full_prompt.append("\n### 会話の続きを生成してください\nAI:")
            
            response = ai_model.generate_content('\n'.join(full_prompt))
            response_text = response.text
        except Exception as e:
            print(f"--- AI API ERROR --- \n {e}")
            pass

    if response_text is None:
        user_message_lower = user_message.lower()
        default_answer = "申し訳ありません、よく分かりませんでした。"
        response_text = default_answer
        if qa_list:
            for qa_pair in qa_list:
                for keyword in qa_pair.get('keywords', []):
                    if keyword.lower() in user_message_lower:
                        response_text = qa_pair.get('answer', default_answer)
                        break
                else: continue
                break
    
    socketio.sleep(0.5)

    db.execute('INSERT INTO private_messages (sender_id, recipient_id, content, is_from_ai) VALUES (0, ?, ?, 1)',
               (current_user.id, response_text))
    db.commit()
    
    emit('ai_response', {'message': response_text}, room=request.sid)

# --- スケジュールタスク ---
def scheduled_scraping_tasks():
    print("Running scheduled scraping tasks...")
    scrape_weather()
    scrape_traffic()
    scrape_disaster()
    print("Scheduled scraping tasks finished.")

def schedule_monthly_survey_announcement():
    with app.app_context():
        try:
            db = get_db()
            title = "月次アンケートご協力のお願い"
            content = "いつもTMHKchatをご利用いただきありがとうございます！サービスの品質向上のため、アンケートへのご協力をお願いいたします。「アンケート」ページよりご回答いただけます。"
            db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (title, content))
            db.commit()
            print("Monthly survey announcement created.")
        except Exception as e:
            print(f"Failed to create monthly survey announcement: {e}")

def schedule_yearly_ai_event():
    with app.app_context():
        if not ai_model:
            print("AI model not available for yearly event planning.")
            return
        try:
            db = get_db()
            prompt = "あなたはチャットアプリの企画担当者です。ユーザーが楽しめるオンラインイベントを1つ企画してください。イベント名と、簡潔で魅力的な説明文を考えてください。出力形式は「イベント名：(ここにイベント名)\n説明：(ここに説明文)」の形式でお願いします。"
            response = ai_model.generate_content(prompt)
            
            lines = response.text.split('\n')
            title = lines[0].replace("イベント名：", "").strip() if lines else "AI企画イベント"
            content = lines[1].replace("説明：", "").strip() if len(lines) > 1 else "詳細は後日お知らせします！"

            db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (f"【年間イベント予告】{title}", content))
            db.commit()
            print(f"Yearly AI event created: {title}")
        except Exception as e:
            print(f"Failed to create yearly AI event: {e}")

def schedule_weekly_feature_report():
    with app.app_context():
        if not ai_model:
            print("AI model not available for weekly report.")
            return
        try:
            db = get_db()
            one_week_ago = datetime.now() - timedelta(days=7)
            most_used_feature_row = db.execute("""
                SELECT activity_type, COUNT(*) as count 
                FROM activity_feed 
                WHERE created_at >= ?
                GROUP BY activity_type 
                ORDER BY count DESC 
                LIMIT 1
            """, (one_week_ago,)).fetchone()

            if most_used_feature_row:
                feature_map = {
                    'login': 'ログイン', 'timeline_post': 'タイムライン投稿',
                    'acquire_stamp': 'スタンプ取得', 'external_link': '外部リンク利用'
                }
                feature_name = feature_map.get(most_used_feature_row['activity_type'], '特定の機能')

                prompt = f"チャットアプリで、この1週間は「{feature_name}」機能が一番多く使われました。この情報をもとに、ユーザー全体に向けて「最近人気の機能」として紹介する、親しみやすい短いお知らせメッセージを作成してください。"
                response = ai_model.generate_content(prompt)
                
                title = "【今週のトレンド】人気の機能紹介！"
                content = response.text
                db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (title, content))
                db.commit()
                print("Weekly feature report created.")
        except Exception as e:
            print(f"Failed to create weekly feature report: {e}")

@app.route('/settings/custom_lists/manage/<int:list_id>')
@login_required
def manage_list_members(list_id):
    db = get_db()
    
    clist = db.execute("SELECT * FROM custom_friend_lists WHERE id = ? AND user_id = ?", (list_id, current_user.id)).fetchone()
    
    if not clist:
        flash('編集するリストが見つかりません。', 'warning')
        return redirect(url_for('custom_lists_page'))
    
    friends = db.execute("""
        SELECT u.id, u.username 
        FROM users u JOIN friends f ON u.id = f.friend_id 
        WHERE f.user_id = ? AND f.status IN ('friend', 'favorite') 
        ORDER BY u.username
    """, (current_user.id,)).fetchall()
    
    member_ids_rows = db.execute("SELECT friend_id FROM custom_list_members WHERE list_id = ?", (list_id,)).fetchall()
    
    member_ids = {row['friend_id'] for row in member_ids_rows}
    
    return render_template('manage_list_members.html', 
                                  clist=clist, 
                                  friends=friends, 
                                  member_ids=member_ids)


@app.route('/settings/alarm', methods=['GET', 'POST'])
@login_required
def alarm_settings_page():
    # 実際のアラーム設定ロジックはここに記述します
    # 今回はダミーのデータを渡すだけにします
    if request.method == 'POST':
        # ここでフォームから送信されたデータを保存する処理を将来的に追加
        flash('アラーム設定を保存しました。', 'success')
        return redirect(url_for('alarm_settings_page'))
        
    alarm_data = {
        'enabled': True, # DBなどから取得した現在の設定
        'time': '07:30'  # DBなどから取得した現在の設定
    }
    return render_template('alarm_settings.html', alarm=alarm_data)

@app.route('/settings/api')
@login_required
def api_settings_page():
    # ユーザーごとのAPIキーをDBで管理するのが理想ですが、
    # 今回はダミーのキーを生成して表示します
    # (ページをリロードするたびに変わります)
    api_key = str(uuid.uuid4())
    return render_template('api_settings.html', api_key=api_key)

@app.route('/app_manual')
@login_required
def app_manual_page():
    # manual.txtを読み込んで内容を渡す
    content = "説明書ファイル (manual.txt) が見つかりませんでした。"
    try:
        # server.pyと同じ階層にあるmanual.txtのパスを指定
        manual_path = os.path.join(app.root_path, 'manual.txt')
        with open(manual_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        # ファイルが見つからない場合のエラー処理
        print(f"Warning: '{manual_path}' not found.")
    except Exception as e:
        print(f"Error reading manual.txt: {e}")

    return render_template('app_manual.html', manual_content=content)

# --- 設定画面 (追加のルート) ---


@app.route('/settings/account_delete')
@login_required
def account_delete_page():
    return render_template('account_delete.html')

@app.route('/settings/age_verification')
@login_required
def age_verification_page():
    return render_template('age_verification.html')


@app.route('/settings/email_change')
@login_required
def email_change_page():
    return render_template('email_change.html')

@app.route('/settings/language')
@login_required
def language_settings_page():
    return render_template('language_settings.html')

@app.route('/settings/notification')
@login_required
def notification_settings_page():
    return render_template('notification_settings.html')

@app.route('/settings/password_change')
@login_required
def password_change_page():
    # この関数がなかったのでエラーになっていました
    return render_template('password_change.html')

@app.route('/settings/talk_backup')
@login_required
def talk_backup_page():
    return render_template('talk_backup.html')

@app.route('/settings/usage_time')
@login_required
def usage_time_page():
    return render_template('usage_time.html')



# --- スケジューラーとアプリの起動 ---
with app.app_context():
    if not scheduler.running:
        scheduler.add_job(scheduled_scraping_tasks, 'interval', hours=1, id='scraping_job', next_run_time=datetime.now())
        scheduler.add_job(schedule_monthly_survey_announcement, 'cron', month='*', day=1, hour=3, id='monthly_survey_job')
        scheduler.add_job(schedule_weekly_feature_report, 'cron', day_of_week='mon', hour=4, id='weekly_report_job')
        scheduler.add_job(schedule_yearly_ai_event, 'cron', year='*', month=1, day=1, hour=5, id='yearly_event_job')
        try:
            scheduler.start()
            print("Scheduler started.")
        except (KeyboardInterrupt, SystemExit):
            pass

# --- サーバーシャットダウン機能 ---
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'サーバーをシャットダウンします...'

if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=False)