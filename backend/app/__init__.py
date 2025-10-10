"""
ARE - Flask Application Factory
2035年次世代統合コミュニケーションアプリ
"""

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from app.config import config
from app.extensions import db, jwt, migrate, cache, redis_client


def create_app(config_name='development'):
    """
    Flaskアプリケーションファクトリー
    
    Args:
        config_name: 環境名 ('development', 'production', 'testing')
    
    Returns:
        Flask: 初期化済みFlaskアプリ
    """
    app = Flask(__name__)
    
    # 設定の読み込み
    app.config.from_object(config[config_name])
    
    # 拡張機能の初期化
    initialize_extensions(app)
    
    # CORS設定
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Blueprintの登録
    register_blueprints(app)
    
    # WebSocketの初期化
    socketio = initialize_socketio(app)
    
    # エラーハンドラーの登録
    register_error_handlers(app)
    
    # CLIコマンドの登録
    register_cli_commands(app)
    
    return app, socketio


def initialize_extensions(app):
    """Flask拡張機能の初期化"""
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    
    # Redisクライアントの初期化
    redis_client.init_app(app)


def register_blueprints(app):
    """APIルートの登録"""
    from app.routes import auth, chat, friends, media, call, stories
    from app.routes import games, ai, workspace, user, notification
    
    # API v1 Blueprints
    app.register_blueprint(auth.bp, url_prefix='/api/v1/auth')
    app.register_blueprint(chat.bp, url_prefix='/api/v1/chat')
    app.register_blueprint(friends.bp, url_prefix='/api/v1/friends')
    app.register_blueprint(media.bp, url_prefix='/api/v1/media')
    app.register_blueprint(call.bp, url_prefix='/api/v1/call')
    app.register_blueprint(stories.bp, url_prefix='/api/v1/stories')
    app.register_blueprint(games.bp, url_prefix='/api/v1/games')
    app.register_blueprint(ai.bp, url_prefix='/api/v1/ai')
    app.register_blueprint(workspace.bp, url_prefix='/api/v1/workspace')
    app.register_blueprint(user.bp, url_prefix='/api/v1/user')
    app.register_blueprint(notification.bp, url_prefix='/api/v1/notifications')


def initialize_socketio(app):
    """Flask-SocketIOの初期化"""
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config.get('CORS_ORIGINS', '*'),
        async_mode='gevent',
        logger=True,
        engineio_logger=True
    )
    
    # WebSocketイベントハンドラーの登録
    from app.websocket import chat, call, presence
    
    return socketio


def register_error_handlers(app):
    """エラーハンドラーの登録"""
    from flask import jsonify
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad Request', 'message': str(error)}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'message': 'Permission denied'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not Found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal Server Error: {error}')
        return jsonify({'error': 'Internal Server Error', 'message': 'Something went wrong'}), 500


def register_cli_commands(app):
    """CLIコマンドの登録"""
    
    @app.cli.command('init-db')
    def init_db():
        """データベース初期化"""
        db.create_all()
        print('Database initialized!')
    
    @app.cli.command('seed-db')
    def seed_db():
        """テストデータ投入"""
        from app.models import User
        # テストユーザー作成
        test_user = User(
            email='test@are.com',
            username='testuser',
            display_name='テストユーザー'
        )
        test_user.set_password('password123')
        db.session.add(test_user)
        db.session.commit()
        print('Test data seeded!')
