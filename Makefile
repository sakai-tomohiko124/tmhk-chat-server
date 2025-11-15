# Makefile - TMHKchat 開発用タスクランナー

.PHONY: help setup install dev test clean deploy backup

# デフォルトターゲット
.DEFAULT_GOAL := help

# カラー出力
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help: ## このヘルプメッセージを表示
	@echo "========================================="
	@echo "  TMHKchat Makefile"
	@echo "========================================="
	@echo ""
	@echo "使用可能なコマンド:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

setup: ## 開発環境をセットアップ（初回のみ）
	@echo "$(YELLOW)開発環境をセットアップ中...$(NC)"
	@chmod +x setup.sh
	@./setup.sh

install: ## 依存パッケージをインストール
	@echo "$(YELLOW)依存パッケージをインストール中...$(NC)"
	@. venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)✓ インストール完了$(NC)"

dev: ## 開発サーバーを起動
	@echo "$(YELLOW)開発サーバーを起動中...$(NC)"
	@. venv/bin/activate && python app.py

run: dev ## 開発サーバーを起動（devのエイリアス）

test: ## テストを実行
	@echo "$(YELLOW)テストを実行中...$(NC)"
	@. venv/bin/activate && python scripts/test_endpoints.py

test-db: ## データベースをテスト
	@echo "$(YELLOW)データベースをテスト中...$(NC)"
	@. venv/bin/activate && python scripts/check_db.py

create-admin: ## 管理者アカウントを作成
	@echo "$(YELLOW)管理者アカウントを作成中...$(NC)"
	@. venv/bin/activate && python scripts/create_admin.py

clean: ## 一時ファイルとキャッシュを削除
	@echo "$(YELLOW)クリーンアップ中...$(NC)"
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
	@find . -type f -name '*.log' -delete
	@find . -type f -name '.DS_Store' -delete
	@echo "$(GREEN)✓ クリーンアップ完了$(NC)"

clean-all: clean ## すべての生成ファイルを削除（venv, db含む）
	@echo "$(YELLOW)すべてのファイルを削除中...$(NC)"
	@rm -rf venv/
	@rm -f chat.db
	@rm -f *.log
	@echo "$(GREEN)✓ すべて削除完了$(NC)"

deploy: ## 本番環境にデプロイ（要SSH設定）
	@echo "$(YELLOW)本番環境にデプロイ中...$(NC)"
	@chmod +x deploy.sh
	@./deploy.sh

backup: ## データベースをバックアップ
	@echo "$(YELLOW)バックアップを作成中...$(NC)"
	@chmod +x backup.sh
	@./backup.sh

db-reset: ## データベースをリセット（警告: データが失われます）
	@echo "$(YELLOW)警告: データベースをリセットします$(NC)"
	@read -p "続行しますか? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f chat.db; \
		. venv/bin/activate && python -c "from app import init_db; init_db()"; \
		echo "$(GREEN)✓ データベースをリセットしました$(NC)"; \
	else \
		echo "キャンセルしました"; \
	fi

lint: ## コードをリント（flake8）
	@echo "$(YELLOW)コードをリント中...$(NC)"
	@. venv/bin/activate && flake8 app.py services/ --max-line-length=120 || echo "$(YELLOW)flake8がインストールされていません$(NC)"

format: ## コードをフォーマット（black）
	@echo "$(YELLOW)コードをフォーマット中...$(NC)"
	@. venv/bin/activate && black app.py services/ || echo "$(YELLOW)blackがインストールされていません$(NC)"

requirements: ## requirements.txtを更新
	@echo "$(YELLOW)requirements.txtを更新中...$(NC)"
	@. venv/bin/activate && pip freeze > requirements.txt
	@echo "$(GREEN)✓ requirements.txtを更新しました$(NC)"

logs: ## PM2のログを表示（本番環境）
	@pm2 logs tmhk-chat

status: ## PM2のステータスを表示（本番環境）
	@pm2 status

restart: ## アプリケーションを再起動（本番環境）
	@echo "$(YELLOW)アプリケーションを再起動中...$(NC)"
	@pm2 restart tmhk-chat
	@echo "$(GREEN)✓ 再起動完了$(NC)"

git-commit: ## 変更をコミット（インタラクティブ）
	@echo "$(YELLOW)変更をコミット中...$(NC)"
	@git status
	@echo ""
	@read -p "コミットメッセージ: " msg; \
	git add .; \
	git commit -m "$$msg"; \
	echo "$(GREEN)✓ コミット完了$(NC)"

git-push: ## 変更をGitHubにプッシュ
	@echo "$(YELLOW)GitHubにプッシュ中...$(NC)"
	@git push origin main
	@echo "$(GREEN)✓ プッシュ完了$(NC)"

update: ## GitHubから最新コードを取得
	@echo "$(YELLOW)最新コードを取得中...$(NC)"
	@git pull origin main
	@. venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)✓ 更新完了$(NC)"

init-db: ## データベースを初期化
	@echo "$(YELLOW)データベースを初期化中...$(NC)"
	@. venv/bin/activate && python -c "from app import init_db; init_db()"
	@echo "$(GREEN)✓ データベースを初期化しました$(NC)"

# 本番環境デプロイ関連
aws-start: ## AWS EC2インスタンスを起動
	@echo "$(YELLOW)AWS EC2インスタンスを起動中...$(NC)"
	@chmod +x scripts/aws_instance.sh
	@bash scripts/aws_instance.sh start

aws-stop: ## AWS EC2インスタンスを停止
	@echo "$(YELLOW)AWS EC2インスタンスを停止中...$(NC)"
	@chmod +x scripts/aws_instance.sh
	@bash scripts/aws_instance.sh stop

aws-status: ## AWS EC2インスタンスの状態確認
	@chmod +x scripts/aws_instance.sh
	@bash scripts/aws_instance.sh status

aws-ip: ## AWS EC2インスタンスのIPアドレスを取得
	@chmod +x scripts/aws_instance.sh
	@bash scripts/aws_instance.sh ip

setup-noip: ## No-IP Dynamic DNSをセットアップ（サーバー上で実行）
	@echo "$(YELLOW)No-IPをセットアップ中...$(NC)"
	@echo "$(YELLOW)注意: このコマンドはサーバー上で実行してください$(NC)"
	@chmod +x scripts/setup_noip.sh
	@sudo bash scripts/setup_noip.sh

pm2-start: ## PM2でアプリケーションを起動
	@echo "$(YELLOW)PM2でアプリケーションを起動中...$(NC)"
	@pm2 start ecosystem.config.js --env production
	@echo "$(GREEN)✓ アプリケーションを起動しました$(NC)"

pm2-stop: ## PM2でアプリケーションを停止
	@echo "$(YELLOW)PM2でアプリケーションを停止中...$(NC)"
	@pm2 stop tmhk-chat
	@echo "$(GREEN)✓ アプリケーションを停止しました$(NC)"

pm2-restart: ## PM2でアプリケーションを再起動
	@echo "$(YELLOW)PM2でアプリケーションを再起動中...$(NC)"
	@pm2 restart tmhk-chat
	@echo "$(GREEN)✓ アプリケーションを再起動しました$(NC)"

pm2-logs: ## PM2のログを表示
	@pm2 logs tmhk-chat

pm2-monit: ## PM2のリアルタイム監視
	@pm2 monit

deploy-full: ## フルデプロイ（git push + サーバー更新 + PM2再起動）
	@echo "$(YELLOW)フルデプロイを開始します...$(NC)"
	@echo ""
	@echo "Step 1: GitHubにプッシュ"
	@git add .
	@read -p "コミットメッセージ: " msg; \
	git commit -m "$$msg" || echo "変更なし"; \
	git push origin main
	@echo "$(GREEN)✓ GitHubへのプッシュ完了$(NC)"
	@echo ""
	@echo "Step 2: サーバーでデプロイスクリプトを実行してください"
	@echo "  ssh -i tmhk-chat.pem ubuntu@52.69.241.31"
	@echo "  cd /home/ubuntu/tmhk-chat-server"
	@echo "  bash deploy.sh"
	@echo ""
