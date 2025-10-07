"""
本番環境用エラーハンドラー
既存のabcd.pyに影響を与えずに、本番環境でのエラー処理を改善
"""

from flask import render_template, request, jsonify
import logging

def register_error_handlers(app):
    """エラーハンドラーを登録する"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        """404エラー（ページが見つからない）の処理"""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': 'リクエストされたエンドポイントが見つかりません',
                'status': 404
            }), 404
        
        try:
            return render_template('index.html'), 404
        except:
            # テンプレートが見つからない場合のフォールバック
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>TMHKchat - ページが見つかりません</title>
                <meta charset="UTF-8">
            </head>
            <body>
                <h1>ページが見つかりません</h1>
                <p>申し訳ありませんが、お探しのページは見つかりませんでした。</p>
                <a href="/">ホームページに戻る</a>
            </body>
            </html>
            ''', 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500エラー（内部サーバーエラー）の処理"""
        logging.error(f'Internal Server Error: {error}')
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': '内部サーバーエラーが発生しました',
                'status': 500
            }), 500
        
        try:
            return render_template('index.html'), 500
        except:
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>TMHKchat - サーバーエラー</title>
                <meta charset="UTF-8">
            </head>
            <body>
                <h1>サーバーエラー</h1>
                <p>申し訳ありませんが、サーバー内部でエラーが発生しました。</p>
                <a href="/">ホームページに戻る</a>
            </body>
            </html>
            ''', 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """403エラー（アクセス禁止）の処理"""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': 'アクセスが禁止されています',
                'status': 403
            }), 403
        
        try:
            return render_template('index.html'), 403
        except:
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>TMHKchat - アクセス禁止</title>
                <meta charset="UTF-8">
            </head>
            <body>
                <h1>アクセス禁止</h1>
                <p>このページにアクセスする権限がありません。</p>
                <a href="/">ホームページに戻る</a>
            </body>
            </html>
            ''', 403
    
    @app.before_request
    def before_request():
        """リクエスト前の処理"""
        # 本番環境でのプロキシヘッダー処理
        if app.config.get('PREFERRED_URL_SCHEME') == 'https':
            if request.headers.get('X-Forwarded-Proto') == 'https':
                request.environ['wsgi.url_scheme'] = 'https'
    
    @app.after_request 
    def after_request(response):
        """レスポンス後の処理"""
        # セキュリティヘッダーの追加
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # 本番環境でのCORS設定
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response