import os
import json
from typing import List, Dict, Any
from datetime import datetime

class StampManager:
    def __init__(self, db_conn, app_root):
        self.db = db_conn
        self.stamp_folder = os.path.join(app_root, 'static', 'stamps')
        self.stamp_data_file = os.path.join(app_root, 'data', 'stamps.json')
        self._ensure_directories()
        self._load_stamp_data()

    def _ensure_directories(self):
        """必要なディレクトリの作成"""
        os.makedirs(self.stamp_folder, exist_ok=True)
        os.makedirs(os.path.dirname(self.stamp_data_file), exist_ok=True)

    def _load_stamp_data(self):
        """スタンプデータの読み込み"""
        try:
            with open(self.stamp_data_file, 'r', encoding='utf-8') as f:
                self.stamp_data = json.load(f)
        except FileNotFoundError:
            self.stamp_data = {
                'categories': ['感情', 'あいさつ', '動物', 'その他'],
                'stamps': {}
            }
            self._save_stamp_data()

    def _save_stamp_data(self):
        """スタンプデータの保存"""
        with open(self.stamp_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.stamp_data, f, ensure_ascii=False, indent=2)

    def add_stamp(self, stamp_file, category: str, tags: List[str]) -> Dict[str, Any]:
        """新しいスタンプの追加"""
        stamp_id = self._generate_stamp_id()
        filename = f"stamp_{stamp_id}.png"
        
        # スタンプファイルの保存
        stamp_file.save(os.path.join(self.stamp_folder, filename))
        
        # スタンプデータの更新
        stamp_data = {
            'id': stamp_id,
            'filename': filename,
            'category': category,
            'tags': tags
        }
        self.stamp_data['stamps'][stamp_id] = stamp_data
        
        # カテゴリの追加（存在しない場合）
        if category not in self.stamp_data['categories']:
            self.stamp_data['categories'].append(category)
        
        self._save_stamp_data()
        return stamp_data

    def get_stamps(self, category: str = None, tag: str = None) -> List[Dict[str, Any]]:
        """スタンプの取得"""
        stamps = []
        for stamp in self.stamp_data['stamps'].values():
            if category and stamp['category'] != category:
                continue
            if tag and tag not in stamp['tags']:
                continue
            stamps.append(stamp)
        return stamps

    def get_categories(self) -> List[str]:
        """スタンプカテゴリの取得"""
        return self.stamp_data['categories']

    def get_popular_stamps(self, limit: int = 10) -> List[Dict[str, Any]]:
        """人気のスタンプを取得"""
        # スタンプ使用履歴をSQLiteで集計（仮実装）
        popular_stamps = []
        for stamp_id, stamp in list(self.stamp_data['stamps'].items())[:limit]:
            stamp_copy = stamp.copy()
            stamp_copy['usage_count'] = 0
            popular_stamps.append(stamp_copy)
        
        return popular_stamps

    def search_stamps(self, query: str) -> List[Dict[str, Any]]:
        """スタンプの検索"""
        query = query.lower()
        results = []
        
        for stamp in self.stamp_data['stamps'].values():
            # タグとカテゴリで検索
            if (query in stamp['category'].lower() or
                any(query in tag.lower() for tag in stamp['tags'])):
                results.append(stamp)
        
        return results

    def record_stamp_usage(self, stamp_id: str, user_id: int):
        """スタンプの使用を記録"""
        # 簡易実装：データベースに記録
        pass

    def _generate_stamp_id(self) -> str:
        """新しいスタンプIDの生成"""
        existing_ids = set(self.stamp_data['stamps'].keys())
        stamp_id = 1
        while str(stamp_id) in existing_ids:
            stamp_id += 1
        return str(stamp_id)
