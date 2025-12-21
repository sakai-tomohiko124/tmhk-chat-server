"""
Profile Manager - ユーザープロフィール管理
"""
import os
from datetime import datetime
from PIL import Image
import io

class ProfileManager:
    """ユーザープロフィール管理クラス"""
    
    def __init__(self, db, root_path):
        """初期化"""
        self.db = db
        self.root_path = root_path
        self.upload_folder = os.path.join(root_path, 'static', 'uploads', 'profiles')
        self._ensure_upload_folder()
    
    def _ensure_upload_folder(self):
        """アップロードフォルダの作成"""
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def get_profile(self, user_id):
        """ユーザープロフィール取得"""
        try:
            cursor = self.db.execute(
                "SELECT id, username, bio, profile_image, background_image, created_at FROM users WHERE id = ?",
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                return None
            
            return {
                'id': user['id'],
                'username': user['username'],
                'bio': user.get('bio', ''),
                'profile_image': user.get('profile_image', ''),
                'background_image': user.get('background_image', ''),
                'created_at': user['created_at']
            }
        except Exception as e:
            raise Exception(f"プロフィール取得エラー: {str(e)}")
    
    def update_profile(self, user_id, data):
        """ユーザープロフィール更新"""
        try:
            username = data.get('username', '')
            bio = data.get('bio', '')
            
            if not username:
                raise ValueError("ユーザー名は必須です")
            
            self.db.execute(
                "UPDATE users SET username = ?, bio = ?, updated_at = ? WHERE id = ?",
                (username, bio, datetime.now().isoformat(), user_id)
            )
            self.db.commit()
            
            return self.get_profile(user_id)
        except Exception as e:
            raise Exception(f"プロフィール更新エラー: {str(e)}")
    
    def update_profile_image(self, user_id, image_file):
        """プロフィール画像更新"""
        try:
            if not image_file or image_file.filename == '':
                raise ValueError("ファイルが選択されていません")
            
            # 画像処理
            img = Image.open(image_file.stream)
            img.thumbnail((200, 200))
            
            filename = f"profile_{user_id}_{datetime.now().timestamp()}.png"
            filepath = os.path.join(self.upload_folder, filename)
            img.save(filepath)
            
            # DB更新
            self.db.execute(
                "UPDATE users SET profile_image = ?, updated_at = ? WHERE id = ?",
                (f"uploads/profiles/{filename}", datetime.now().isoformat(), user_id)
            )
            self.db.commit()
            
            return filename
        except Exception as e:
            raise Exception(f"画像アップロードエラー: {str(e)}")
    
    def update_background_image(self, user_id, image_file):
        """背景画像更新"""
        try:
            if not image_file or image_file.filename == '':
                raise ValueError("ファイルが選択されていません")
            
            # 画像処理
            img = Image.open(image_file.stream)
            img.thumbnail((1200, 400))
            
            filename = f"background_{user_id}_{datetime.now().timestamp()}.png"
            filepath = os.path.join(self.upload_folder, filename)
            img.save(filepath)
            
            # DB更新
            self.db.execute(
                "UPDATE users SET background_image = ?, updated_at = ? WHERE id = ?",
                (f"uploads/profiles/{filename}", datetime.now().isoformat(), user_id)
            )
            self.db.commit()
            
            return filename
        except Exception as e:
            raise Exception(f"背景画像アップロードエラー: {str(e)}")
    
    def get_privacy_settings(self, user_id):
        """プライバシー設定取得"""
        try:
            cursor = self.db.execute(
                "SELECT * FROM privacy_settings WHERE user_id = ?",
                (user_id,)
            )
            settings = cursor.fetchone()
            
            if not settings:
                # デフォルト設定を返す
                return {
                    'show_profile': True,
                    'allow_messages': True,
                    'show_online_status': True,
                    'show_last_seen': True
                }
            
            return dict(settings)
        except Exception as e:
            raise Exception(f"プライバシー設定取得エラー: {str(e)}")
    
    def update_privacy_settings(self, user_id, data):
        """プライバシー設定更新"""
        try:
            self.db.execute(
                """
                INSERT OR REPLACE INTO privacy_settings 
                (user_id, show_profile, allow_messages, show_online_status, show_last_seen, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    data.get('show_profile', True),
                    data.get('allow_messages', True),
                    data.get('show_online_status', True),
                    data.get('show_last_seen', True),
                    datetime.now().isoformat()
                )
            )
            self.db.commit()
            
            return self.get_privacy_settings(user_id)
        except Exception as e:
            raise Exception(f"プライバシー設定更新エラー: {str(e)}")
