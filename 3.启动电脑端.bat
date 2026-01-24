@echo off
cd /d "%~dp0"
echo 正在启动服务端...
echo -----------------------------------

if exist "..\venv\Scripts\python.exe" (
    "..\venv\Scripts\python.exe" main.py
) else (
    echo 未找到虚拟环境，尝试使用系统 Python...
    python main.py
)

if %errorlevel% neq 0 (
    echo.
    echo 启动失败！请检查报错信息。
    pause
) else (
    echo.
    echo 程序已退出。
    pause
)
