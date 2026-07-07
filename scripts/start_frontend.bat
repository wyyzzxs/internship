@echo off
chcp 65001 > nul
REM ============================================================
REM  AI 智能旅游规划师 · 启动前端脚本(Windows)
REM  使用: 在项目根目录执行 .\scripts\start_frontend.bat
REM ============================================================

cd /d %~dp0\..

echo [1/3] 激活虚拟环境...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [警告] 未找到 venv 虚拟环境
)

echo [2/3] 启动 Streamlit 前端(端口 8501)...
cd frontend
start "AI-Travel-Frontend" cmd /k "streamlit run app.py --server.port 8501"
cd ..

echo [3/3] 等待 3 秒,前端启动完成...
timeout /t 3 /nobreak > nul

echo.
echo ============================================================
echo  前端已启动: http://localhost:8501
echo  浏览器会自动打开,如未打开请手动访问
echo  后端启动命令: .\scripts\start_backend.bat
echo ============================================================
echo.
pause