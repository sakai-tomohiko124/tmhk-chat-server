"""
本番環境用健全性チェックスクリプト
サーバーの動作状況を確認し、問題を早期発見するためのツール
"""

import requests
import sqlite3
import os
import sys
import json
from datetime import datetime

def check_database():
    """データベースの健全性をチェック"""
    try:
        conn = sqlite3.connect('abc.db')
        cursor = conn.cursor()
        
        # テーブルの存在確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        expected_tables = ['users', 'messages']
        existing_tables = [table[0] for table in tables]
        
        for table in expected_tables:
            if table not in existing_tables:
                return False, f"テーブル '{table}' が見つかりません"
        
        # データの基本確認
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        conn.close()
        
        return True, f"データベース正常 (ユーザー: {user_count}, メッセージ: {message_count})"
        
    except Exception as e:
        return False, f"データベースエラー: {str(e)}"

def check_server_response(host='localhost', port=5000):
    """サーバーの応答をチェック"""
    try:
        # ルートページの確認
        response = requests.get(f'http://{host}:{port}/', timeout=10)
        if response.status_code == 200:
            return True, f"サーバー応答正常 (ステータス: {response.status_code})"
        else:
            return False, f"サーバー応答異常 (ステータス: {response.status_code})"
            
    except requests.exceptions.ConnectionError:
        return False, "サーバーに接続できません"
    except requests.exceptions.Timeout:
        return False, "サーバー応答がタイムアウトしました"
    except Exception as e:
        return False, f"サーバーチェックエラー: {str(e)}"

def check_api_endpoints(host='localhost', port=5000):
    """APIエンドポイントの確認"""
    endpoints = [
        '/api/weather',
        '/api/train_delay'
    ]
    
    results = []
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'http://{host}:{port}{endpoint}', timeout=10)
            if response.status_code == 200:
                results.append(f"✓ {endpoint}: 正常")
            else:
                results.append(f"✗ {endpoint}: ステータス {response.status_code}")
        except Exception as e:
            results.append(f"✗ {endpoint}: エラー - {str(e)}")
    
    return results

def check_static_files():
    """静的ファイルの存在確認"""
    required_templates = [
        'templates/index.html',
        'templates/chat.html',
        'templates/admin.html',
        'templates/login.html',
        'templates/register.html'
    ]
    
    missing_files = []
    
    for template in required_templates:
        if not os.path.exists(template):
            missing_files.append(template)
    
    if missing_files:
        return False, f"欠落ファイル: {', '.join(missing_files)}"
    else:
        return True, "すべてのテンプレートファイルが存在します"

def check_environment():
    """環境設定の確認"""
    checks = []
    
    # 環境変数の確認
    env_vars = ['SECRET_KEY', 'FLASK_ENV']
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            if var == 'SECRET_KEY':
                checks.append(f"✓ {var}: 設定済み (長さ: {len(value)})")
            else:
                checks.append(f"✓ {var}: {value}")
        else:
            checks.append(f"⚠ {var}: 未設定")
    
    # ファイル権限の確認
    if os.path.exists('abc.db'):
        checks.append("✓ データベースファイル: 存在")
    else:
        checks.append("⚠ データベースファイル: 存在しません")
    
    return checks

def main():
    """メインの健全性チェック実行"""
    print("="*50)
    print("TMHKchat Server 健全性チェック")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # 環境確認
    print("\n1. 環境設定の確認:")
    env_checks = check_environment()
    for check in env_checks:
        print(f"  {check}")
    
    # データベース確認
    print("\n2. データベースの確認:")
    db_ok, db_msg = check_database()
    print(f"  {'✓' if db_ok else '✗'} {db_msg}")
    
    # 静的ファイル確認
    print("\n3. テンプレートファイルの確認:")
    files_ok, files_msg = check_static_files()
    print(f"  {'✓' if files_ok else '✗'} {files_msg}")
    
    # サーバー応答確認
    print("\n4. サーバー応答の確認:")
    
    # 環境変数からホストとポートを取得
    host = os.environ.get('HOST', 'localhost')
    port = int(os.environ.get('PORT', 5000))
    
    server_ok, server_msg = check_server_response(host, port)
    print(f"  {'✓' if server_ok else '✗'} {server_msg}")
    
    if server_ok:
        print("\n5. APIエンドポイントの確認:")
        api_results = check_api_endpoints(host, port)
        for result in api_results:
            print(f"  {result}")
    
    # 総合判定
    print("\n" + "="*50)
    all_ok = db_ok and files_ok and server_ok
    status = "正常" if all_ok else "問題あり"
    print(f"総合ステータス: {status}")
    print("="*50)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)