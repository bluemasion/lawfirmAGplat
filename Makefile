.PHONY: dev build deploy release status logs stop clean

SERVER = root@192.168.31.99
REMOTE_DIR = /app/lawfirm-prod

# ── 开发 ──
dev:
	@echo "🔧 启动开发环境..."
	@cd agentic_on_arch && source venv/bin/activate && python3.8 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
	@export NVM_DIR="$$HOME/.nvm" && [ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh" && cd platform && npx --yes vite --port 5173 --host 0.0.0.0

# ── 构建 ──
build:
	@echo "📦 前端打包..."
	@export NVM_DIR="$$HOME/.nvm" && [ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh" && cd platform && npm run build
	@echo "✅ 打包完成: platform/dist/"

# ── 部署 ──
deploy:
	@bash scripts/deploy.sh

deploy-init:
	@bash scripts/deploy.sh --init-data

# ── 发布 ──
release:
	@if [ -z "$(v)" ]; then echo "用法: make release v=3.1.0"; exit 1; fi
	@echo "🏷️  发布 v$(v)..."
	@git add -A && git commit -m "release: v$(v)" || true
	@git tag -a v$(v) -m "Release v$(v)"
	@bash scripts/deploy.sh
	@echo "✅ v$(v) 发布完成"

# ── 运维 ──
status:
	@ssh $(SERVER) "cd $(REMOTE_DIR) && docker compose ps"

logs:
	@ssh $(SERVER) "cd $(REMOTE_DIR) && docker compose logs --tail=50 -f"

logs-api:
	@ssh $(SERVER) "cd $(REMOTE_DIR) && docker compose logs --tail=100 -f backend"

logs-web:
	@ssh $(SERVER) "cd $(REMOTE_DIR) && docker compose logs --tail=100 -f frontend"

stop:
	@ssh $(SERVER) "cd $(REMOTE_DIR) && docker compose stop"

restart:
	@ssh $(SERVER) "cd $(REMOTE_DIR) && docker compose restart"

clean:
	@ssh $(SERVER) "cd $(REMOTE_DIR) && docker compose down && docker image prune -f"
