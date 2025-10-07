"""
405 Method Not Allowed エラー対策
既存のabcd.pyを変更せずに、chat.htmlからのPOSTリクエストを処理するためのパッチ
"""

from flask import request, redirect, url_for, flash

def setup_method_fixes(app):
    """405エラーを回避するためのルート修正"""
    
    @app.route('/chat', methods=['GET', 'POST'])
    def chat_fixed():
        """修正版チャットルート（GETとPOSTの両方をサポート）"""
        if request.method == 'POST':
            # POSTリクエストの場合はGETにリダイレクト
            # これにより405エラーを回避
            return redirect(url_for('chat'))
        
        # 元のchat関数を呼び出し
        from abcd import chat as original_chat
        return original_chat()
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """405エラーの処理"""
        # POSTリクエストの場合はGETにリダイレクト
        if request.method == 'POST':
            path = request.path
            if path == '/chat':
                return redirect(url_for('chat'))
            elif path.startswith('/admin/chat/'):
                # 管理者チャットの場合
                user_id = path.split('/')[-1]
                try:
                    user_id = int(user_id)
                    return redirect(url_for('admin_chat', user_id=user_id))
                except ValueError:
                    pass
        
        # その他の場合は通常のエラー処理
        return redirect(url_for('index')), 405