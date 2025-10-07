# DBファイル名・管理者ユーザー名の定数を追加
DATABASE = 'abc.db'
ADMIN_USERNAME = 'skytomo124'
"""
本番環境用設定ファイル
既存のコードを変更せずに本番環境の問題を解決するための設定
"""

import os

class Config:
    # 本番環境での基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_very_secret_key_for_tmhkchat_2035')
    
    # 本番環境でのパス設定
    STATIC_FOLDER = 'static'
    TEMPLATE_FOLDER = 'templates'
    
    # 本番環境でのホスト設定
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # 本番環境でのプロキシ設定
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'http')
    
    # 本番環境でのセキュリティ設定
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 本番環境でのログ設定
    LOG_LEVEL = 'WARNING' if os.environ.get('FLASK_ENV') == 'production' else 'INFO'

class ProductionConfig(Config):
    """本番環境用の追加設定"""
    DEBUG = False
    TESTING = False
    
    # プロキシサーバー対応
    PROXY_FIX_FOR = 1
    PROXY_FIX_PROTO = 1
    PROXY_FIX_HOST = 1
    PROXY_FIX_PREFIX = 1

class DevelopmentConfig(Config):
    """開発環境用設定"""
    DEBUG = True
    TESTING = False

# 環境に応じた設定の選択
def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    else:
        return DevelopmentConfig()

# NGワードリスト（分割管理）
NG_WORDS = [
    "やば","ザコ","くさ","AI","ともひこ","ひこ","ポテト","ねずひこ","おかしい","うそ","大丈夫","？",
    "どうした","え？","は？","あっそ","ふーん","ふざ","でしょ","デッキブラシ","ブチコ","どっち","ん？",
    "すいません","とも","馬鹿", "アホ", "死ね", "殺す", "馬鹿野郎", "バカ","クソ", "糞", "ちくしょう",
    "畜生", "くたばれ", "うん","おかしい","ばか","学習"
]