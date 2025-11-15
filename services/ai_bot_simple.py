import os
from typing import List, Dict, Any
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("警告: google-generativeaiがインストールされていません")

from datetime import datetime

class AIBot:
    def __init__(self):
        if not GENAI_AVAILABLE:
            self.model = None
            self.chat_history = {}
            return
            
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("警告: Google AI APIキーが設定されていません")
            self.model = None
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        
        self.chat_history = {}
        
    def get_response(self, user_id: str, message: str) -> Dict[str, Any]:
        """ユーザーメッセージへの応答を生成"""
        if not self.model:
            return {
                'content': "AIボット機能は現在利用できません。Google AI APIキーを設定してください。",
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
            
        try:
            # チャット履歴の取得または作成
            if user_id not in self.chat_history:
                self.chat_history[user_id] = self.model.start_chat(history=[])
            
            chat = self.chat_history[user_id]
            
            # 応答の生成
            response = chat.send_message(message)
            
            return {
                'content': response.text,
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
        except Exception as e:
            print(f"AI response error: {e}")
            return {
                'content': "申し訳ありません。現在応答を生成できません。",
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
    
    def clear_history(self, user_id: str):
        """特定ユーザーのチャット履歴をクリア"""
        if user_id in self.chat_history:
            del self.chat_history[user_id]
    
    def get_chat_history(self, user_id: str) -> List[Dict[str, Any]]:
        """チャット履歴の取得"""
        if user_id not in self.chat_history:
            return []
        
        return []  # 簡易実装
