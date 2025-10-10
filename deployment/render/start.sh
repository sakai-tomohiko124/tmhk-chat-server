#!/bin/bash

###############################################################################
# ARE - Render.com Start Script
# Render.comでのアプリ起動スクリプト
###############################################################################

set -e

echo "========================================="
echo "ARE - Starting Server on Render"
echo "========================================="

# バックエンドディレクトリに移動
cd backend

# 環境変数の確認（デバッグ用、本番では削除推奨）
echo "Environment:"
echo "  FLASK_ENV: $FLASK_ENV"
echo "  PORT: $PORT"
echo "  DATABASE_URL: ${DATABASE_URL:0:30}..." # 最初の30文字のみ表示

# データベースマイグレーション
echo "Running database migrations..."
export FLASK_APP=wsgi.py
flask db upgrade || echo "⚠️  Migration failed or no migrations to apply"

# Gunicornでアプリ起動
echo "Starting Gunicorn server..."
echo "========================================="
gunicorn -c gunicorn_config.py wsgi:app
