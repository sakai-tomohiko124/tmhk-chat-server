"""
ARE - 通話モデル
"""

from datetime import datetime
from app.extensions import db


class Call(db.Model):
    """通話モデル"""
    
    __tablename__ = 'calls'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    initiator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 通話情報
    call_type = db.Column(db.String(20), nullable=False)  # audio, video, screen_share
    status = db.Column(db.String(20), default='initiated')  # initiated, ringing, ongoing, ended, missed
    
    # Agoraチャネル情報
    channel_name = db.Column(db.String(100), unique=True)
    agora_token = db.Column(db.String(500))
    
    # 通話時間
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # 秒
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # リレーションシップ
    participants = db.relationship('CallParticipant', backref='call', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Call {self.id} - {self.call_type}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'initiator_id': self.initiator_id,
            'call_type': self.call_type,
            'status': self.status,
            'channel_name': self.channel_name,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration': self.duration,
            'created_at': self.created_at.isoformat(),
            'participant_count': self.participants.count(),
        }


class CallParticipant(db.Model):
    """通話参加者モデル"""
    
    __tablename__ = 'call_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey('calls.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 参加情報
    joined_at = db.Column(db.DateTime)
    left_at = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # 秒
    
    # ステータス
    is_audio_on = db.Column(db.Boolean, default=True)
    is_video_on = db.Column(db.Boolean, default=True)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_call_user', 'call_id', 'user_id'),
    )
    
    def __repr__(self):
        return f'<CallParticipant call={self.call_id} user={self.user_id}>'
