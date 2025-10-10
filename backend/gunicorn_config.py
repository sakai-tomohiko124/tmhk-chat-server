"""
ARE - Gunicorn Configuration
本番環境用のGunicorn設定ファイル
"""

import multiprocessing
import os

# サーバーソケット設定
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# ワーカープロセス設定
# CPUコア数 × 2 + 1 が推奨値
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "eventlet"  # WebSocket対応（Flask-SocketIO使用）
worker_connections = 1000
max_requests = 1000  # メモリリーク対策
max_requests_jitter = 50  # max_requestsにランダム性を追加
timeout = 120  # タイムアウト（秒）
keepalive = 5  # Keep-Alive接続時間（秒）

# スレッド設定（eventletを使う場合は不要）
# threads = 2

# ログ設定
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"  # debug, info, warning, error, critical
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# プロセス命名
proc_name = "are-backend"

# デーモン化（PM2を使う場合はFalse）
daemon = False

# 開発環境での自動リロード（本番環境ではFalse）
reload = os.getenv('FLASK_ENV') == 'development'
reload_engine = 'auto'

# セキュリティ設定
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# サーバーフック
def on_starting(server):
    """サーバー起動時"""
    print("=" * 60)
    print("🚀 ARE Backend Server Starting...")
    print(f"👷 Workers: {workers}")
    print(f"🔧 Worker Class: {worker_class}")
    print(f"📍 Binding: {bind}")
    print("=" * 60)

def on_reload(server):
    """リロード時"""
    print("🔄 Reloading server...")

def when_ready(server):
    """サーバー準備完了時"""
    print("✅ Server is ready. Accepting connections.")

def on_exit(server):
    """サーバー終了時"""
    print("👋 ARE Backend Server stopped.")
