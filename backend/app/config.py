"""
ARE - アプリケーション設定
環境別設定クラス
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()


class Config:
    """基本設定クラス"""
    
    # Flask設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')
    DEBUG = False
    TESTING = False
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///are_dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Redis設定
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # JWT設定
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # CORS設定
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # ファイルアップロード設定
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 
                         'mp3', 'wav', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}
    
    # AWS設定
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-1')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')
    AWS_CLOUDFRONT_DOMAIN = os.getenv('AWS_CLOUDFRONT_DOMAIN')
    
    # Supabase設定
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
    SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'are-media')
    
    # Agora.io設定
    AGORA_APP_ID = os.getenv('AGORA_APP_ID')
    AGORA_APP_CERTIFICATE = os.getenv('AGORA_APP_CERTIFICATE')
    
    # Grok API設定
    GROK_API_KEY = os.getenv('GROK_API_KEY')
    GROK_API_BASE_URL = os.getenv('GROK_API_BASE_URL', 'https://api.x.ai/v1')
    
    # Celery設定
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'Asia/Tokyo'
    
    # セキュリティ設定
    BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', 12))
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # キャッシュ設定
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    
    # ログ設定
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/are.log')
    
    # その他設定
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Tokyo')
    LANGUAGE = os.getenv('LANGUAGE', 'ja')
    ITEMS_PER_PAGE = 20
    

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # 本番環境ではPostgreSQLを使用
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://user:pass@localhost:5432/are_production'
    )
    
    # Heroku/Renderの場合、postgres:// を postgresql:// に変換
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            'postgres://', 'postgresql://', 1
        )


class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# 環境別設定のマッピング
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
