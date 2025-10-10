"""
ARE - ワークスペースモデル
"""

from datetime import datetime
from app.extensions import db


class Workspace(db.Model):
    """ワークスペースモデル"""
    
    __tablename__ = 'workspaces'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ワークスペース設定
    avatar_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    tasks = db.relationship('Task', backref='workspace', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Workspace {self.id} - {self.name}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'task_count': self.tasks.count(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Task(db.Model):
    """タスクモデル"""
    
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # タスク情報
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, done
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    
    # 期限
    due_date = db.Column(db.DateTime)
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_workspace_status', 'workspace_id', 'status'),
        db.Index('idx_assigned_status', 'assigned_to', 'status'),
    )
    
    def __repr__(self):
        return f'<Task {self.id} - {self.title}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'workspace_id': self.workspace_id,
            'created_by': self.created_by,
            'assigned_to': self.assigned_to,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
