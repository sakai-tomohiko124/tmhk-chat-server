"""
ARE - 友達関係モデル
"""

from datetime import datetime
from app.extensions import db


class Friend(db.Model):
    """友達関係モデル"""
    
    __tablename__ = 'friends'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 関係性の種類
    relationship_type = db.Column(db.String(20), default='friend')  # friend, blocked, muted
    
    # ニックネーム（友達に付ける名前）
    nickname = db.Column(db.String(100))
    
    # お気に入り
    is_favorite = db.Column(db.Boolean, default=False)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # インデックス
    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
        db.Index('idx_user_friend', 'user_id', 'friend_id'),
        db.Index('idx_friend_user', 'friend_id', 'user_id'),
        db.CheckConstraint('user_id != friend_id', name='check_not_self_friend'),
    )
    
    def __repr__(self):
        return f'<Friend {self.user_id} -> {self.friend_id}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'friend_id': self.friend_id,
            'relationship_type': self.relationship_type,
            'nickname': self.nickname,
            'is_favorite': self.is_favorite,
            'created_at': self.created_at.isoformat(),
        }
    
    @staticmethod
    def are_friends(user_id, friend_id):
        """2人が友達かどうかチェック"""
        return Friend.query.filter(
            db.or_(
                db.and_(Friend.user_id == user_id, Friend.friend_id == friend_id),
                db.and_(Friend.user_id == friend_id, Friend.friend_id == user_id)
            ),
            Friend.relationship_type == 'friend'
        ).first() is not None
    
    @staticmethod
    def is_blocked(user_id, blocked_user_id):
        """ブロック状態かどうかチェック"""
        return Friend.query.filter_by(
            user_id=user_id,
            friend_id=blocked_user_id,
            relationship_type='blocked'
        ).first() is not None


class FriendRequest(db.Model):
    """友達リクエストモデル"""
    
    __tablename__ = 'friend_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # リクエストの状態
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, cancelled
    
    # メッセージ
    message = db.Column(db.Text)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_sender_receiver', 'sender_id', 'receiver_id'),
        db.Index('idx_receiver_status', 'receiver_id', 'status'),
        db.CheckConstraint('sender_id != receiver_id', name='check_not_self_request'),
    )
    
    def __repr__(self):
        return f'<FriendRequest {self.sender_id} -> {self.receiver_id} ({self.status})>'
    
    def to_dict(self, include_sender=True, include_receiver=True):
        """辞書形式に変換"""
        data = {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'status': self.status,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
        }
        
        if include_sender:
            from app.models.user import User
            sender = User.query.get(self.sender_id)
            data['sender'] = sender.to_dict() if sender else None
        
        if include_receiver:
            from app.models.user import User
            receiver = User.query.get(self.receiver_id)
            data['receiver'] = receiver.to_dict() if receiver else None
        
        return data
    
    def accept(self):
        """友達リクエストを承認"""
        self.status = 'accepted'
        self.responded_at = datetime.utcnow()
        
        # 双方向の友達関係を作成
        friend1 = Friend(user_id=self.sender_id, friend_id=self.receiver_id)
        friend2 = Friend(user_id=self.receiver_id, friend_id=self.sender_id)
        
        db.session.add(friend1)
        db.session.add(friend2)
        db.session.commit()
    
    def reject(self):
        """友達リクエストを拒否"""
        self.status = 'rejected'
        self.responded_at = datetime.utcnow()
        db.session.commit()
    
    def cancel(self):
        """友達リクエストをキャンセル"""
        self.status = 'cancelled'
        self.responded_at = datetime.utcnow()
        db.session.commit()
