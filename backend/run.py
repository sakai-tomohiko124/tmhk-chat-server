"""
ARE - Development Server Runner
開発環境用のサーバー起動スクリプト
"""

from app import create_app, socketio

# 開発環境でアプリを作成
app, socketio = create_app('development')

if __name__ == '__main__':
    print("=" * 60)
    print("ARE Development Server")
    print("=" * 60)
    print("🚀 Starting Flask-SocketIO development server...")
    print("📍 URL: http://127.0.0.1:5000")
    print("📍 API: http://127.0.0.1:5000/api/v1/")
    print("🔌 WebSocket: ws://127.0.0.1:5000/socket.io")
    print("=" * 60)
    print("Press CTRL+C to quit")
    print()
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True,
        log_output=True
    )
