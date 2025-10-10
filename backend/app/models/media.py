"""
ARE - メディアファイルモデル
"""

from datetime import datetime
from app.extensions import db


class Media(db.Model):
    """メディアファイルモデル"""
    
    __tablename__ = 'media'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ファイル情報
    file_type = db.Column(db.String(20), nullable=False)  # image, video, audio, document
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)  # バイト
    mime_type = db.Column(db.String(100))
    
    # URL
    file_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500))
    
    # メタデータ
    width = db.Column(db.Integer)  # 画像・動画の幅
    height = db.Column(db.Integer)  # 画像・動画の高さ
    duration = db.Column(db.Integer)  # 動画・音声の長さ（秒）
    
    # ストレージ情報
    storage_provider = db.Column(db.String(50))  # s3, supabase, cloudflare-r2
    storage_path = db.Column(db.String(500))
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_user_created', 'user_id', 'created_at'),
        db.Index('idx_file_type', 'file_type'),
    )
    
    def __repr__(self):
        return f'<Media {self.id} - {self.file_type}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_type': self.file_type,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'file_url': self.file_url,
            'thumbnail_url': self.thumbnail_url,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'created_at': self.created_at.isoformat(),
        }
