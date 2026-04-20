#!/bin/bash
# 一键部署到服务器 192.168.31.99
set -e

SERVER="root@192.168.31.99"
REMOTE_DIR="/app/lawfirm-prod"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 律所AI平台 — 部署开始"
echo "   服务器: $SERVER"
echo "   目录: $REMOTE_DIR"
echo ""

# 1. 确保远程目录存在
echo "📁 [1/5] 初始化远程目录..."
ssh $SERVER "mkdir -p $REMOTE_DIR/prod-data/{materials,bidding,tasks,company,uploads}"

# 2. 同步代码到服务器（排除不需要的文件）
echo "📤 [2/5] 同步代码到服务器..."
rsync -avz --delete \
    --exclude='venv/' \
    --exclude='node_modules/' \
    --exclude='platform/dist/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='prod-data/' \
    --exclude='agentic_on_arch/data/tasks/' \
    "$PROJECT_DIR/" "$SERVER:$REMOTE_DIR/"

# 3. 同步生产数据（仅首次或手动触发）
if [ "$1" == "--init-data" ]; then
    echo "📊 [2.5] 同步初始数据..."
    rsync -avz "$PROJECT_DIR/agentic_on_arch/data/materials/" "$SERVER:$REMOTE_DIR/prod-data/materials/"
    rsync -avz "$PROJECT_DIR/agentic_on_arch/data/company/" "$SERVER:$REMOTE_DIR/prod-data/company/"
    rsync -avz "$PROJECT_DIR/agentic_on_arch/.env" "$SERVER:$REMOTE_DIR/agentic_on_arch/.env"
fi

# 4. 远程构建 Docker 镜像
echo "🐳 [3/5] 构建 Docker 镜像..."
ssh $SERVER "cd $REMOTE_DIR && docker compose build"

# 5. 启动/重启服务
echo "🔄 [4/5] 启动服务..."
ssh $SERVER "cd $REMOTE_DIR && docker compose up -d"

# 6. 健康检查
echo "🏥 [5/5] 健康检查..."
sleep 5
ssh $SERVER "curl -sf http://localhost:8001/health && echo ' ✅ Backend OK' || echo ' ❌ Backend FAILED'"
ssh $SERVER "curl -sf http://localhost:80 > /dev/null && echo ' ✅ Frontend OK' || echo ' ❌ Frontend FAILED'"

echo ""
echo "✅ 部署完成!"
echo "   前端: http://192.168.31.99"
echo "   后端: http://192.168.31.99:8001"
echo "   API文档: http://192.168.31.99:8001/docs"
