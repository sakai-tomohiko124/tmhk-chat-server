# Flaskアプリ本体・ルート定義の起点

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = 'skytomohiko124'  # 本番は環境変数推奨
socketio = SocketIO(app)

# ここにルートや初期化をimportして使います

# 分割管理例（必要に応じてファイル名・関数名を調整してください）
from db import init_db

from routes import register_routes  # ルート分割時
from socketio_handlers import register_socketio_events  # SocketIOイベント分割時

if __name__ == '__main__':
	init_db()
	register_routes(app)
	register_socketio_events(socketio)
	socketio.run(app, host='0.0.0.0', port=5000, debug=False)