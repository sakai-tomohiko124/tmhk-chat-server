"""
ARE - ストーリーモデル
"""

from datetime import datetime, timedelta
from app.extensions import db


class Story(db.Model):
    """ストーリーモデル（24時間限定投稿）"""
    
    __tablename__ = 'stories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # コンテンツ情報
    content_type = db.Column(db.String(20), nullable=False)  # image, video, text
    media_url = db.Column(db.String(500))
    thumbnail_url = db.Column(db.String(500))
    text_content = db.Column(db.Text)
    duration = db.Column(db.Integer, default=5)  # 表示秒数
    
    # プライバシー設定
    privacy = db.Column(db.String(20), default='all')  # all, friends, selected
    
    # ステータス
    is_active = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)  # 24時間後
    
    # リレーションシップ
    views = db.relationship('StoryView', backref='story', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Story, self).__init__(**kwargs)
        # 作成24時間後に自動削除
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    def __repr__(self):
        return f'<Story {self.id} by {self.user_id}>'
    
    def to_dict(self, include_user=True):
        """辞書形式に変換"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'content_type': self.content_type,
            'media_url': self.media_url,
            'thumbnail_url': self.thumbnail_url,
            'text_content': self.text_content,
            'duration': self.duration,
            'privacy': self.privacy,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
        }
        
        if include_user:
            data['user'] = self.user.to_dict()
        
        return data
    
    @property
    def is_expired(self):
        """ストーリーが期限切れかどうか"""
        return datetime.utcnow() > self.expires_at


class StoryView(db.Model):
    """ストーリー視聴履歴モデル"""
    
    __tablename__ = 'story_views'
    
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # インデックス
    __table_args__ = (
        db.UniqueConstraint('story_id', 'user_id', name='unique_story_view'),
        db.Index('idx_story_viewed', 'story_id', 'viewed_at'),
    )
    
    def __repr__(self):
        return f'<StoryView story={self.story_id} user={self.user_id}>'
