"""
デバッグ用の追加ルート
表示問題の診断に使用
"""

from flask import render_template_string

def add_debug_routes(app):
    """デバッグ用ルートを追加"""
    
    @app.route('/test')
    def test_page():
        """シンプルなテストページ"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>テスト</title>
            <style>
                body { 
                    background: #0a0a1a; 
                    color: white; 
                    font-family: Arial; 
                    padding: 20px; 
                }
                .box {
                    background: rgba(255,255,255,0.1);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>TMHKchat サーバーテスト</h1>
                <p>このページが表示されている場合、サーバーは正常に動作しています。</p>
                <p>現在時刻: <span id="time"></span></p>
                <a href="/admin" style="color: #667eea;">管理者画面に戻る</a>
            </div>
            
            <script>
                function updateTime() {
                    document.getElementById('time').textContent = new Date().toLocaleString('ja-JP');
                }
                updateTime();
                setInterval(updateTime, 1000);
                console.log('Test page loaded successfully');
            </script>
        </body>
        </html>
        """
    
    @app.route('/debug-chat')  
    def debug_chat():
        """チャット画面のデバッグ版"""
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>チャットデバッグ</title>
            <style>
                body { background: #0a0a1a; color: white; font-family: Arial; padding: 20px; }
                .debug { background: #333; padding: 15px; margin: 10px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>チャット画面デバッグ</h1>
            <div class="debug">
                <h3>変数確認:</h3>
                <p>is_admin_chat: {{ is_admin_chat }}</p>
                <p>user: {{ user }}</p>
                <p>messages count: {{ messages|length if messages else 0 }}</p>
                <p>leaderboard count: {{ leaderboard|length if leaderboard else 0 }}</p>
            </div>
            
            <div class="debug">
                <h3>基本的なチャット要素:</h3>
                <div style="border: 1px solid white; padding: 10px; margin: 10px 0;">
                    <h4>チャットヘッダー</h4>
                </div>
                <div style="border: 1px solid white; padding: 10px; margin: 10px 0; height: 200px;">
                    <h4>メッセージエリア</h4>
                    {% if messages %}
                        {% for message in messages %}
                        <div>{{ message.content }}</div>
                        {% endfor %}
                    {% else %}
                        <p>メッセージなし</p>
                    {% endif %}
                </div>
                <div style="border: 1px solid white; padding: 10px; margin: 10px 0;">
                    <input type="text" placeholder="テスト入力" style="width: 200px; padding: 5px;">
                    <button>送信</button>
                </div>
            </div>
            
            <a href="/admin" style="color: #667eea;">管理者画面に戻る</a>
        </body>
        </html>
        """, 
        is_admin_chat=False,
        user={'username': 'test', 'balance': 1000},
        messages=[],
        leaderboard=[]
        )