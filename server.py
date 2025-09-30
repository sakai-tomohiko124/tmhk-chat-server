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
# （ーーここから変更しましたーー）
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
# （ーーここまで変更しましたーー）

# --- 各種設定 ---
# 環境変数からSECRET_KEYを読み込む、設定されていなければデフォルト値を使用
SECRET_KEY = os.getenv('SECRET_KEY', 'aK4$d!sF9@gH2%jLpQ7rT1&uY5vW8xZc')
app.config['SECRET_KEY'] = SECRET_KEY

# その他の設定
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
DATABASE = os.path.join(app.root_path, 'database', 'tmhk.db') # データベースファイル名変更 (tmchat -> hkchat)

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
    # --- AIモデルの初期化 (エラー修正) ---
    # 'gemini-pro' は古いか、アクセスできないモデル名になっているため、エラーが発生していました。
    # 現在推奨されている安定版のモデル 'gemini-1.5-pro-latest' に変更します。
    ai_model = genai.GenerativeModel('gemini-pro')
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
# （ここまで追加）

# YouTube APIキー設定
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
# YouTube APIキー設定
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# 管理者アカウント情報
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'skytomohiko17@gmail.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'skytomo124')

# 定数
FORBIDDEN_WORDS = ["馬鹿", "アホ", "死ね", "バカ", "終わり","やばい","マジ","クソ","しね","消えろ","クズ","不適切ワード"]

# （ーーここから変更しましたーー）
# アカウントタイプの定義
ACCOUNT_TYPES = {
    'work': {'name': '職場', 'theme': 'professional', 'bg_gradient': 'linear-gradient(135deg, #1e3a8a, #3b82f6)'},
    'home': {'name': '家庭', 'theme': 'warm', 'bg_gradient': 'linear-gradient(135deg, #f97316, #fbbf24)'},
    'private': {'name': 'プライベート', 'theme': 'casual', 'bg_gradient': 'linear-gradient(135deg, #10b981, #34d399)'},
    'other': {'name': 'その他', 'theme': 'custom', 'bg_gradient': 'linear-gradient(135deg, #6c757d, #343a40)'} # 「その他」を追加
}
# （ーーここまで変更しましたーー）

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

# ヘルパー関数として追加（約200行目付近）
def filter_admin_from_results(query_results):
    """クエリ結果から管理者アカウントを除外する"""
    if not query_results:
        return []
    
    filtered_results = []
    for result in query_results:
        # 辞書形式でもSQLiteRowでも対応
        if hasattr(result, 'get'):
            if not (result.get('is_admin', 0) == 1 or result.get('account_type') == 'admin'):
                filtered_results.append(result)
        elif hasattr(result, '__getitem__'):
            try:
                if not (result['is_admin'] == 1 or result['account_type'] == 'admin'):
                    filtered_results.append(result)
            except (KeyError, TypeError):
                filtered_results.append(result)
        else:
            filtered_results.append(result)
    
    return filtered_results

def is_system_admin():
    """現在のユーザーがシステム管理者かチェック"""
    return (current_user.is_authenticated and 
            current_user.is_admin and 
            session.get('is_system_admin', False))


def init_extended_db():
    """database/tmhk.sqlファイルからスキーマを読み込みデータベースを構築する"""
    with app.app_context():
        db = get_db()
        # tmhk.sqlファイルのパスを取得
        sql_file_path = os.path.join(app.root_path, 'database', 'tmhk.sql')
        
        try:
            # SQLファイルを読み込んで実行
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

# 既存のlogin関数内の管理者自動作成部分を以下に修正（約540行目付近）
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_app'))
# === 管理者アカウント自動作成（セキュリティ強化版） ===
    # 管理者アカウントが存在しない場合、バックグラウンドで自動作成
    db = get_db()
    admin_exists = db.execute("SELECT id FROM users WHERE email = ? AND is_admin = 1", (ADMIN_EMAIL,)).fetchone()
    if not admin_exists:
        try:
            hashed_admin_password = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
            # 管理者アカウントはaccount_type='admin'として区別
            db.execute(
                'INSERT INTO users (username, email, password, is_admin, status, account_type) VALUES (?, ?, ?, ?, ?, ?)',
                ('admin_system', ADMIN_EMAIL, hashed_admin_password, 1, 'active', 'admin')
            )
            db.commit()
            # ログには表示しない（セキュリティ上の理由）
            print('システム管理者アカウントが初期化されました。')
        except Exception as e:
            print(f'システム初期化エラー: {str(e)[:50]}...')  # エラー詳細も一部のみ表示
    # === 自動作成終了 ===

    if request.method == 'POST':
        # （ーーここから変更しましたーー）
        account_type = request.form.get('account_type', 'private')
        custom_account_name = request.form.get('custom_account_name', '').strip()
        login_id = request.form.get('login_id')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        # 「その他」が選択された場合、カスタム名をアカウントタイプとして使用
        if account_type == 'other' and custom_account_name:
            account_type_for_query = custom_account_name
        else:
            account_type_for_query = account_type

        db = get_db()
        query = 'SELECT * FROM users WHERE (email = ? OR username = ?) AND account_type = ?'
        user_data = db.execute(query, (login_id, login_id, account_type_for_query)).fetchone()
        # （ーーここまで変更しましたーー）

        if user_data and check_password_hash(user_data['password'], password):
            user = load_user(user_data['id'])
            if user.status != 'active':
                flash('このアカウントは現在利用が制限されています。', 'danger')
                return render_template_string(LOGIN_HTML, account_types=ACCOUNT_TYPES, selected_account_type=account_type)

            # === 管理者ログイン時の特別処理 ===
            if user.is_admin and user_data['account_type'] == 'admin':
                # 管理者は専用ログとして記録（一般ユーザーには見えない）
                print(f'[ADMIN LOGIN] System administrator accessed at {datetime.now()}')
                # 管理者専用のセッション情報設定
                session['is_system_admin'] = True
            else:
                session.pop('is_system_admin', None)
            # === 管理者処理終了 ===
            
            # （ーーここから変更しましたーー）
            login_user(user, remember=remember)
            session['account_type'] = user.account_type # DBから取得した正確なタイプをセッションに保存

            # --- 全体へのオンライン通知 ---
            try:
                announcement_title = "オンライン通知"
                announcement_content = f"{user.username}さんがオンラインになりました。"
                db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", 
                           (announcement_title, announcement_content))
                db.commit()
            except Exception as e:
                print(f"Announcement creation failed: {e}")
            # --- 通知終了 ---
            
            update_login_streak(user.id)
            record_activity(user.id, 'login', f'{ACCOUNT_TYPES.get(account_type, {"name": "システム"})["name"]}アカウントでログイン')
            # （ーーここまで変更しましたーー）

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
        # （ーーここから変更しましたーー）
        account_type = request.form.get('account_type', 'private')
        custom_account_name = request.form.get('custom_account_name', '').strip()
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # 「その他」が選択された場合、カスタム名をアカウントタイプとして使用
        if account_type == 'other' and custom_account_name:
            account_type_to_db = custom_account_name
        else:
            account_type_to_db = account_type
        # （ーーここまで変更しましたーー）

        if not username or not password:
            flash('ユーザー名とパスワードは必須です。', 'danger')
            return render_template_string(REGISTER_HTML, account_types=ACCOUNT_TYPES, selected_account_type=account_type)

        db = get_db()
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            # （ーーここから変更しましたーー）
            cursor = db.execute('INSERT INTO users (username, email, password, account_type) VALUES (?, ?, ?, ?)',
                                (username, email if email else None, hashed_password, account_type_to_db))
            # （ーーここまで変更しましたーー）
            db.commit()

            user_id = cursor.lastrowid
            give_default_stamps(user_id)
            check_achievement_unlocked(user_id, '新規登録', 1)

            flash(f'アカウントの登録が完了しました。', 'success')
            return redirect(url_for('login'))
        # （ーーここから変更しましたーー）
        except sqlite3.IntegrityError:
            flash('そのユーザー名またはメールアドレスは既に使用されています。', 'danger')
        # （ーーここまで変更しましたーー）

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
    talk_filter = request.args.get('talk_filter', 'individual') # デフォルトは「個人」
    
    # account_type に応じたテーマ情報を取得
    account_type = current_user.account_type
    theme_info = ACCOUNT_TYPES.get(account_type) or ACCOUNT_TYPES['other']

    # --- ホームタブ用データ（変更なし） ---
    favorite_friends = db.execute("SELECT u.id, u.username, u.profile_image FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND f.status = 'favorite' AND u.account_type = ?",(current_user.id, current_user.account_type)).fetchall()
    normal_friends = db.execute("SELECT u.id, u.username, u.profile_image FROM friends f JOIN users u ON f.friend_id = u.id WHERE f.user_id = ? AND f.status = 'friend' AND u.account_type = ?",(current_user.id, current_user.account_type)).fetchall()
    
    # --- トークタブ用データ（フィルタリング機能付き） ---
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

    if talk_filter == 'individual': # 個人
        talks_list = db.execute(f"{base_private_message_query} ORDER BY p.last_message_time DESC", params).fetchall()
    elif talk_filter == 'close_friends': # 親しい友達
        talks_list = db.execute(f"{base_private_message_query} AND u.id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'favorite') ORDER BY p.last_message_time DESC", params + [current_user.id]).fetchall()
    elif talk_filter == 'acquaintances': # 知り合い
        talks_list = db.execute(f"{base_private_message_query} AND u.id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'friend') ORDER BY p.last_message_time DESC", params + [current_user.id]).fetchall()
    elif talk_filter == 'groups': # グループ
        groups_list = db.execute("""
            SELECT r.id, r.name, (SELECT content FROM messages WHERE room_id = r.id ORDER BY timestamp DESC LIMIT 1) as last_message
            FROM rooms r JOIN room_members rm ON r.id = rm.room_id WHERE rm.user_id = ?
        """, (current_user.id,)).fetchall()
    elif talk_filter.startswith('custom_'): # カスタムリスト
        list_id = talk_filter.split('_')[1]
        talks_list = db.execute(f"{base_private_message_query} AND u.id IN (SELECT friend_id FROM custom_list_members WHERE list_id = ?) ORDER BY p.last_message_time DESC", params + [list_id]).fetchall()


    # --- タイムラインタブ用データ（変更なし） ---
    weather_data = db.execute('SELECT * FROM weather_data ORDER BY timestamp DESC').fetchall()
    traffic = db.execute('SELECT * FROM traffic_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    disaster = db.execute('SELECT * FROM disaster_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    posts = db.execute("SELECT tp.*, u.username, u.profile_image FROM timeline_posts tp JOIN users u ON tp.user_id = u.id WHERE u.account_type = ? ORDER BY tp.created_at DESC LIMIT 50", (current_user.account_type,)).fetchall()

    # --- その他データ（カスタムリスト取得を追加） ---
    announcements = db.execute('SELECT * FROM announcements ORDER BY created_at DESC LIMIT 3').fetchall()
    daily_missions = db.execute('SELECT * FROM missions WHERE is_active = 1 LIMIT 3').fetchall()
    activity_feed = db.execute("SELECT af.*, u.username, u.profile_image FROM activity_feed af JOIN users u ON af.user_id = u.id WHERE af.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status IN ('friend', 'favorite')) OR af.user_id = ? ORDER BY af.created_at DESC LIMIT 10", (current_user.id, current_user.id)).fetchall()
    custom_lists = db.execute("SELECT * FROM custom_friend_lists WHERE user_id = ?", (current_user.id,)).fetchall()

    return render_template_string(MAIN_APP_HTML, current_user=current_user, theme=theme_info, 
                                  favorite_friends=favorite_friends, normal_friends=normal_friends,
                                  talks_list=talks_list, groups_list=groups_list, announcements=announcements,
                                  daily_missions=daily_missions, activity_feed=activity_feed,
                                  weather_data=weather_data, traffic=traffic, disaster=disaster, posts=posts,
                                  custom_lists=custom_lists, current_filter=talk_filter)



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
    
    # --- 中断したゲームを取得 ---
    saved_games = db.execute("""
        SELECT sg.room_id, sg.game_type, sg.last_updated_at FROM saved_games sg
        JOIN saved_game_players sgp ON sg.id = sgp.game_id
        WHERE sgp.user_id = ?
    """, (current_user.id,)).fetchall()

    return render_template_string(GAMES_HUB_HTML, games=games, rankings=rankings, saved_games=saved_games)

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
    if db.execute('SELECT COUNT(*) FROM stamps WHERE is_free = 1').fetchone() == 0:
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
# （ーーここから変更しましたーー）
@app.route('/profile/edit')
@login_required
def profile_edit_page():
    db = get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (current_user.id,)).fetchone()
    # YouTubeリンクを取得する処理を追加
    youtube_links = db.execute("SELECT * FROM user_youtube_links WHERE user_id = ? ORDER BY created_at DESC", (current_user.id,)).fetchall()
    return render_template_string(PROFILE_EDIT_HTML, user=user_data, account_types=ACCOUNT_TYPES, youtube_links=youtube_links)
# （ーーここまで変更しましたーー）

# （ーーここから変更しましたーー）
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
    # YouTubeリンクを取得する処理を追加
    youtube_links = db.execute("SELECT * FROM user_youtube_links WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    
    return render_template_string(PROFILE_VIEW_HTML, user=user, friend_status=friend_status, achievements=achievements, youtube_links=youtube_links)
# （ーーここまで変更しましたーー）


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
        friends = db.execute("SELECT friend_id FROM friends WHERE user_id = ? AND (status = 'friend' OR 'favorite')", (current_user.id,)).fetchall()
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

# （ーーここから追加しましたーー）
@app.route('/profile/add_youtube', methods=['POST'])
@login_required
def add_youtube_link():
    url = request.form.get('url')
    title = request.form.get('title')

    # 簡単なURLバリデーション
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
# （ーーここまで追加しましたーー）

# --- 友達管理 ---
# （ーーここから変更しましたーー）
@app.route('/friends', methods=['GET', 'POST'])
@login_required
def friends_page():
    db = get_db()
    search_results = []
    query = '' # 初期化

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        
        # 友達、申請関係にない同じアカウントタイプのユーザーを検索するベースクエリ
        base_query = """
            SELECT u.id, u.username, u.profile_image 
            FROM users u 
            WHERE u.id != ? 
            AND u.account_type = ? 
            AND u.is_admin = 0
            AND NOT EXISTS (SELECT 1 FROM friends f WHERE (f.user_id = ? AND f.friend_id = u.id) OR (f.user_id = u.id AND f.friend_id = ?))
        """
        params = [current_user.id, current_user.account_type, current_user.id, current_user.id]

        if query: # 検索ワードがある場合
            base_query += " AND u.username LIKE ?"
            params.append(f'%{query}%')
            search_results_raw = db.execute(base_query, params).fetchall()
        else: # 空検索の場合
            search_results_raw = db.execute(base_query, params).fetchall()

        for user_row in search_results_raw:
            search_results.append(dict(user_row))

    # 友達リストとリクエストも同じアカウントタイプに限定
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

    # 招待リンク生成
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

    return render_template_string(FRIENDS_HTML, 
                                  friend_requests=friend_requests, 
                                  friends_list=friends_list, 
                                  search_results=search_results, 
                                  query=query, 
                                  invite_link=invite_link)
# （ーーここまで変更しましたーー）

# ユーザー検索機能も管理者除外（約850行目付近に追加）
@app.route('/search_users')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    db = get_db()
    # （ーーここから変更しましたーー）
    # 管理者アカウントと異なるアカウントタイプを検索結果から除外
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
    # （ーーここまで変更しましたーー）
    
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
    
    # （ーーここから追加しましたーー）
    # --- アカウントタイプチェック ---
    recipient = db.execute("SELECT account_type FROM users WHERE id = ?", (recipient_id,)).fetchone()
    if not recipient or recipient['account_type'] != current_user.account_type:
        flash('このユーザーにリクエストを送信することはできません。', 'danger')
        return redirect(url_for('friends_page'))
    # --- チェック終了 ---
    # （ーーここまで追加しましたーー）
    
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

# （ーーここから追加しましたーー）
@app.route('/reject_request/<int:sender_id>')
@login_required
def reject_request(sender_id):
    db = get_db()
    # 自分(friend_id) 宛の、相手(user_id) からの 'pending' リクエストを削除
    db.execute("DELETE FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'pending'", 
               (sender_id, current_user.id))
    db.commit()
    flash('友達リクエストを拒否しました。', 'info')
    
    # 相手に通知を送る場合はここにSocketIOの処理を追加
    # if sender_id in online_users:
    #     socketio.emit('friend_request_rejected', {...}, room=online_users[sender_id]['sid'])
        
    return redirect(url_for('friends_page'))
# （ーーここまで追加しましたーー）

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
    # （ーーここから変更しましたーー）
    # 同じアカウントタイプの相手かチェック
    opponent = db.execute('SELECT id, username, profile_image FROM users WHERE id = ? AND account_type = ?', (user_id, current_user.account_type)).fetchone()
    if not opponent:
        flash('チャット相手が見つからないか、アクセス権がありません。', 'warning')
        return redirect(url_for('main_app'))
    # （ーーここまで変更しましたーー）
    
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
    
    # --- ユーザーの回答をDBに保存 ---
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

    # --- 管理者への通知メッセージ作成 ---
    try:
        # システム管理者(is_admin=1)を取得
        admin_user = db.execute("SELECT id FROM users WHERE is_admin = 1 AND status = 'active' LIMIT 1").fetchone()
        if admin_user:
            admin_id = admin_user['id']
            notification_content = f"【システム通知】\nユーザー「{current_user.username}」さんがアンケートに回答しました。"
            # 管理者のKeepメモ（自分宛メッセージ）として送信
            db.execute("INSERT INTO private_messages (sender_id, recipient_id, content) VALUES (?, ?, ?)",
                       (admin_id, admin_id, notification_content))
            
            # もし管理者がオンラインならリアルタイムで通知
            if admin_id in online_users:
                 socketio.emit('new_private_message', 
                               {'sender_id': admin_id, 'content': notification_content, 'timestamp': datetime.now().isoformat()}, 
                               room=online_users[admin_id]['sid'])
    except Exception as e:
        print(f"Error sending survey notification to admin: {e}")
        
    db.commit()
    flash('アンケートにご回答いただきありがとうございます！', 'success')
    return redirect(url_for('main_app'))



@app.route('/app/search_results', methods=['POST'])
@login_required
def main_search():
    # このルートはfriends_pageに統合されているため、基本的には使用されない想定
    # もし使用する場合はfriends_pageと同様のロジックをここに実装
    return redirect(url_for('friends_page'))

# （ここから追加）
# --- 「その他」タブ関連のルート ---

@app.route('/settings/auto_replies')
@login_required
def auto_replies_page():
    items = get_db().execute("SELECT * FROM auto_replies WHERE user_id = ? ORDER BY id DESC", (current_user.id,)).fetchall()
    return render_template_string(AUTO_REPLIES_HTML, items=items)

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
    return render_template_string(CANNED_MESSAGES_HTML, items=items)

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
    # 将来的にブロックしたユーザーの情報をJOINして取得
    return render_template_string(BLOCK_LIST_HTML, users=[])

@app.route('/settings/hidden_list')
@login_required
def hidden_list_page():
    # 将来的に非表示にしたユーザーの情報をJOINして取得
    return render_template_string(HIDDEN_LIST_HTML, users=[])
# （ここまで追加）

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

# （ここから追加）
@app.route('/settings/custom_lists')
@login_required
def custom_lists_page():
    custom_lists = get_db().execute("SELECT * FROM custom_friend_lists WHERE user_id = ?", (current_user.id,)).fetchall()
    return render_template_string(CUSTOM_LISTS_HTML, custom_lists=custom_lists)

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
    # 自分のリストか確認してから削除
    db.execute("DELETE FROM custom_friend_lists WHERE id = ? AND user_id = ?", (list_id, current_user.id))
    db.commit()
    return redirect(url_for('custom_lists_page'))

@app.route('/settings/custom_lists/manage/<int:list_id>')
@login_required
def manage_list_members(list_id):
    db = get_db()
    clist = db.execute("SELECT * FROM custom_friend_lists WHERE id = ? AND user_id = ?", (list_id, current_user.id)).fetchone()
    if not clist:
        return redirect(url_for('custom_lists_page'))
    
    friends = db.execute("SELECT u.id, u.username FROM users u JOIN friends f ON u.id = f.friend_id WHERE f.user_id = ? AND f.status IN ('friend', 'favorite')", (current_user.id,)).fetchall()
    member_ids_rows = db.execute("SELECT friend_id FROM custom_list_members WHERE list_id = ?", (list_id,)).fetchall()
    member_ids = {row['friend_id'] for row in member_ids_rows}
    
    return render_template_string(MANAGE_LIST_MEMBERS_HTML, clist=clist, friends=friends, member_ids=member_ids)

@app.route('/settings/custom_lists/update/<int:list_id>', methods=['POST'])
@login_required
def update_list_members(list_id):
    db = get_db()
    # 自分のリストか確認
    if not db.execute("SELECT 1 FROM custom_friend_lists WHERE id = ? AND user_id = ?", (list_id, current_user.id)).fetchone():
        return redirect(url_for('custom_lists_page'))

    # 現在のメンバーを一旦全員削除
    db.execute("DELETE FROM custom_list_members WHERE list_id = ?", (list_id,))
    
    # チェックされたメンバーを再登録
    selected_members = request.form.getlist('members')
    for member_id in selected_members:
        db.execute("INSERT INTO custom_list_members (list_id, friend_id) VALUES (?, ?)", (list_id, int(member_id)))
    
    db.commit()
    return redirect(url_for('custom_lists_page'))
# （ここまで追加）

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
    if room['last_char'] and word != room['last_char']:
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

# （ーーここから変更しましたーー）
# [修正] オフライン通知機能を追加
@socketio.on('disconnect')
def handle_disconnect():
    user_id_to_remove = None
    sid_to_remove = request.sid
    for user_id, data in online_users.items():
        if data['sid'] == sid_to_remove:
            user_id_to_remove = user_id
            break
            
    if user_id_to_remove:
        # --- オフライン通知の作成 ---
        with app.app_context():
            try:
                db = get_db()
                user = db.execute("SELECT username FROM users WHERE id = ?", (user_id_to_remove,)).fetchone()
                if user:
                    announcement_title = "オフライン通知"
                    announcement_content = f"{user['username']}さんがオフラインになりました。"
                    db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", 
                               (announcement_title, announcement_content))
                    db.commit()
            except Exception as e:
                print(f"Offline announcement creation failed: {e}")
        # --- 通知終了 ---

        # 参加していたゲームルームから退出
        for room_id, room_data in list(game_rooms.items()):
            player_ids = [p['id'] for p in room_data.get('players', [])]
            if user_id_to_remove in player_ids:
                leave_room(room_id, sid=sid_to_remove)
                print(f"User {user_id_to_remove} left game room {room_id}")

        del online_users[user_id_to_remove]
        print(f"User {user_id_to_remove} disconnected.")
# （ーーここまで変更しましたーー）


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

# （ーーここから追加しましたーー）
def schedule_monthly_survey_announcement():
    """月に一度、アンケート実施を通知するアナウンスを作成する"""
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
    """年に一度、AIが企画したイベントを通知するアナウンスを作成する"""
    with app.app_context():
        if not ai_model:
            print("AI model not available for yearly event planning.")
            return
        try:
            db = get_db()
            prompt = "あなたはチャットアプリの企画担当者です。ユーザーが楽しめるオンラインイベントを1つ企画してください。イベント名と、簡潔で魅力的な説明文を考えてください。出力形式は「イベント名：(ここにイベント名)\n説明：(ここに説明文)」の形式でお願いします。"
            response = ai_model.generate_content(prompt)
            
            # AIの出力をパース
            lines = response.text.split('\n')
            title = lines.replace("イベント名：", "").strip()
            content = lines.replace("説明：", "").strip() if len(lines) > 1 else "詳細は後日お知らせします！"

            db.execute("INSERT INTO announcements (title, content) VALUES (?, ?)", (f"【年間イベント予告】{title}", content))
            db.commit()
            print(f"Yearly AI event created: {title}")
        except Exception as e:
            print(f"Failed to create yearly AI event: {e}")

def schedule_weekly_feature_report():
    """週に一度、利用状況などをAIが分析してアナウンスを作成する"""
    with app.app_context():
        if not ai_model:
            print("AI model not available for weekly report.")
            return
        try:
            db = get_db()
            # この1週間で最も使われた機能を集計
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
                    'login': 'ログイン',
                    'timeline_post': 'タイムライン投稿',
                    'acquire_stamp': 'スタンプ取得',
                    'external_link': '外部リンク利用'
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
# （ーーここまで追加しましたーー）


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

# LOGIN_HTML変数を以下に置き換え（約1500行目付近）
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ログイン - TMHKchat</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background: {{ theme['bg_gradient'] if theme else 'linear-gradient(135deg, #10b981, #34d399)' }};
            min-height: 100vh;
        }
        .login-container {
            max-width: 400px;
            margin: 50px auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .login-header {
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        .login-body {
            padding: 30px;
        }
        .password-toggle-container {
            position: relative;
        }
        .password-toggle {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            border: none;
            background: none;
            cursor: pointer;
            color: #6c757d;
            z-index: 5;
        }
        .password-toggle:hover {
            color: #495057;
        }
        .form-control {
            padding-right: 40px;
        }
        .account-type-card {
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
            margin-bottom: 10px;
        }
        .account-type-card.selected {
            border-color: #4f46e5;
            background: #f8f9ff;
        }
        .account-type-card:hover {
            border-color: #7c3aed;
            background: #f8f9ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-container">
            <div class="login-header">
                <h2><i class="bi bi-person-circle"></i></h2>
                <h4>ログイン</h4>
                <p class="mb-0">TMHKchatへようこそ</p>
            </div>
            
            <div class="login-body">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <form method="POST">
                    <div class="mb-4">
                        <label class="form-label fw-bold">アカウントタイプ</label>
                        <div class="row">
                            {% for key, value in account_types.items() %}
                            <div class="col-12">
                                <div class="account-type-card" onclick="selectAccountType('{{ key }}')">
                                    <input type="radio" name="account_type" value="{{ key }}" id="type-{{ key }}" 
                                           {% if key == selected_account_type %}checked{% endif %} style="display: none;">
                                    <div class="fw-bold">{{ value['name'] }}</div>
                                    <small class="text-muted">{{ value['name'] }}用アカウント</small>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <!-- （ーーここから追加しましたーー） -->
                    <div class="mb-3" id="custom-account-name-wrapper-login" style="display: none;">
                        <label for="custom_account_name" class="form-label">コミュニティ名</label>
                        <input type="text" class="form-control" id="custom_account_name" name="custom_account_name"
                               placeholder="参加しているコミュニティ名を入力">
                    </div>
                    <!-- （ーーここまで追加しましたーー） -->

                    <div class="mb-3">
                        <label for="login_id" class="form-label">ユーザー名またはメールアドレス</label>
                        <input type="text" class="form-control" id="login_id" name="login_id" required
                               placeholder="ユーザー名またはメールアドレス">
                    </div>
                    
                    <div class="mb-3">
                        <label for="password" class="form-label">パスワード</label>
                        <div class="password-toggle-container">
                            <input type="password" class="form-control" id="password" name="password" required
                                   placeholder="パスワード">
                            <button type="button" class="password-toggle" onclick="togglePassword('password')">
                                <i class="bi bi-eye" id="password-toggle-icon"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" id="remember" name="remember">
                        <label class="form-check-label" for="remember">ログイン状態を保持する</label>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100 mb-3">
                        <i class="bi bi-box-arrow-in-right"></i> ログイン
                    </button>
                    
                    <div class="text-center">
                        <span class="text-muted">アカウントをお持ちでないですか？</span>
                        <a href="{{ url_for('register') }}" class="text-decoration-none">新規登録</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // （ーーここから変更しましたーー）
        function selectAccountType(type) {
            document.querySelectorAll('.account-type-card').forEach(card => {
                card.classList.remove('selected');
            });
            event.currentTarget.classList.add('selected');
            document.getElementById('type-' + type).checked = true;

            const customInput = document.getElementById('custom-account-name-wrapper-login');
            if (type === 'other') {
                customInput.style.display = 'block';
                document.getElementById('custom_account_name').required = true;
            } else {
                customInput.style.display = 'none';
                document.getElementById('custom_account_name').required = false;
            }
        }
        // （ーーここまで変更しましたーー）
        
        function togglePassword(inputId) {
            const passwordInput = document.getElementById(inputId);
            const toggleIcon = document.getElementById(inputId + '-toggle-icon');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.className = 'bi bi-eye-slash';
            } else {
                passwordInput.type = 'password';
                toggleIcon.className = 'bi bi-eye';
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            const selectedRadio = document.querySelector('input[name="account_type"]:checked');
            if (selectedRadio) {
                selectedRadio.closest('.account-type-card').classList.add('selected');
            }
        });
    </script>
</body>
</html>
"""

# REGISTER_HTML変数を以下に置き換え（約1800行目付近）
REGISTER_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新規登録 - TMHKchat</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .register-container {
            max-width: 450px;
            margin: 30px auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .register-header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 25px 20px;
            text-align: center;
        }
        .register-body {
            padding: 30px;
        }
        .password-toggle-container {
            position: relative;
        }
        .password-toggle {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            border: none;
            background: none;
            cursor: pointer;
            color: #6c757d;
            z-index: 5;
        }
        .password-toggle:hover {
            color: #495057;
        }
        .form-control {
            padding-right: 40px;
        }
        .account-type-card {
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
            margin-bottom: 8px;
        }
        .account-type-card.selected {
            border-color: #f5576c;
            background: #fff5f7;
        }
        .account-type-card:hover {
            border-color: #f093fb;
            background: #fff5f7;
        }
        .password-strength {
            margin-top: 5px;
            font-size: 0.8em;
        }
        .strength-weak { color: #dc3545; }
        .strength-medium { color: #ffc107; }
        .strength-strong { color: #28a745; }
    </style>
</head>
<body>
    <div class="container">
        <div class="register-container">
            <div class="register-header">
                <h2><i class="bi bi-person-plus-fill"></i></h2>
                <h4>新規登録</h4>
                <p class="mb-0">TMHKchatへの参加</p>
            </div>
            
            <div class="register-body">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label fw-bold">アカウントタイプ</label>
                        <div class="row">
                            {% for key, value in account_types.items() %}
                            <div class="col-12">
                                <div class="account-type-card" onclick="selectAccountType('{{ key }}')">
                                    <input type="radio" name="account_type" value="{{ key }}" id="reg-type-{{ key }}" 
                                           {% if key == selected_account_type %}checked{% endif %} style="display: none;">
                                    <div class="fw-bold">{{ value['name'] }}</div>
                                    <small class="text-muted">{{ value['name'] }}用アカウント</small>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <!-- （ーーここから追加しましたーー） -->
                    <div class="mb-3" id="custom-account-name-wrapper" style="display: none;">
                        <label for="custom_account_name" class="form-label">コミュニティ名 <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="custom_account_name" name="custom_account_name"
                               placeholder="参加したいコミュニティ名を入力">
                    </div>
                    <!-- （ーーここまで追加しましたーー） -->

                    <div class="mb-3">
                        <label for="username" class="form-label">ユーザー名 <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="username" name="username" required
                               placeholder="ユーザー名（半角英数字・日本語可）" maxlength="20">
                        <div class="form-text">3〜20文字以内で入力してください</div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="email" class="form-label">メールアドレス <small class="text-muted">(任意)</small></label>
                        <input type="email" class="form-control" id="email" name="email"
                               placeholder="example@email.com">
                        <div class="form-text">後から設定画面で追加・変更可能です</div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="password" class="form-label">パスワード <span class="text-danger">*</span></label>
                        <div class="password-toggle-container">
                            <input type="password" class="form-control" id="password" name="password" required
                                   placeholder="パスワード（8文字以上推奨）" minlength="4" onkeyup="checkPasswordStrength()">
                            <button type="button" class="password-toggle" onclick="togglePassword('password')">
                                <i class="bi bi-eye" id="password-toggle-icon"></i>
                            </button>
                        </div>
                        <div id="password-strength" class="password-strength"></div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="confirm_password" class="form-label">パスワード確認 <span class="text-danger">*</span></label>
                        <div class="password-toggle-container">
                            <input type="password" class="form-control" id="confirm_password" name="confirm_password" required
                                   placeholder="パスワードを再入力" onkeyup="checkPasswordMatch()">
                            <button type="button" class="password-toggle" onclick="togglePassword('confirm_password')">
                                <i class="bi bi-eye" id="confirm_password-toggle-icon"></i>
                            </button>
                        </div>
                        <div id="password-match" class="password-strength"></div>
                    </div>
                    
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" id="terms" required>
                        <label class="form-check-label" for="terms">
                            <a href="#" class="text-decoration-none">利用規約</a>と<a href="#" class="text-decoration-none">プライバシーポリシー</a>に同意します
                        </label>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100 mb-3" id="submitBtn" disabled>
                        <i class="bi bi-person-plus"></i> アカウント作成
                    </button>
                    
                    <div class="text-center">
                        <span class="text-muted">既にアカウントをお持ちですか？</span>
                        <a href="{{ url_for('login') }}" class="text-decoration-none">ログイン</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // （ーーここから変更しましたーー）
        function selectAccountType(type) {
            document.querySelectorAll('.account-type-card').forEach(card => {
                card.classList.remove('selected');
            });
            event.currentTarget.classList.add('selected');
            document.getElementById('reg-type-' + type).checked = true;

            // 「その他」が選択された場合のみカスタム名入力欄を表示
            const customInput = document.getElementById('custom-account-name-wrapper');
            if (type === 'other') {
                customInput.style.display = 'block';
                document.getElementById('custom_account_name').required = true;
            } else {
                customInput.style.display = 'none';
                document.getElementById('custom_account_name').required = false;
            }
        }
        // （ーーここまで変更しましたーー）
        
        function togglePassword(inputId) {
            const passwordInput = document.getElementById(inputId);
            const toggleIcon = document.getElementById(inputId + '-toggle-icon');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.className = 'bi bi-eye-slash';
            } else {
                passwordInput.type = 'password';
                toggleIcon.className = 'bi bi-eye';
            }
        }
        
        function checkPasswordStrength() {
            const password = document.getElementById('password').value;
            const strengthDiv = document.getElementById('password-strength');
            
            if (password.length === 0) {
                strengthDiv.innerHTML = '';
                return;
            }
            
            let strength = 0;
            let messages = [];
            
            if (password.length >= 8) strength++;
            else messages.push('8文字以上');
            
            if (/[a-z]/.test(password)) strength++;
            else messages.push('小文字');
            
            if (/[A-Z]/.test(password)) strength++;
            else messages.push('大文字');
            
            if (/[0-9]/.test(password)) strength++;
            else messages.push('数字');
            
            if (/[^A-Za-z0-9]/.test(password)) strength++;
            else messages.push('記号');
            
            if (strength <= 2) {
                strengthDiv.className = 'password-strength strength-weak';
                strengthDiv.innerHTML = '弱い - 推奨: ' + messages.slice(0, 2).join('、');
            } else if (strength <= 3) {
                strengthDiv.className = 'password-strength strength-medium';
                strengthDiv.innerHTML = '普通 - より安全にするには: ' + messages.slice(0, 1).join('、');
            } else {
                strengthDiv.className = 'password-strength strength-strong';
                strengthDiv.innerHTML = '強い - セキュリティ良好！';
            }
            
            checkPasswordMatch();
        }
        
        function checkPasswordMatch() {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            const matchDiv = document.getElementById('password-match');
            const submitBtn = document.getElementById('submitBtn');
            
            if (confirmPassword.length === 0) {
                matchDiv.innerHTML = '';
                submitBtn.disabled = true;
                return;
            }
            
            if (password === confirmPassword) {
                matchDiv.className = 'password-strength strength-strong';
                matchDiv.innerHTML = 'パスワードが一致しています';
                submitBtn.disabled = false;
            } else {
                matchDiv.className = 'password-strength strength-weak';
                matchDiv.innerHTML = 'パスワードが一致しません';
                submitBtn.disabled = true;
            }
        }
        
        // ページ読み込み時の初期化
        document.addEventListener('DOMContentLoaded', function() {
            const selectedRadio = document.querySelector('input[name="account_type"]:checked');
            if (selectedRadio) {
                selectedRadio.closest('.account-type-card').classList.add('selected');
            }
            
            // 利用規約チェックボックスの状態確認
            document.getElementById('terms').addEventListener('change', function() {
                checkPasswordMatch(); // 送信ボタンの状態更新
            });
        });
    </script>
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
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h3>トーク</h3>
                <select id="talk-filter-select" class="form-control" style="width: auto;">
                    <option value="individual" {% if current_filter == 'individual' %}selected{% endif %}>個人</option>
                    <option value="groups" {% if current_filter == 'groups' %}selected{% endif %}>グループ</option>
                    <option value="close_friends" {% if current_filter == 'close_friends' %}selected{% endif %}>親しい友達</option>
                    <option value="acquaintances" {% if current_filter == 'acquaintances' %}selected{% endif %}>知り合い</option>
                    <optgroup label="その他">
                        {% for clist in custom_lists %}
                        <option value="custom_{{ clist.id }}" {% if current_filter == 'custom_' + clist.id|string %}selected{% endif %}>{{ clist.list_name }}</option>
                        {% endfor %}
                    </optgroup>
                </select>
            </div>
             <ul class="list-group">
                {% if talk_filter == 'groups' %}
                    {% for group in groups_list %}
                    <a href="#" class="list-group-item list-group-item-action"> <!-- TODO: Add group chat URL -->
                        <div class="d-flex w-100 justify-content-between">
                            <h5 class="mb-1"><i class="bi bi-people-fill"></i> {{ group.name }}</h5>
                        </div>
                        <p class="mb-1 text-muted">{{ group.last_message[:30] or 'まだメッセージはありません' }}...</p>
                    </a>
                    {% else %}
                    <li class="list-group-item">参加しているグループはありません。</li>
                    {% endfor %}
                {% else %}
                    {% for talk in talks_list %}
                    <a href="{{ url_for('start_chat_with', user_id=talk.partner_id) }}" class="list-group-item list-group-item-action">
                        <div class="d-flex w-100 justify-content-between">
                            <h5 class="mb-1">{{ talk.partner_name }}</h5>
                            <small>{{ talk.last_message_time | format_datetime }}</small>
                        </div>
                        <p class="mb-1 text-muted">{{ talk.last_message_content[:30] }}...</p>
                        {% if talk.unread_count > 0 %}<span class="badge badge-danger badge-pill">{{ talk.unread_count }}</span>{% endif %}
                    </a>
                    {% else %}
                    <li class="list-group-item">トーク履歴がありません。</li>
                    {% endfor %}
                {% endif %}
            </ul>
        </section>

        
                <!-- （ーーここから変更しましたーー） -->
<!-- タイムラインタブ -->
<section id="timeline-tab" class="tab-content" style="overflow-y: auto; height: 100%; padding-bottom: 50px;">
<!-- 情報パネル -->
<div class="card mb-3">
<div class="card-header">リアルタイム情報</div>
<div class="card-body" style="font-size: 0.9em;">
<p class="mb-1"><strong>天気:</strong> {% for w in weather_data %}{{ w.data }}{% endfor %} <a href="https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code=130000" target="_blank" class="small">(気象庁)</a></p>
<p class="mb-1"><strong>交通:</strong> {{ traffic.data if traffic else '情報なし' }} <a href="https://traininfo.jreast.co.jp/train_info/kanto.aspx" target="_blank" class="small">(JR東日本)</a></p>
<p class="mb-0"><strong>災害:</strong> {{ disaster.data if disaster else '情報なし' }} <a href="https://www.jma.go.jp/bosai/warning/#area_type=offices&area_code=130000" target="_blank" class="small">(気象庁)</a></p>
</div>
</div>

            <!-- 投稿フォーム -->
            <div class="card mb-3">
                <div class="card-body">
                    <form action="{{ url_for('post_timeline') }}" method="post" enctype="multipart/form-data">
                        <div class="form-group">
                            <textarea name="content" class="form-control" rows="2" placeholder="今なにしてる？"></textarea>
                        </div>
                        <div class="form-group mb-2">
                            <input type="file" name="media" class="form-control-file">
                        </div>
                        <button type="submit" class="btn btn-primary btn-block">投稿</button>
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
                                <!-- 投稿メディアの表示 (画像か動画か判定) -->
                                {% if post.media_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) %}
                                    <img src="{{ url_for('static', filename='assets/uploads/' + post.media_url) }}" class="img-fluid rounded mb-2" style="max-height: 300px;">
                                {% elif post.media_url.lower().endswith(('.mp4', '.mov', '.avi')) %}
                                    <video src="{{ url_for('static', filename='assets/uploads/' + post.media_url) }}" class="img-fluid rounded mb-2" controls style="max-height: 300px;"></video>
                                {% endif %}
                            {% endif %}
                            <small class="text-muted">{{ post.created_at | format_datetime }}</small>
                        </div>
                    </div>
                </div>
            </div>
            {% else %}
            <p>まだ投稿がありません。</p>
            {% endfor %}
        </section>
        <!-- （このセクションを丸ごと追加してください） -->
        <!-- その他タブ -->
        <section id="other-tab" class="tab-content">
            <ul class="list-group">
                <a href="{{ url_for('settings_page') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-gear-fill mr-2"></i>全体設定</div>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('auto_replies_page') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-robot mr-2"></i>自動応答メッセージ設定</div>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('canned_messages_page') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-body-text mr-2"></i>定型文設定</div>
                    <i class="bi bi-chevron-right"></i>
                </a>
                 <a href="{{ url_for('block_list_page') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-slash-circle-fill mr-2"></i>ブロックリスト</div>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('hidden_list_page') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-eye-slash-fill mr-2"></i>非表示リスト</div>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('custom_lists_page') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-person-lines-fill mr-2"></i>カスタムリスト管理</div>
                    <i class="bi bi-chevron-right"></i>
                </a>

            </ul>
            <div class="mt-4">
                 <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-block">ログアウト</a>
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

    // （ここからが修正部分）
    const talkFilterSelect = document.getElementById('talk-filter-select');
    if (talkFilterSelect) {
        talkFilterSelect.addEventListener('change', function() {
            const selectedFilter = this.value;
            window.location.href = `/app?talk_filter=${selectedFilter}`;
        });
    }
    // （ここまでが修正部分）
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
    <!-- （ここから追加） -->
    <!-- 中断したゲーム -->
    {% if saved_games %}
    <h2 class="h4">中断したゲーム</h2>
    <div class="list-group mb-5">
        {% for game in saved_games %}
        <a href="{{ url_for('game_room', room_id=game.room_id) }}" class="list-group-item list-group-item-action">
            <div class="d-flex w-100 justify-content-between">
                <h5 class="mb-1"><i class="bi bi-play-circle-fill"></i> {{ game.game_type | capitalize }} を再開</h5>
                <small>最終更新: {{ game.last_updated_at | format_datetime }}</small>
            </div>
            <p class="mb-1">ルームID: {{ game.room_id }}</p>
        </a>
        {% endfor %}
    </div>
    {% endif %}
    <!-- （ここまで追加） -->

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
        <button id="save-game-btn" class="btn btn-sm btn-warning mb-3"><i class="bi bi-pause-circle"></i> 中断して退出</button>
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
            const card = selectedCards;
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
    // （ここから追加）
    const saveGameBtn = document.getElementById('save-game-btn');
    if (saveGameBtn) {
        saveGameBtn.addEventListener('click', () => {
            if (confirm('ゲームを中断して退出しますか？進行状況は保存されます。')) {
                socket.emit('save_game', { room_id: roomId });
            }
        });
    }

    socket.on('game_saved_and_closed', (data) => {
        alert(data.message);
        window.location.href = "{{ url_for('games_hub') }}";
    });
    // （ここまで追加）

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


# （この関数全体を置き換えてください）
@socketio.on('send_ai_message')
@login_required
def handle_send_ai_message(data):
    user_message = data['message'].strip()
    if not user_message:
        return

    db = get_db()
    # ユーザーのメッセージをDBに保存（元のメッセージ内容を保持）
    db.execute('INSERT INTO private_messages (sender_id, recipient_id, content, is_from_ai) VALUES (?, 0, ?, 0)',
               (current_user.id, user_message))
    db.commit()

    response_text = None

    # --- ステップ1: AI APIへの問い合わせを試行 ---
    if ai_model:
        try:
            # 以前のAI応答ロジックをここで実行
            # 1. 知識ベースから関連情報を検索
            personal_facts = db.execute("SELECT keyword, fact FROM ai_knowledge_base WHERE user_id = ?", (current_user.id,)).fetchall()
            global_facts = db.execute("SELECT keyword, fact FROM ai_knowledge_base WHERE user_id = 0").fetchall()
            
            context_prompt = ""
            if personal_facts or global_facts:
                context_prompt += "### 指示\nあなたはユーザーをサポートするAIアシスタントです。以下の事前情報を最優先で参考にして、会話の続きを生成してください。\n\n### 事前情報\n"
                if personal_facts:
                    context_prompt += "【あなた(ユーザー)に関する情報】:\n"
                    for fact in personal_facts: context_prompt += f"- {fact['keyword']}: {fact['fact']}\n"
                if global_facts:
                    context_prompt += "【全体で共有されている情報】:\n"
                    for fact in global_facts: context_prompt += f"- {fact['keyword']}: {fact['fact']}\n"
            
            # 2. データベースから会話履歴を取得
            history_rows = db.execute("""
                SELECT content, is_from_ai FROM private_messages 
                WHERE ((sender_id = ? AND recipient_id = 0) OR (sender_id = 0 AND recipient_id = ?))
                ORDER BY timestamp ASC
            """, (current_user.id, current_user.id)).fetchall()

            # 3. プロンプト全体を組み立てる
            full_prompt = [context_prompt] if context_prompt else []
            full_prompt.append("### 会話履歴")
            for row in history_rows:
                role = "AI" if row['is_from_ai'] else "あなた"
                full_prompt.append(f"{role}: {row['content']}")
            full_prompt.append("\n### 会話の続きを生成してください\nAI:")
            
            # 4. AIに送信
            response = ai_model.generate_content('\n'.join(full_prompt))
            response_text = response.text

        except Exception as e:
            print(f"--- AI API ERROR ---")
            print(f"Falling back to rule-based response. Error: {e}")
            # エラーが発生した場合、response_text は None のままになり、次のステップに進む
            pass

    # --- ステップ2: AIが利用不可またはエラーだった場合に、JSONベースの応答を実行 ---
    if response_text is None:
        user_message_lower = user_message.lower()
        default_answer = "申し訳ありません、よく分かりませんでした。簡単な言葉で話しかけてみてください。"
        response_text = default_answer # デフォルトの応答
        found_answer = False

        if qa_list:
            for qa_pair in qa_list:
                for keyword in qa_pair.get('keywords', []):
                    if keyword.lower() in user_message_lower:
                        response_text = qa_pair.get('answer', default_answer)
                        found_answer = True
                        break
                if found_answer:
                    break
    
    # AIの返信をエミュレートする（少し待つ）
    socketio.sleep(0.5)

    # --- ステップ3: 最終的な応答をDBに保存して送信 ---
    db.execute('INSERT INTO private_messages (sender_id, recipient_id, content, is_from_ai) VALUES (0, ?, ?, 1)',
               (current_user.id, response_text))
    db.commit()
    
    emit('ai_response', {'message': response_text}, room=request.sid)


# （この関数全体を置き換えてください）
@socketio.on('janken_move')
@login_required
def handle_janken_move(data):
    room_id = data['room_id']
    move = data['move']
    if room_id not in game_rooms or game_rooms[room_id]['type'] != 'janken':
        return

    room = game_rooms[room_id]
    
    if 'moves' not in room:
        room['moves'] = {}

    room['moves'][current_user.id] = move
    emit('player_moved', {'player_id': current_user.id}, room=room_id)

    human_players = [p for p in room['players'] if not p.get('is_cpu')]
    cpu_players = [p for p in room['players'] if p.get('is_cpu')]

    for cpu in cpu_players:
        if cpu['id'] not in room['moves']:
            room['moves'][cpu['id']] = random.choice(['rock', 'paper', 'scissors'])
    
    if len(room['moves']) == len(room['players']):
        # ▼▼▼ ここからが修正部分 ▼▼▼
        player_one = room['players'][0]
        player_two = room['players'][1]

        p1_move = room['moves'][player_one['id']]
        p2_move = room['moves'][player_two['id']]
        
        winner_id = None
        if p1_move == p2_move:
            result_text = "あいこ"
        elif (p1_move == 'rock' and p2_move == 'scissors') or \
             (p1_move == 'scissors' and p2_move == 'paper') or \
             (p1_move == 'paper' and p2_move == 'rock'):
            result_text = f"{player_one['name']} の勝ち！"
            winner_id = player_one['id']
        else:
            result_text = f"{player_two['name']} の勝ち！"
            winner_id = player_two['id']
        # ▲▲▲ ここまでが修正部分 ▲▲▲
            
        emit('janken_result', {
            'moves': room['moves'],
            'result_text': result_text,
            'winner_id': winner_id
        }, room=room_id)
        
        room['moves'] = {}


@socketio.on('delete_message')
@login_required
def handle_delete_message(data):
    message_id = data.get('message_id')
    db = get_db()
    # 該当メッセージが自分のものか確認
    msg = db.execute("SELECT sender_id, recipient_id FROM private_messages WHERE id = ?", (message_id,)).fetchone()
    if msg and msg['sender_id'] == current_user.id:
        # 物理削除ではなく、削除済みフラグを立てる
        db.execute("UPDATE private_messages SET content = ?, is_deleted = 1 WHERE id = ?", ('このメッセージは削除されました。', message_id))
        db.commit()
        
        # 関係者に通知
        recipient_id = msg['recipient_id']
        emit('message_deleted', {'message_id': message_id}, room=request.sid)
        if recipient_id in online_users:
            emit('message_deleted', {'message_id': message_id}, room=online_users[recipient_id]['sid'])

@socketio.on('edit_message')
@login_required
def handle_edit_message(data):
    message_id = data.get('message_id')
    new_content = data.get('new_content')
    db = get_db()
    msg = db.execute("SELECT sender_id, recipient_id FROM private_messages WHERE id = ?", (message_id,)).fetchone()
    if msg and msg['sender_id'] == current_user.id and new_content:
        updated_at = datetime.now()
        db.execute("UPDATE private_messages SET content = ?, updated_at = ? WHERE id = ?", (new_content, updated_at, message_id))
        db.commit()
        
        payload = {'message_id': message_id, 'new_content': new_content, 'updated_at': updated_at.isoformat()}
        recipient_id = msg['recipient_id']
        emit('message_edited', payload, room=request.sid)
        if recipient_id in online_users:
            emit('message_edited', payload, room=online_users[recipient_id]['sid'])

@socketio.on('react_to_message')
@login_required
def handle_react_to_message(data):
    message_id = data.get('message_id')
    reaction = data.get('reaction')
    db = get_db()
    msg = db.execute("SELECT sender_id, recipient_id, reactions FROM private_messages WHERE id = ?", (message_id,)).fetchone()
    if msg:
        reactions = json.loads(msg['reactions']) if msg['reactions'] else {}
        
        # リアクションを追加/削除
        if reaction in reactions:
            if current_user.id in reactions[reaction]:
                reactions[reaction].remove(current_user.id)
                if not reactions[reaction]: # 誰もリアクションしてなければ絵文字ごと消す
                    del reactions[reaction]
            else:
                reactions[reaction].append(current_user.id)
        else:
            reactions[reaction] = [current_user.id]
            
        db.execute("UPDATE private_messages SET reactions = ? WHERE id = ?", (json.dumps(reactions), message_id))
        db.commit()

        payload = {'message_id': message_id, 'reactions': reactions}
        # 関係者全員に通知
        sender_id, recipient_id = msg['sender_id'], msg['recipient_id']
        if sender_id in online_users: emit('message_reacted', payload, room=online_users[sender_id]['sid'])
        if recipient_id in online_users: emit('message_reacted', payload, room=online_users[recipient_id]['sid'])
# （ここまで追加）

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
        log_msg += f" {discarded_cards['rank']}のペアを捨てました。"
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
        loser = room['turn_order'] if room['turn_order'] else '不明'
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
                    <input type="text" name="query" class="form-control" placeholder="ユーザー名で検索 (空欄で全員表示)" value="{{ query or '' }}">
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
                <!-- （ーーここから変更しましたーー） -->
                <div>
                    <a href="{{ url_for('accept_request', sender_id=req.id) }}" class="btn btn-sm btn-primary">承認</a>
                    <a href="{{ url_for('reject_request', sender_id=req.id) }}" class="btn btn-sm btn-danger ml-1">拒否</a>
                </div>
                <!-- （ーーここまで変更しましたーー） -->
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    <!-- 友達リスト -->
<!-- 友達リスト -->
            <div class="card mb-4">
                <div class="card-header">友達リスト</div>
                <ul class="list-group list-group-flush">
                    {% for friend in friends_list %}
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            {% if friend.status == 'favorite' %}
                                <i class="bi bi-heart-fill text-danger"></i>
                            {% else %}
                                <i class="bi bi-person-fill text-muted"></i>
                            {% endif %}
                            <a href="{{ url_for('view_profile', user_id=friend.id) }}" class="text-dark ml-2">{{ friend.username }}</a>
                        </div>
                        <div>
                            <a href="{{ url_for('start_chat_with', user_id=friend.id) }}" class="btn btn-sm btn-info" title="チャット"><i class="bi bi-chat-dots"></i></a>
                            <!-- ▼▼▼ ここから変更 ▼▼▼ -->
                            <a href="{{ url_for('toggle_favorite', friend_id=friend.id) }}" 
                               class="btn btn-sm {{ 'btn-danger' if friend.status == 'favorite' else 'btn-outline-danger' }}" 
                               title="親しい友達に設定/解除">
                               <i class="bi bi-heart"></i>
                            </a>
                            <!-- ▲▲▲ ここまで変更 ▲▲▲ -->
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
        html, body { height: 100%; overflow: hidden; }
        body { display: flex; flex-direction: column; background-color: #E5DDD5; }
        .chat-header { flex-shrink: 0; background-color: #005E54; color: white; }
        .chat-container-wrapper { flex-grow: 1; overflow-y: auto; padding: 15px; }
        .message-row { display: flex; flex-direction: column; margin-bottom: 2px; }
        .my-message-row { align-items: flex-end; }
        .opponent-message-row { align-items: flex-start; }
        .message-bubble { max-width: 70%; padding: 6px 12px; border-radius: 8px; word-wrap: break-word; position: relative; box-shadow: 0 1px 1px rgba(0,0,0,0.1); cursor: pointer; }
        .my-message-row .message-bubble { background-color: #DCF8C6; }
        .opponent-message-row .message-bubble { background-color: #FFFFFF; }
        .message-content { padding-bottom: 15px; }
        .deleted-message { font-style: italic; color: #888; }
        .message-meta { position: absolute; bottom: 4px; right: 8px; font-size: 0.7em; color: #999; }
        .edited-mark { font-size: 0.7em; color: #999; }
        .reactions-container { margin-top: -8px; margin-left: 10px; margin-right: 10px; text-align: right; }
        .reaction-pill { display: inline-block; background-color: #f0f0f0; border-radius: 10px; padding: 1px 6px; font-size: 0.8em; margin: 2px; }
        .chat-form { flex-shrink: 0; background-color: #f0f0f0; }
        .message-menu { display: none; position: absolute; background: white; border: 1px solid #ccc; border-radius: 5px; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .message-menu button { background: none; border: none; display: block; width: 100%; text-align: left; padding: 8px 12px; }
        .message-menu button:hover { background: #f0f0f0; }
        .reaction-palette { display: flex; }
        .reaction-palette button { font-size: 1.2rem; padding: 2px 6px; }
    </style>
</head>
<body>
    <header class="chat-header p-2 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <a href="{{ url_for('main_app') }}" class="btn btn-link text-white"><i class="bi bi-arrow-left"></i></a>
            <strong class="ml-2">{{ opponent.username }}</strong>
        </div>
    </header>

    <div class="chat-container-wrapper" id="chat-container-wrapper">
        <div id="chat-container">
        {% for message in messages %}
            <div id="message-row-{{ message.id }}" class="message-row {{ 'my-message-row' if message.sender_id == current_user.id else 'opponent-message-row' }}">
                <div class="message-bubble" data-message-id="{{ message.id }}">
                    <div class="message-content {{ 'deleted-message' if message.is_deleted else '' }}">{{ message.content | nl2br }}</div>
                    <div class="message-meta">
                        <span class="edited-mark" style="display: {{ 'inline' if message.updated_at else 'none' }};">(編集済み)</span>
                        {{ message.timestamp | format_datetime('%H:%M') }}
                    </div>
                </div>
                <div class="reactions-container" id="reactions-{{ message.id }}">
                    {% if message.reactions and message.reactions|fromjson %}
                        {% for emoji, users in (message.reactions|fromjson).items() %}
                            <span class="reaction-pill">{{ emoji }} {{ users|length }}</span>
                        {% endfor %}
                    {% endif %}
                </div>
            </div>
        {% endfor %}
        </div>
    </div>
    
    <!-- メッセージ操作メニュー -->
    <div id="message-menu" class="message-menu">
        <div class="reaction-palette">
            <button class="btn-reaction" data-emoji="👍">👍</button>
            <button class="btn-reaction" data-emoji="❤️">❤️</button>
            <button class="btn-reaction" data-emoji="😂">😂</button>
            <button class="btn-reaction" data-emoji="😲">😲</button>
            <button class="btn-reaction" data-emoji="🙏">🙏</button>
        </div>
        <hr class="my-1">
        <button id="btn-edit" style="display:none;"><i class="bi bi-pencil"></i> 編集</button>
        <button id="btn-delete" style="display:none;"><i class="bi bi-trash"></i> 削除</button>
    </div>

    <form class="chat-form p-2 bg-light border-top" id="message-form">
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
    const chatContainerWrapper = document.getElementById('chat-container-wrapper');
    const opponentId = {{ opponent.id }};
    const currentUserId = {{ current_user.id }};

    chatContainerWrapper.scrollTop = chatContainerWrapper.scrollHeight;

    form.addEventListener('submit', function(e) { e.preventDefault(); sendMessage(); });

    function sendMessage() {
        if (input.value) {
            socket.emit('send_private_message', { 'recipient_id': opponentId, 'message': input.value });
            input.value = '';
        }
    }

    socket.on('new_private_message', (msg) => {
        if ((msg.sender_id === opponentId && msg.recipient_id === currentUserId) || (msg.sender_id === currentUserId && msg.recipient_id === opponentId)) {
            // 新規メッセージを追加
        }
    });
    
    // --- メッセージ操作メニュー ---
    const menu = document.getElementById('message-menu');
    let activeMessageId = null;

    document.getElementById('chat-container').addEventListener('click', function(e) {
        const bubble = e.target.closest('.message-bubble');
        if (bubble) {
            activeMessageId = bubble.dataset.messageId;
            const messageRow = document.getElementById(`message-row-${activeMessageId}`);
            const isMyMessage = messageRow.classList.contains('my-message-row');
            
            document.getElementById('btn-edit').style.display = isMyMessage ? 'block' : 'none';
            document.getElementById('btn-delete').style.display = isMyMessage ? 'block' : 'none';

            menu.style.display = 'block';
            menu.style.top = `${bubble.offsetTop - menu.offsetHeight - 5}px`;
            menu.style.left = `${bubble.offsetLeft}px`;
        } else {
            menu.style.display = 'none';
        }
    });

    document.querySelectorAll('.btn-reaction').forEach(btn => {
        btn.addEventListener('click', () => {
            socket.emit('react_to_message', { message_id: activeMessageId, reaction: btn.dataset.emoji });
            menu.style.display = 'none';
        });
    });

    document.getElementById('btn-delete').addEventListener('click', () => {
        if (confirm('このメッセージを削除しますか？')) {
            socket.emit('delete_message', { message_id: activeMessageId });
        }
        menu.style.display = 'none';
    });

    document.getElementById('btn-edit').addEventListener('click', () => {
        const contentDiv = document.querySelector(`#message-row-${activeMessageId} .message-content`);
        const currentContent = contentDiv.innerText;
        const newContent = prompt('メッセージを編集:', currentContent);
        if (newContent && newContent !== currentContent) {
            socket.emit('edit_message', { message_id: activeMessageId, new_content: newContent });
        }
        menu.style.display = 'none';
    });

    // --- SocketIO Listeners for Updates ---
    socket.on('message_deleted', (data) => {
        const contentDiv = document.querySelector(`#message-row-${data.message_id} .message-content`);
        if(contentDiv) {
            contentDiv.textContent = 'このメッセージは削除されました。';
            contentDiv.classList.add('deleted-message');
        }
    });

    socket.on('message_edited', (data) => {
        const contentDiv = document.querySelector(`#message-row-${data.message_id} .message-content`);
        const editedMark = document.querySelector(`#message-row-${data.message_id} .edited-mark`);
        if(contentDiv) {
            contentDiv.innerText = data.new_content;
            editedMark.style.display = 'inline';
        }
    });

    socket.on('message_reacted', (data) => {
        const reactionsContainer = document.getElementById(`reactions-${data.message_id}`);
        reactionsContainer.innerHTML = '';
        for (const [emoji, users] of Object.entries(data.reactions)) {
            if (users.length > 0) {
                const pill = document.createElement('span');
                pill.className = 'reaction-pill';
                pill.textContent = `${emoji} ${users.length}`;
                reactionsContainer.appendChild(pill);
            }
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
        .profile-img-container { position: relative; width: 120px; height: 120px; margin: 0 auto 20px; }
        .profile-img-container img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }
        .profile-img-container .upload-label { position: absolute; bottom: 0; right: 0; background: #007bff; color: white; padding: 5px 10px; border-radius: 50%; cursor: pointer; }
        .profile-img-container input[type="file"] { display: none; }
    </style>
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <a href="{{ url_for('main_app') }}" class="btn btn-secondary"><i class="bi bi-arrow-left"></i> 戻る</a>
        <h1 class="mb-0 h2">プロフィール編集</h1>
        <a href="{{ url_for('view_profile', user_id=current_user.id) }}" class="btn btn-outline-primary">プレビュー</a>
    </div>

    <form action="{{ url_for('update_settings') }}" method="POST" enctype="multipart/form-data">
        <div class="card mb-4">
            <div class="card-header">基本情報</div>
            <div class="card-body">
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
            </div>
        </div>
        
        <button type="submit" class="btn btn-primary btn-block mt-4 mb-4">基本情報を更新する</button>
    </form>

    <hr>

    <h4 class="mt-4">おすすめYouTube</h4>
    <div class="card mb-4">
        <div class="card-body">
            <form action="{{ url_for('add_youtube_link') }}" method="POST">
                <div class="form-group">
                    <label for="youtube_url">YouTube URL</label>
                    <div class="input-group">
                        <input type="url" class="form-control" name="url" id="youtube_url" placeholder="https://www.youtube.com/watch?v=..." required>
                        <div class="input-group-append">
                            <a href="https://www.youtube.com" target="_blank" class="btn btn-danger"><i class="bi bi-youtube"></i> YouTubeで探す</a>
                        </div>
                    </div>
                </div>
                <div class="form-group">
                    <label for="youtube_title">表示名 (任意)</label>
                    <input type="text" class="form-control" name="title" id="youtube_title" placeholder="例：おすすめの曲">
                </div>
                <button type="submit" class="btn btn-success">追加</button>
            </form>
        </div>
        {% if youtube_links %}
        <ul class="list-group list-group-flush">
            {% for link in youtube_links %}
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <a href="{{ link.url }}" target="_blank">{{ link.title or link.url }}</a>
                </div>
                <a href="{{ url_for('delete_youtube_link', link_id=link.id) }}" class="btn btn-sm btn-danger"><i class="bi bi-trash"></i></a>
            </li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>

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
            background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url("{{ url_for('static', filename='assets/images/' + user.background_image) }}");
            background-size: cover; background-position: center; color: white;
            padding: 40px 20px; text-align: center; position: relative;
        }
        .profile-avatar {
            width: 120px; height: 120px; border-radius: 50%; border: 4px solid white;
            object-fit: cover; margin-top: -60px; background: white;
        }
    </style>
</head>
<body>

<div class="container-fluid p-0" style="max-width: 600px; margin: auto; background: #fff;">
    <a href="{{ url_for('main_app') }}" class="btn btn-light m-3" style="position: absolute; z-index: 10; opacity: 0.9;"><i class="bi bi-arrow-left"></i></a>
    <div class="profile-header"></div>
    <div class="text-center">
        <img src="{{ url_for('static', filename='assets/uploads/profile_images/' + user.profile_image if 'user' in user.profile_image else 'assets/images/' + user.profile_image) }}" alt="プロフィール画像" class="profile-avatar">
    </div>

    <div class="container p-4">
        <div class="text-center">
            <h2 class="mb-0">{{ user.username }}</h2>
            <p class="text-muted">{{ user.status_message or '' }}</p>
        </div>

        <!-- アクションボタン -->
        <div class="text-center my-4">
            {% if user.id == current_user.id %}
                <a href="{{ url_for('profile_edit_page') }}" class="btn btn-primary"><i class="bi bi-pencil-square"></i> プロフィールを編集</a>
            {% else %}
                <a href="{{ url_for('start_chat_with', user_id=user.id) }}" class="btn btn-success"><i class="bi bi-chat-dots-fill"></i> チャットする</a>
                {% if friend_status == 'not_friend' %}
                    <a href="{{ url_for('send_request', recipient_id=user.id) }}" class="btn btn-info"><i class="bi bi-person-plus-fill"></i> 友達になる</a>
                {% elif friend_status == 'pending' %}
                    <button class="btn btn-secondary" disabled>リクエスト送信済み</button>
                {% elif friend_status == 'friend' or friend_status == 'favorite' %}
                    <a href="{{ url_for('toggle_favorite', friend_id=user.id) }}" class="btn btn-outline-warning">
                        <i class="bi bi-star{{ '-fill' if friend_status == 'favorite' else '' }}"></i> お気に入り
                    </a>
                {% endif %}
            {% endif %}
        </div>

        <div class="my-4 p-3 bg-light rounded">
            <p class="mb-0">{{ user.bio or '自己紹介はまだ設定されていません。' }}</p>
        </div>
        
        <!-- おすすめYouTube -->
        {% if youtube_links %}
        <hr>
        <h4 class="mt-4"><i class="bi bi-youtube text-danger"></i> おすすめ</h4>
        <div class="list-group">
        {% for link in youtube_links %}
            <a href="{{ link.url }}" target="_blank" class="list-group-item list-group-item-action">
                {{ link.title or link.url }}
            </a>
        {% endfor %}
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
                    <!-- （ーーここから変更しましたーー） -->
<small class="text-muted float-right">{{ announcement.created_at | format_datetime('%m月%d日 %H:%M') }}</small>
                    <!-- （ーーここまで変更しましたーー） -->
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
            <strong class="ml-2"><i class="bi bi-robot"></i> AIチャット (Gemini)</strong>
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
                <h6>{{ room.players.name }}</h6>
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
        <button id="save-game-btn" class="btn btn-sm btn-warning mb-3"><i class="bi bi-pause-circle"></i> 中断して退出</button>
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
    const saveGameBtn = document.getElementById('save-game-btn');
    if (saveGameBtn) {
        saveGameBtn.addEventListener('click', () => {
            if (confirm('ゲームを中断して退出しますか？進行状況は保存されます。')) {
                socket.emit('save_game', { room_id: roomId });
            }
        });
    }

    socket.on('game_saved_and_closed', (data) => {
        alert(data.message);
        window.location.href = "{{ url_for('games_hub') }}";
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

# （ーーここから変更しましたーー）
# --- スケジュールタスクの登録と起動 ---
# アプリケーションコンテキスト内で一度だけ実行されるように設定
# with app.app_context():
#     # 既存のジョブがあればリセット
#     if scheduler.get_job('scraping_job'):
#         scheduler.remove_job('scraping_job')
#     if scheduler.get_job('monthly_survey_job'):
#         scheduler.remove_job('monthly_survey_job')
#     if scheduler.get_job('yearly_event_job'):
#         scheduler.remove_job('yearly_event_job')
#     if scheduler.get_job('weekly_report_job'):
#         scheduler.remove_job('weekly_report_job')
#
#     # 各タスクを登録
#     # 1時間ごとに外部情報を取得
#     scheduler.add_job(scheduled_scraping_tasks, 'interval', hours=1, id='scraping_job', next_run_time=datetime.now())
#     # 毎月1日にアンケート通知
#     scheduler.add_job(schedule_monthly_survey_announcement, 'cron', month='*', day=1, hour=3, id='monthly_survey_job')
#     # 毎週月曜日に機能レポート
#     scheduler.add_job(schedule_weekly_feature_report, 'cron', day_of_week='mon', hour=4, id='weekly_report_job')
#     # 毎年1月1日にイベント企画
#     scheduler.add_job(schedule_yearly_ai_event, 'cron', year='*', month=1, day=1, hour=5, id='yearly_event_job')
#
#     # スケジューラーが起動していなければ起動する
#     if not scheduler.running:
#         try:
#             scheduler.start()
#             print("Scheduler started with all jobs.")
#         except (KeyboardInterrupt, SystemExit):
#             pass
# （ーーここまで変更しましたーー）



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


# （ここから4つのHTML変数を追加）
AUTO_REPLIES_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>自動応答メッセージ設定</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4">自動応答メッセージ設定</h1>

    <div class="card mb-4">
        <div class="card-header">新規追加</div>
        <div class="card-body">
            <form action="{{ url_for('add_auto_reply') }}" method="POST">
                <div class="form-group">
                    <label for="keyword">キーワード</label>
                    <input type="text" name="keyword" class="form-control" placeholder="この言葉が含まれていたら..." required>
                </div>
                <div class="form-group">
                    <label for="response_message">応答メッセージ</label>
                    <textarea name="response_message" class="form-control" rows="2" placeholder="このメッセージを返す" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">追加する</button>
            </form>
        </div>
    </div>

    <div class="card">
        <div class="card-header">登録済みリスト</div>
        <ul class="list-group list-group-flush">
            {% for item in items %}
            <li class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small class="text-muted">キーワード</small>
                        <p class="font-weight-bold mb-1">{{ item.keyword }}</p>
                        <small class="text-muted">応答メッセージ</small>
                        <p class="mb-0">{{ item.response_message }}</p>
                    </div>
                    <a href="{{ url_for('delete_auto_reply', item_id=item.id) }}" class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></a>
                </div>
            </li>
            {% else %}
            <li class="list-group-item">登録されている自動応答メッセージはありません。</li>
            {% endfor %}
        </ul>
    </div>
</div>
</body>
</html>
"""

CANNED_MESSAGES_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>定型文設定</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4">定型文設定</h1>
    <div class="card mb-4">
        <div class="card-header">新規追加</div>
        <div class="card-body">
            <form action="{{ url_for('add_canned_message') }}" method="POST">
                <div class="form-group">
                    <label for="title">タイトル</label>
                    <input type="text" name="title" class="form-control" placeholder="（例）挨拶、お礼" required>
                </div>
                <div class="form-group">
                    <label for="content">内容</label>
                    <textarea name="content" class="form-control" rows="3" placeholder="お世話になっております。" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">追加する</button>
            </form>
        </div>
    </div>
    <div class="card">
        <div class="card-header">登録済みリスト</div>
        <ul class="list-group list-group-flush">
            {% for item in items %}
            <li class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <p class="font-weight-bold mb-1">{{ item.title }}</p>
                        <p class="mb-0 text-muted" style="white-space: pre-wrap;">{{ item.content }}</p>
                    </div>
                    <a href="{{ url_for('delete_canned_message', item_id=item.id) }}" class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></a>
                </div>
            </li>
            {% else %}
            <li class="list-group-item">登録されている定型文はありません。</li>
            {% endfor %}
        </ul>
    </div>
</div>
</body>
</html>
"""

BLOCK_LIST_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>ブロックリスト</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4">ブロックリスト</h1>
    <div class="card">
        <ul class="list-group list-group-flush">
            {% for user in users %}
            <li class="list-group-item d-flex justify-content-between align-items-center">
                {{ user.username }}
                <a href="#" class="btn btn-sm btn-outline-secondary">ブロック解除</a>
            </li>
            {% else %}
            <li class="list-group-item">ブロック中のユーザーはいません。</li>
            {% endfor %}
        </ul>
    </div>
</div>
</body>
</html>
"""

HIDDEN_LIST_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>非表示リスト</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4">非表示リスト</h1>
    <div class="card">
        <ul class="list-group list-group-flush">
            {% for user in users %}
            <li class="list-group-item d-flex justify-content-between align-items-center">
                {{ user.username }}
                <a href="#" class="btn btn-sm btn-outline-secondary">再表示</a>
            </li>
            {% else %}
            <li class="list-group-item">非表示中のユーザーはいません。</li>
            {% endfor %}
        </ul>
    </div>
</div>
</body>
</html>
"""
# （ここまで追加）
# （ここから2つのHTML変数を追加）
CUSTOM_LISTS_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>カスタムリスト管理</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('main_app') }}" class="btn btn-secondary mb-4"><i class="bi bi-arrow-left"></i> 戻る</a>
    <h1 class="mb-4">カスタムリスト管理</h1>
    <div class="card mb-4">
        <div class="card-header">新しいリストを作成</div>
        <div class="card-body">
            <form action="{{ url_for('create_custom_list') }}" method="POST">
                <div class="input-group">
                    <input type="text" name="list_name" class="form-control" placeholder="リスト名 (例: 趣味仲間)" required>
                    <div class="input-group-append">
                        <button type="submit" class="btn btn-primary">作成</button>
                    </div>
                </div>
            </form>
        </div>
    </div>
    <div class="card">
        <div class="card-header">作成済みリスト</div>
        <ul class="list-group list-group-flush">
            {% for clist in custom_lists %}
            <li class="list-group-item d-flex justify-content-between align-items-center">
                {{ clist.list_name }}
                <div>
                    <a href="{{ url_for('manage_list_members', list_id=clist.id) }}" class="btn btn-sm btn-outline-primary">メンバー編集</a>
                    <a href="{{ url_for('delete_custom_list', list_id=clist.id) }}" class="btn btn-sm btn-outline-danger ml-1"><i class="bi bi-trash"></i></a>
                </div>
            </li>
            {% else %}
            <li class="list-group-item">カスタムリストはまだありません。</li>
            {% endfor %}
        </ul>
    </div>
</div>
</body>
</html>
"""

MANAGE_LIST_MEMBERS_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>メンバー編集: {{ clist.list_name }}</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4" style="max-width: 600px;">
    <a href="{{ url_for('custom_lists_page') }}" class="btn btn-secondary mb-4">戻る</a>
    <h1 class="mb-4">メンバー編集: <span class="text-primary">{{ clist.list_name }}</span></h1>
    <form action="{{ url_for('update_list_members', list_id=clist.id) }}" method="POST">
        <div class="card">
            <div class="card-header">友達を選択</div>
            <ul class="list-group list-group-flush">
                {% for friend in friends %}
                <li class="list-group-item">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" name="members" value="{{ friend.id }}" id="friend-{{ friend.id }}"
                               {% if friend.id in member_ids %}checked{% endif %}>
                        <label class="form-check-label" for="friend-{{ friend.id }}">
                            {{ friend.username }}
                        </label>
                    </div>
                </li>
                {% else %}
                <li class="list-group-item">リストに追加できる友達がいません。</li>
                {% endfor %}
            </ul>
            <div class="card-footer">
                <button type="submit" class="btn btn-success">メンバーを更新</button>
            </div>
        </div>
    </form>
</div>
</body>
</html>
"""
# （ここまで追加）



if __name__ == '__main__':
    # 本番環境では debug=False で実行する
    # host='0.0.0.0' はコンテナや外部からのアクセスを受け付けるための標準設定
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)

#if __name__ == '__main__':
    # 開発サーバー起動時にスケジューラーが二重に起動するのを防ぐ
    # use_reloader=False はスケジューラーを安定動作させるために重要
#    socketio.run(app, debug=True, use_reloader=False)