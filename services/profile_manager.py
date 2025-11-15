import os
import json
from typing import Dict, Any, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class ProfileManager:
    def __init__(self, db_conn, app_root):
        self.db = db_conn
        self.upload_folder = os.path.join(app_root, 'static', 'uploads')
        self._ensure_upload_directory()

    def _ensure_upload_directory(self):
        """アップロードディレクトリの作成"""
        os.makedirs(self.upload_folder, exist_ok=True)

    def update_profile(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """プロフィール情報の更新"""
        updates = []
        values = []
        
        # 更新可能なフィールド
        allowed_fields = {
            'username': str,
            'email': str,
            'status_message': str,
            'bio': str,
            'birthday': str,
            'show_typing': bool,
            'show_online_status': bool
        }
        
        # フィールドの検証と更新
        for field, value in data.items():
            if field in allowed_fields:
                if field == 'email' and value:
                    # メールアドレスの重複チェック
                    cursor = self.db.execute('SELECT id FROM users WHERE email = ? AND id != ?',
                                      (value, user_id))
                    if cursor.fetchone():
                        raise ValueError('このメールアドレスは既に使用されています')
                
                updates.append(f"{field} = ?")
                values.append(value)
        
        if updates:
            values.append(user_id)
            query = f"""
                UPDATE users
                SET {', '.join(updates)}
                WHERE id = ?
            """
            self.db.execute(query, values)
            self.db.commit()
        
        return self.get_profile(user_id)

    def update_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """パスワードの更新"""
        cursor = self.db.execute('SELECT password FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['password'], current_password):
            return False
        
        hashed_password = generate_password_hash(new_password)
        self.db.execute('UPDATE users SET password = ? WHERE id = ?',
                  (hashed_password, user_id))
        self.db.commit()
        return True

    def update_profile_image(self, user_id: int, image_file) -> str:
        """プロフィール画像の更新"""
        if not image_file:
            raise ValueError('画像ファイルが提供されていません')
        
        filename = f"profile_{user_id}_{int(datetime.now().timestamp())}.png"
        filepath = os.path.join(self.upload_folder, filename)
        
        # 画像の保存
        image_file.save(filepath)
        
        # データベースの更新
        self.db.execute('UPDATE users SET profile_image = ? WHERE id = ?',
                  (filename, user_id))
        self.db.commit()
        
        return filename

    def update_background_image(self, user_id: int, image_file) -> str:
        """背景画像の更新"""
        if not image_file:
            raise ValueError('画像ファイルが提供されていません')
        
        filename = f"bg_{user_id}_{int(datetime.now().timestamp())}.png"
        filepath = os.path.join(self.upload_folder, filename)
        
        # 画像の保存
        image_file.save(filepath)
        
        # データベースの更新
        self.db.execute('UPDATE users SET background_image = ? WHERE id = ?',
                  (filename, user_id))
        self.db.commit()
        
        return filename

    def get_profile(self, user_id: int) -> Dict[str, Any]:
        """プロフィール情報の取得"""
        cursor = self.db.execute('''
            SELECT 
                username, email, profile_image, background_image,
                status_message, bio, birthday,
                show_typing, show_online_status, created_at
            FROM users
            WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        profile = dict(row)
        
        # オンラインステータスの取得（仮実装）
        profile['is_online'] = False
        
        return profile

    def get_privacy_settings(self, user_id: int) -> Dict[str, bool]:
        """プライバシー設定の取得"""
        cursor = self.db.execute('''
            SELECT show_typing, show_online_status
            FROM users
            WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return {}
        
        return dict(row)

    def update_privacy_settings(self, user_id: int, settings: Dict[str, bool]) -> Dict[str, bool]:
        """プライバシー設定の更新"""
        updates = []
        values = []
        
        allowed_settings = {'show_typing', 'show_online_status'}
        
        for setting, value in settings.items():
            if setting in allowed_settings:
                updates.append(f"{setting} = ?")
                values.append(1 if value else 0)
        
        if updates:
            values.append(user_id)
            query = f"""
                UPDATE users
                SET {', '.join(updates)}
                WHERE id = ?
            """
            self.db.execute(query, values)
            self.db.commit()
        
        return self.get_privacy_settings(user_id)
