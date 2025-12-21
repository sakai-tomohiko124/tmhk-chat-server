import os
from typing import List, Dict, Any
import google.generativeai as genai
from datetime import datetime

class AIBot:
    def __init__(self):
        api_key = os.getenv('GOOGLE_AI_API_KEY')
        if not api_key:
            raise ValueError("Google AI APIキーが設定されていません")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat_history = {}
        
    async def get_response(self, user_id: str, message: str) -> Dict[str, Any]:
        """ユーザーメッセージへの応答を生成"""
        try:
            # チャット履歴の取得または作成
            if user_id not in self.chat_history:
                self.chat_history[user_id] = self.model.start_chat(history=[])
            
            chat = self.chat_history[user_id]
            
            # 応答の生成
            response = await chat.send_message_async(message)
            
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
        
        chat = self.chat_history[user_id]
        history = []
        
        for message in chat.history:
            history.append({
                'role': 'user' if message.role == 'user' else 'assistant',
                'content': message.parts[0].text,
                'timestamp': message.timestamp.isoformat() if hasattr(message, 'timestamp') and message.timestamp else None
            })
        
        return history
    
    async def analyze_sentiment(self, message: str) -> Dict[str, Any]:
        """メッセージの感情分析"""
        try:
            prompt = f"""
            以下のメッセージの感情を分析してください：
            {message}
            
            以下の形式でJSON形式で返してください：
            {{
                "sentiment": "positive/negative/neutral",
                "score": 0-1の値,
                "emotions": ["感情1", "感情2"]
            }}
            """
            
            response = await self.model.generate_content_async(prompt)
            return eval(response.text)
            
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return {
                'sentiment': 'neutral',
                'score': 0.5,
                'emotions': []
            }
    
    async def get_conversation_suggestions(self, context: str) -> List[str]:
        """会話の提案を生成"""
        try:
            prompt = f"""
            以下の文脈に基づいて、自然な会話の続きとして適切な3つの短い応答を提案してください：
            {context}
            
            応答はカンマ区切りで、シンプルに返してください。
            """
            
            response = await self.model.generate_content_async(prompt)
            suggestions = [s.strip() for s in response.text.split(',')]
            return suggestions[:3]  # 最大3つの提案を返す
            
        except Exception as e:
            print(f"Suggestion generation error: {e}")
            return ["はい、そうですね", "なるほど", "それは面白いですね"]

    async def moderate_content(self, content: str) -> Dict[str, Any]:
        """コンテンツのモデレーション"""
        try:
            prompt = f"""
            以下のコンテンツを分析し、不適切な内容が含まれているか判断してください：
            {content}
            
            以下の形式でJSON形式で返してください：
            {{
                "is_appropriate": true/false,
                "reason": "不適切と判断した場合の理由",
                "severity": "low/medium/high"
            }}
            """
            
            response = await self.model.generate_content_async(prompt)
            return eval(response.text)
            
        except Exception as e:
            print(f"Content moderation error: {e}")
            return {
                'is_appropriate': True,
                'reason': None,
                'severity': 'low'
            }
