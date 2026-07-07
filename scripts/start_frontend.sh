#!/bin/bash
# AI 智能旅游规划师 · 启动前端(macOS/Linux)
cd "$(dirname "$0")/.."

if [ -d "venv" ]; then
    source venv/bin/activate
fi

cd frontend
nohup streamlit run app.py --server.port 8501 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "前端 PID: $FRONTEND_PID"
echo "日志: logs/frontend.log"
echo "访问: http://localhost:8501"