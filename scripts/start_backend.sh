#!/bin/bash
# ============================================================
# AI 智能旅游规划师 · 启动后端脚本(macOS/Linux)
# 使用: ./scripts/start_backend.sh
# ============================================================

cd "$(dirname "$0")/.."

echo "[1/4] 激活虚拟环境..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[警告] 未找到 venv 虚拟环境,请先运行: python -m venv venv"
fi

echo "[2/4] 检查 .env 文件..."
if [ ! -f ".env" ]; then
    echo "[警告] 未找到 .env 文件"
    echo "[自动复制 .env.example → .env]"
    cp .env.example .env
    echo "[请编辑 .env 后重新运行]"
    exit 1
fi

echo "[3/4] 启动 FastAPI 后端..."
cd backend
nohup uvicorn main:app --reload --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo "后端 PID: $BACKEND_PID"

echo "[4/4] 完成,后端日志: logs/backend.log"
echo "访问: http://localhost:8000/docs"