#!/bin/bash

###############################################################################
# ARE - Render.com Build Script
# Render.comでのビルド時に実行されるスクリプト
###############################################################################

set -e

echo "========================================="
echo "ARE - Render Build Script"
echo "========================================="

# バックエンドディレクトリに移動
cd backend

# Pythonバージョン確認
echo "Python version:"
python --version

# pipのアップグレード
echo "Upgrading pip..."
pip install --upgrade pip

# 依存関係のインストール
echo "Installing dependencies..."
pip install -r requirements.txt

# 依存関係の確認
echo "Installed packages:"
pip list

echo "========================================="
echo "✅ Build completed successfully!"
echo "========================================="
