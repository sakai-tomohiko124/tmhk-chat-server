"""
ARE - ユーザーモデル
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """ユーザーモデル"""
    
    __tablename__ = 'users'
    
    # 基本情報
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # プロフィール情報
    display_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(255))
    cover_image_url = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    
    # ステータス情報
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)
    
    # プライバシー設定
    privacy_profile = db.Column(db.String(20), default='public')  # public, friends, private
    privacy_online_status = db.Column(db.String(20), default='everyone')  # everyone, friends, nobody
    privacy_last_seen = db.Column(db.String(20), default='everyone')
    
    # QRコード
    qr_code = db.Column(db.String(100), unique=True)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    sent_messages = db.relationship('Message', backref='sender', lazy='dynamic', 
                                   foreign_keys='Message.sender_id')
    rooms = db.relationship('RoomMember', backref='user', lazy='dynamic')
    sent_friend_requests = db.relationship('FriendRequest', backref='sender', 
                                          lazy='dynamic', foreign_keys='FriendRequest.sender_id')
    received_friend_requests = db.relationship('FriendRequest', backref='receiver', 
                                              lazy='dynamic', foreign_keys='FriendRequest.receiver_id')
    stories = db.relationship('Story', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """パスワードをハッシュ化して保存"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """パスワードを検証"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_private=False):
        """辞書形式に変換"""
        data = {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'cover_image_url': self.cover_image_url,
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat(),
        }
        
        if include_private:
            data.update({
                'email': self.email,
                'phone_number': self.phone_number,
                'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
                'qr_code': self.qr_code,
                'privacy_profile': self.privacy_profile,
                'privacy_online_status': self.privacy_online_status,
                'privacy_last_seen': self.privacy_last_seen,
            })
        
        return data
    
    def update_online_status(self, is_online=True):
        """オンライン状態を更新"""
        self.is_online = is_online
        self.last_seen = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def generate_qr_code():
        """ユニークなQRコードを生成"""
        import uuid
        return f"ARE-{uuid.uuid4().hex[:12].upper()}"
