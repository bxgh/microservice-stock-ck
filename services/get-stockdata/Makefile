# Get Stock Data 微服务 - Makefile
# 简化常用的开发和部署命令

.PHONY: help dev prod build test clean logs restart health

# 默认目标：显示帮助信息
help:
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Get Stock Data 微服务 - 开发命令"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "🔥 开发环境命令（推荐）:"
	@echo "  make dev          - 启动开发环境（支持热加载）"
	@echo "  make dev-build    - 重新构建并启动开发环境"
	@echo "  make dev-logs     - 查看开发环境日志"
	@echo "  make dev-down     - 停止开发环境"
	@echo ""
	@echo "🚀 生产环境命令:"
	@echo "  make prod         - 启动生产环境"
	@echo "  make prod-build   - 重新构建并启动生产环境"
	@echo "  make prod-logs    - 查看生产环境日志"
	@echo "  make prod-down    - 停止生产环境"
	@echo ""
	@echo "🔧 通用命令:"
	@echo "  make health       - 检查服务健康状态"
	@echo "  make test         - 运行测试"
	@echo "  make clean        - 清理容器和镜像"
	@echo "  make restart      - 重启服务"
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "💡 提示: 开发时请使用 'make dev' 启动热加载环境"
	@echo "════════════════════════════════════════════════════════════"

# ================== 开发环境命令 ==================

dev:
	@echo "🔥 启动开发环境（支持热加载）..."
	@echo "════════════════════════════════════════════════════════════"
	@echo "📝 修改代码后会自动重启（1-2秒）"
	@echo "📋 查看日志: make dev-logs"
	@echo "🛑 停止服务: make dev-down"
	@echo "════════════════════════════════════════════════════════════"
	docker compose -f docker-compose.dev.yml up

dev-build:
	@echo "🔨 重新构建开发环境..."
	docker compose -f docker-compose.dev.yml up --build

dev-bg:
	@echo "🔥 后台启动开发环境..."
	docker compose -f docker-compose.dev.yml up -d
	@echo "✅ 开发环境已在后台启动"
	@echo "📋 查看日志: make dev-logs"

dev-logs:
	@echo "📋 开发环境日志（Ctrl+C 退出）..."
	docker compose -f docker-compose.dev.yml logs -f

dev-down:
	@echo "🛑 停止开发环境..."
	docker compose -f docker-compose.dev.yml down

dev-restart:
	@echo "🔄 重启开发环境..."
	docker compose -f docker-compose.dev.yml restart

# ================== 生产环境命令 ==================

prod:
	@echo "🚀 启动生产环境..."
	docker compose up -d
	@echo "✅ 生产环境已启动"
	@echo "📋 查看日志: make prod-logs"

prod-build:
	@echo "🔨 重新构建生产环境..."
	docker compose up --build -d

prod-logs:
	@echo "📋 生产环境日志（Ctrl+C 退出）..."
	docker compose logs -f

prod-down:
	@echo "🛑 停止生产环境..."
	docker compose down

prod-restart:
	@echo "🔄 重启生产环境..."
	docker compose restart

# ================== 通用命令 ==================

health:
	@echo "🏥 检查服务健康状态..."
	@curl -s http://localhost:8086/api/v1/health | python3 -m json.tool || echo "❌ 服务未运行或无法访问"

test:
	@echo "🧪 运行测试..."
	@echo "TODO: 添加测试命令"

clean:
	@echo "🧹 清理容器和镜像..."
	docker compose -f docker-compose.dev.yml down -v
	docker compose down -v
	@echo "✅ 清理完成"

restart: dev-restart

# ================== 便捷命令 ==================

# 快速启动（默认开发环境）
start: dev-bg

# 快速停止
stop: dev-down

# 查看状态
status:
	@echo "📊 容器状态:"
	@docker ps --filter "name=get-stockdata" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 进入容器
shell:
	@echo "🐚 进入开发容器..."
	docker exec -it get-stockdata-api-dev /bin/bash

# 查看最新日志
tail:
	docker compose -f docker-compose.dev.yml logs --tail 50

# ================== 快捷别名 ==================

up: dev
down: dev-down
log: dev-logs
ps: status
