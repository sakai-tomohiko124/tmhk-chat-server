"""
ARE - ゲームモデル
"""

from datetime import datetime
from app.extensions import db


class Game(db.Model):
    """ゲームセッションモデル"""
    
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ゲーム情報
    game_type = db.Column(db.String(50), nullable=False)  # daifugo, oldmaid, memory, etc.
    status = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    
    # ゲーム設定
    max_players = db.Column(db.Integer, default=4)
    settings = db.Column(db.JSON)  # ゲーム固有の設定
    
    # ゲームデータ
    game_data = db.Column(db.JSON)  # ゲーム状態データ
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    
    # リレーションシップ
    scores = db.relationship('GameScore', backref='game', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Game {self.id} - {self.game_type}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'creator_id': self.creator_id,
            'game_type': self.game_type,
            'status': self.status,
            'max_players': self.max_players,
            'settings': self.settings,
            'game_data': self.game_data,
            'winner_id': self.winner_id,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }


class GameScore(db.Model):
    """ゲームスコアモデル"""
    
    __tablename__ = 'game_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # スコア情報
    score = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)
    is_winner = db.Column(db.Boolean, default=False)
    
    # 統計情報
    achievements = db.Column(db.JSON)  # 獲得した実績
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_game_user', 'game_id', 'user_id'),
        db.Index('idx_user_score', 'user_id', 'score'),
    )
    
    def __repr__(self):
        return f'<GameScore game={self.game_id} user={self.user_id} score={self.score}>'
