"""
ARE - メッセージ・チャットルームモデル
"""

from datetime import datetime
from app.extensions import db


class Room(db.Model):
    """チャットルームモデル"""
    
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    room_type = db.Column(db.String(20), nullable=False)  # private, group
    avatar_url = db.Column(db.String(255))
    description = db.Column(db.Text)
    
    # グループチャット設定
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    members = db.relationship('RoomMember', backref='room', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='room', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Room {self.id} - {self.room_type}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'room_type': self.room_type,
            'avatar_url': self.avatar_url,
            'description': self.description,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'member_count': self.members.count(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class RoomMember(db.Model):
    """チャットルームメンバーモデル"""
    
    __tablename__ = 'room_members'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # メンバー情報
    role = db.Column(db.String(20), default='member')  # admin, member
    nickname = db.Column(db.String(100))  # グループ内ニックネーム
    
    # 通知設定
    is_muted = db.Column(db.Boolean, default=False)
    
    # 既読管理
    last_read_at = db.Column(db.DateTime)
    last_read_message_id = db.Column(db.Integer)
    
    # タイムスタンプ
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # インデックス
    __table_args__ = (
        db.UniqueConstraint('room_id', 'user_id', name='unique_room_member'),
        db.Index('idx_room_member', 'room_id', 'user_id'),
    )
    
    def __repr__(self):
        return f'<RoomMember room={self.room_id} user={self.user_id}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'role': self.role,
            'nickname': self.nickname,
            'is_muted': self.is_muted,
            'joined_at': self.joined_at.isoformat(),
        }


class Message(db.Model):
    """メッセージモデル"""
    
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # メッセージ内容
    message_type = db.Column(db.String(20), nullable=False)  # text, image, video, audio, file, sticker
    content = db.Column(db.Text)  # テキストメッセージの場合
    media_url = db.Column(db.String(255))  # メディアファイルのURL
    file_name = db.Column(db.String(255))  # ファイル名
    file_size = db.Column(db.Integer)  # ファイルサイズ（バイト）
    thumbnail_url = db.Column(db.String(255))  # サムネイル画像
    
    # 返信・引用
    reply_to_id = db.Column(db.Integer, db.ForeignKey('messages.id'))
    
    # ステータス
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_pinned = db.Column(db.Boolean, default=False)
    
    # 暗号化
    is_encrypted = db.Column(db.Boolean, default=False)
    encryption_key_id = db.Column(db.String(100))
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
    
    # リレーションシップ
    reactions = db.relationship('MessageReaction', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    read_receipts = db.relationship('MessageReadReceipt', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    
    # インデックス
    __table_args__ = (
        db.Index('idx_room_created', 'room_id', 'created_at'),
        db.Index('idx_sender_created', 'sender_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id}>'
    
    def to_dict(self, include_sender=True):
        """辞書形式に変換"""
        data = {
            'id': self.id,
            'room_id': self.room_id,
            'sender_id': self.sender_id,
            'message_type': self.message_type,
            'content': self.content if not self.is_deleted else '[削除されたメッセージ]',
            'media_url': self.media_url,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'thumbnail_url': self.thumbnail_url,
            'reply_to_id': self.reply_to_id,
            'is_edited': self.is_edited,
            'is_deleted': self.is_deleted,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sender:
            data['sender'] = self.sender.to_dict()
        
        return data


class MessageReaction(db.Model):
    """メッセージリアクションモデル"""
    
    __tablename__ = 'message_reactions'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)  # 絵文字
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # インデックス
    __table_args__ = (
        db.UniqueConstraint('message_id', 'user_id', 'emoji', name='unique_message_reaction'),
        db.Index('idx_message_reaction', 'message_id', 'user_id'),
    )
    
    def __repr__(self):
        return f'<MessageReaction {self.emoji} by {self.user_id}>'


class MessageReadReceipt(db.Model):
    """メッセージ既読確認モデル"""
    
    __tablename__ = 'message_read_receipts'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # インデックス
    __table_args__ = (
        db.UniqueConstraint('message_id', 'user_id', name='unique_message_read'),
        db.Index('idx_message_read', 'message_id', 'user_id'),
    )
    
    def __repr__(self):
        return f'<MessageReadReceipt message={self.message_id} user={self.user_id}>'
