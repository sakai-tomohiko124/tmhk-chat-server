"""
ARE - Flask拡張機能
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from redis import Redis


# データベース
db = SQLAlchemy()

# マイグレーション
migrate = Migrate()

# JWT認証
jwt = JWTManager()

# キャッシュ
cache = Cache()


class RedisClient:
    """Redisクライアントラッパー"""
    
    def __init__(self):
        self._client = None
    
    def init_app(self, app):
        """Flaskアプリと連携"""
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        self._client = Redis.from_url(redis_url, decode_responses=True)
    
    @property
    def client(self):
        """Redisクライアントインスタンスを取得"""
        return self._client
    
    def get(self, key):
        """値を取得"""
        return self._client.get(key) if self._client else None
    
    def set(self, key, value, ex=None):
        """値を設定"""
        return self._client.set(key, value, ex=ex) if self._client else False
    
    def delete(self, key):
        """値を削除"""
        return self._client.delete(key) if self._client else False
    
    def exists(self, key):
        """キーの存在確認"""
        return self._client.exists(key) if self._client else False
    
    def hset(self, name, key, value):
        """ハッシュに値を設定"""
        return self._client.hset(name, key, value) if self._client else False
    
    def hget(self, name, key):
        """ハッシュから値を取得"""
        return self._client.hget(name, key) if self._client else None
    
    def hgetall(self, name):
        """ハッシュの全値を取得"""
        return self._client.hgetall(name) if self._client else {}
    
    def sadd(self, name, *values):
        """セットに値を追加"""
        return self._client.sadd(name, *values) if self._client else False
    
    def smembers(self, name):
        """セットの全メンバーを取得"""
        return self._client.smembers(name) if self._client else set()
    
    def srem(self, name, *values):
        """セットから値を削除"""
        return self._client.srem(name, *values) if self._client else False


# Redisクライアントインスタンス
redis_client = RedisClient()
