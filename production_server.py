"""
本番環境用起動スクリプト
既存のabcd.pyを変更せずに本番環境の問題を解決するためのラッパー
"""

import os
import sys
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

# 既存のabcd.pyをインポート
from abcd import app, socketio, init_db, DATABASE

# 本番環境用設定とエラーハンドラーをインポート
from config import get_config
from error_handlers import register_error_handlers
from method_fixes import setup_method_fixes
from debug_routes import add_debug_routes

def setup_production_app():
    """本番環境用のアプリケーション設定"""
    
    # 設定を読み込み
    config = get_config()
    
    # アプリケーションに設定を適用
    app.config.from_object(config)
    
    # 本番環境でのプロキシ設定
    if os.environ.get('FLASK_ENV') == 'production':
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=getattr(config, 'PROXY_FIX_FOR', 1),
            x_proto=getattr(config, 'PROXY_FIX_PROTO', 1),
            x_host=getattr(config, 'PROXY_FIX_HOST', 1),
            x_prefix=getattr(config, 'PROXY_FIX_PREFIX', 1)
        )
    
    # エラーハンドラーを登録
    register_error_handlers(app)
    
    # 405エラー対策を適用
    setup_method_fixes(app)
    
    # デバッグルートを追加（開発時のみ）
    if os.environ.get('FLASK_ENV') != 'production':
        add_debug_routes(app)
    
    # ログ設定
    if os.environ.get('FLASK_ENV') == 'production':
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
            handlers=[
                logging.FileHandler('tmhk_chat.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    # データベースの初期化確認
    if not os.path.exists(DATABASE):
        print("データベースを初期化中...")
        init_db()
        print("データベースの初期化が完了しました。")
    
    return app

def run_production_server():
    """本番環境用サーバーの起動"""
    
    # アプリケーションをセットアップ
    production_app = setup_production_app()
    
    # 環境変数から設定を取得
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    print(f"TMHKchat Server starting on {host}:{port}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    try:
        # 本番環境用でSocketIOサーバーを起動
        socketio.run(
            production_app,
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            log_output=os.environ.get('FLASK_ENV') != 'production'
        )
    except Exception as e:
        logging.error(f"サーバー起動エラー: {e}")
        print(f"エラー: サーバーの起動に失敗しました: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # 本番環境用サーバーを起動
    run_production_server()