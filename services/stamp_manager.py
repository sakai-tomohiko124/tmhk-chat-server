"""
Stamp Manager - スタンプ管理
"""
import os
from datetime import datetime

class StampManager:
    """スタンプ管理クラス"""
    
    def __init__(self, db, root_path):
        """初期化"""
        self.db = db
        self.root_path = root_path
        self.stamp_folder = os.path.join(root_path, 'static', 'assets', 'stamps')
        self._ensure_stamp_folder()
    
    def _ensure_stamp_folder(self):
        """スタンプフォルダの作成"""
        os.makedirs(self.stamp_folder, exist_ok=True)
    
    def get_stamps(self, category=None, tag=None):
        """スタンプ一覧取得"""
        try:
            query = "SELECT * FROM stamps WHERE 1=1"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if tag:
                query += " AND tag = ?"
                params.append(tag)
            
            cursor = self.db.execute(query, params)
            stamps = [dict(row) for row in cursor.fetchall()]
            
            return stamps
        except Exception as e:
            raise Exception(f"スタンプ取得エラー: {str(e)}")
    
    def get_categories(self):
        """スタンプカテゴリー一覧取得"""
        try:
            cursor = self.db.execute(
                "SELECT DISTINCT category FROM stamps ORDER BY category"
            )
            categories = [row['category'] for row in cursor.fetchall()]
            
            return categories
        except Exception as e:
            raise Exception(f"カテゴリー取得エラー: {str(e)}")
    
    def add_stamp(self, name, category, image_file, tag=None):
        """スタンプ追加"""
        try:
            if not image_file or image_file.filename == '':
                raise ValueError("画像ファイルが必要です")
            
            filename = f"stamp_{datetime.now().timestamp()}.png"
            filepath = os.path.join(self.stamp_folder, filename)
            image_file.save(filepath)
            
            self.db.execute(
                """
                INSERT INTO stamps (name, category, tag, image_path, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, category, tag, f"assets/stamps/{filename}", datetime.now().isoformat())
            )
            self.db.commit()
            
            return True
        except Exception as e:
            raise Exception(f"スタンプ追加エラー: {str(e)}")
    
    def delete_stamp(self, stamp_id):
        """スタンプ削除"""
        try:
            cursor = self.db.execute("SELECT image_path FROM stamps WHERE id = ?", (stamp_id,))
            stamp = cursor.fetchone()
            
            if not stamp:
                raise ValueError("スタンプが見つかりません")
            
            # ファイル削除
            if stamp['image_path']:
                filepath = os.path.join(self.root_path, 'static', stamp['image_path'].lstrip('/'))
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            # DB削除
            self.db.execute("DELETE FROM stamps WHERE id = ?", (stamp_id,))
            self.db.commit()
            
            return True
        except Exception as e:
            raise Exception(f"スタンプ削除エラー: {str(e)}")
    
    def get_user_stamps(self, user_id):
        """ユーザーが持つスタンプ取得"""
        try:
            cursor = self.db.execute(
                """
                SELECT s.* FROM stamps s
                JOIN user_stamps us ON s.id = us.stamp_id
                WHERE us.user_id = ?
                """,
                (user_id,)
            )
            stamps = [dict(row) for row in cursor.fetchall()]
            
            return stamps
        except Exception as e:
            raise Exception(f"ユーザースタンプ取得エラー: {str(e)}")
    
    def add_stamp_to_user(self, user_id, stamp_id):
        """ユーザーにスタンプを追加"""
        try:
            self.db.execute(
                "INSERT OR IGNORE INTO user_stamps (user_id, stamp_id, acquired_at) VALUES (?, ?, ?)",
                (user_id, stamp_id, datetime.now().isoformat())
            )
            self.db.commit()
            
            return True
        except Exception as e:
            raise Exception(f"ユーザースタンプ追加エラー: {str(e)}")
