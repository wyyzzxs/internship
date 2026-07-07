@echo off
chcp 65001 > nul
REM ============================================================
REM  AI 智能旅游规划师 · 启动后端脚本(Windows)
REM  使用: 双击运行 或 在项目根目录执行 .\scripts\start_backend.bat
REM ============================================================

REM 切到项目根目录(脚本所在目录的父目录)
cd /d %~dp0\..

echo [1/4] 激活虚拟环境...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [警告] 未找到 venv 虚拟环境,请先运行: python -m venv venv
    echo [警告] 继续尝试用系统 Python 运行
)

echo [2/4] 检查 .env 文件...
if not exist .env (
    echo [警告] 未找到 .env 文件
    echo [警告] 请复制 .env.example 为 .env 并填入 Key
    copy .env.example .env
    echo [已自动复制 .env.example → .env,请编辑后重新运行]
    pause
    exit /b 1
)

echo [3/4] 启动 FastAPI 后端(端口 8000)...
cd backend
start "AI-Travel-Backend" cmd /k "uvicorn main:app --reload --port 8000"
cd ..

echo [4/4] 等待 3 秒,后端启动完成...
timeout /t 3 /nobreak > nul

echo.
echo ============================================================
echo  后端已启动: http://localhost:8000
echo  Swagger 文档: http://localhost:8000/docs
echo  下一步: 另开终端运行 .\scripts\start_frontend.bat
echo ============================================================
echo.
pause