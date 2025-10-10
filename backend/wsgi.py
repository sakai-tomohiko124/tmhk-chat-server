"""
ARE - WSGI Entry Point
Production server entry point for Gunicorn
"""

import os
from app import create_app, socketio

# 環境変数から設定を取得（デフォルトはproduction）
config_name = os.getenv('FLASK_ENV', 'production')

# Flaskアプリとsocketioインスタンスを作成
app, socketio = create_app(config_name)

if __name__ == '__main__':
    # 開発環境での起動（本番環境ではGunicornを使用）
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=config_name == 'development'
    )
