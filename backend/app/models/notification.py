"""
ARE - 通知モデル
"""

from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    """通知モデル"""
    
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 通知情報
    notification_type = db.Column(db.String(50), nullable=False)  # message, friend_request, call, story, etc.
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    
    # 関連情報
    related_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 通知を発生させたユーザー
    related_id = db.Column(db.Integer)  # 関連するエンティティID
    related_type = db.Column(db.String(50))  # message, call, story, etc.
    
    # アクションURL
    action_url = db.Column(db.String(255))
    
    # ステータス
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_user_read', 'user_id', 'is_read'),
        db.Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Notification {self.id} to {self.user_id}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notification_type': self.notification_type,
            'title': self.title,
            'content': self.content,
            'related_user_id': self.related_user_id,
            'related_id': self.related_id,
            'related_type': self.related_type,
            'action_url': self.action_url,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat(),
        }
    
    def mark_as_read(self):
        """既読にする"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
