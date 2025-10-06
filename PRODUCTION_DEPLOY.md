# TMHKchat Server - 本番環境デプロイガイド

## 本番環境への移行手順

### 1. 環境変数の設定

```bash
# セキュリティキーの設定（必須）
export SECRET_KEY="your_super_secure_random_key_here"

# 本番環境フラグの設定
export FLASK_ENV="production"
```

### 2. abcd.py の本番環境設定

開発環境から本番環境に移行する際は、以下の行を変更してください：

```python
# 開発環境用（コメントアウト）
# socketio.run(app, debug=True, use_reloader=False)

# 本番環境用（有効化）
socketio.run(app, host='0.0.0.0', port=5000, debug=False)
```

### 3. 本番環境で無効化されている項目

- **デバッグモード**: `debug=False` に設定
- **自動リロード**: `use_reloader=False` に設定
- **詳細なエラー表示**: ログレベルがWARNINGに制限
- **セキュリティ設定**: HTTPS、XSS、CSRF対策が有効

### 4. 推奨される本番環境設定

#### セキュリティ
- HTTPSを使用する
- 強力なSECRET_KEYを設定する
- ファイアウォールでポート5000のアクセスを制限する

#### パフォーマンス
- 本番用WSGIサーバー（Gunicorn、uWSGI等）の使用を推奨
- リバースプロキシ（Nginx等）の設定
- データベースの定期バックアップ

#### 監視
- ログファイルの監視
- リソース使用量の監視
- エラー率の監視

### 5. 本番環境での起動例

```bash
# 環境変数を設定
export SECRET_KEY="$(openssl rand -base64 32)"
export FLASK_ENV="production"

# サーバーを起動
python abcd.py
```

### 6. Gunicornを使用した本番デプロイ（推奨）

```bash
# Gunicornのインストール
pip install gunicorn

# Gunicornでの起動
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 abcd:app
```

## トラブルシューティング

### よくある問題
1. **SECRET_KEYが設定されていない**: 環境変数を確認
2. **ポートが使用中**: 他のプロセスがポート5000を使用していないか確認
3. **データベースエラー**: abc.dbファイルの権限を確認

### ログの確認
本番環境では詳細なログが無効化されています。問題が発生した場合は、一時的に開発環境設定に戻してデバッグしてください。