import os
import hashlib
from PIL import Image, ImageDraw
import numpy as np
from io import BytesIO
import base64

class AvatarGenerator:
    def __init__(self):
        self.colors = {
            'skin': ['#FFD5C2', '#F5C7A9', '#D1A3A4', '#A67C7E'],
            'hair': ['#2C1810', '#4A1F15', '#8C3B2B', '#B04836'],
            'eyes': ['#634E34', '#2C1810', '#000000'],
            'background': ['#E3F2FD', '#F3E5F5', '#E8F5E9', '#FFF3E0']
        }
        
        self.features = {
            'face_shape': ['round', 'oval', 'square'],
            'hair_style': ['short', 'medium', 'long'],
            'eye_style': ['round', 'almond', 'wide'],
            'mouth_style': ['smile', 'neutral', 'serious']
        }

    def _create_base_image(self, size=(400, 400)):
        """ベース画像の作成"""
        return Image.new('RGBA', size, (255, 255, 255, 0))

    def _generate_unique_seed(self, user_id):
        """ユーザーIDから一意のシード値を生成"""
        return int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)

    def _hex_to_rgb(self, hex_color):
        """16進数のカラーコードをRGBに変換"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_face(self, draw, shape, color, size):
        """顔の描画"""
        x, y = size[0] // 2, size[1] // 2
        radius = min(size) // 3
        
        if shape == 'round':
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
        elif shape == 'oval':
            draw.ellipse([x - radius, y - int(radius * 1.2), x + radius, y + int(radius * 1.2)], fill=color)
        else:  # square
            draw.rectangle([x - radius, y - radius, x + radius, y + radius], fill=color)

    def _draw_hair(self, draw, style, color, size):
        """髪の描画"""
        x, y = size[0] // 2, size[1] // 2
        radius = min(size) // 3
        
        if style == 'short':
            draw.arc([x - radius, y - radius - 30, x + radius, y], fill=color, width=20)
        elif style == 'medium':
            draw.arc([x - radius - 10, y - radius - 40, x + radius + 10, y + 10], fill=color, width=25)
        else:  # long
            draw.arc([x - radius - 20, y - radius - 50, x + radius + 20, y + 30], fill=color, width=30)

    def _draw_eyes(self, draw, style, color, size):
        """目の描画"""
        x, y = size[0] // 2, size[1] // 2
        eye_offset = 40
        eye_size = 15
        
        if style == 'round':
            draw.ellipse([x - eye_offset - eye_size, y - 20, x - eye_offset + eye_size, y + 10], fill=color)
            draw.ellipse([x + eye_offset - eye_size, y - 20, x + eye_offset + eye_size, y + 10], fill=color)
        elif style == 'almond':
            draw.ellipse([x - eye_offset - eye_size, y - 15, x - eye_offset + eye_size, y + 5], fill=color)
            draw.ellipse([x + eye_offset - eye_size, y - 15, x + eye_offset + eye_size, y + 5], fill=color)
        else:  # wide
            draw.ellipse([x - eye_offset - 20, y - 15, x - eye_offset + 10, y + 5], fill=color)
            draw.ellipse([x + eye_offset - 10, y - 15, x + eye_offset + 20, y + 5], fill=color)

    def _draw_mouth(self, draw, style, size):
        """口の描画"""
        x, y = size[0] // 2, size[1] // 2
        
        if style == 'smile':
            draw.arc([x - 30, y + 20, x + 30, y + 60], start=0, end=180, fill='#2C1810', width=3)
        elif style == 'neutral':
            draw.line([x - 30, y + 40, x + 30, y + 40], fill='#2C1810', width=3)
        else:  # serious
            draw.arc([x - 30, y + 30, x + 30, y + 70], start=180, end=360, fill='#2C1810', width=3)

    def generate_avatar(self, user_id, preferences=None):
        """アバターの生成"""
        # シード値の設定
        np.random.seed(self._generate_unique_seed(user_id))
        
        # ベース画像の作成
        size = (400, 400)
        avatar = self._create_base_image(size)
        
        # 特徴の選択（ユーザー設定または乱数）
        selected_features = {}
        for feature, options in self.features.items():
            if preferences and feature in preferences:
                selected_features[feature] = preferences[feature]
            else:
                selected_features[feature] = np.random.choice(options)
        
        # 色の選択
        selected_colors = {}
        for color_type, colors in self.colors.items():
            if preferences and color_type in preferences:
                selected_colors[color_type] = preferences[color_type]
            else:
                selected_colors[color_type] = np.random.choice(colors)
        
        # 背景の描画
        draw = ImageDraw.Draw(avatar)
        draw.rectangle([0, 0, size[0], size[1]], fill=self._hex_to_rgb(selected_colors['background']))
        
        # 各特徴の描画
        self._draw_face(draw, selected_features['face_shape'], self._hex_to_rgb(selected_colors['skin']), size)
        self._draw_hair(draw, selected_features['hair_style'], self._hex_to_rgb(selected_colors['hair']), size)
        self._draw_eyes(draw, selected_features['eye_style'], self._hex_to_rgb(selected_colors['eyes']), size)
        self._draw_mouth(draw, selected_features['mouth_style'], size)
        
        return avatar

    def save_avatar(self, avatar, user_id, upload_folder):
        """アバターの保存"""
        os.makedirs(upload_folder, exist_ok=True)
        filename = f"avatar_{user_id}.png"
        filepath = os.path.join(upload_folder, filename)
        avatar.save(filepath, 'PNG')
        return filename

    def get_avatar_base64(self, avatar):
        """アバターをBase64エンコードで返す"""
        buffered = BytesIO()
        avatar.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
