@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo       正在修复运行环境 (Fixing Environment)...
echo ==========================================
echo.

set "VENV_PYTHON=..\PyRemoteControl\venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    echo [INFO] Found environment, installing dependencies...
    "%VENV_PYTHON%" -m pip install kivy[base] PyQt6 -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    echo [WARN] Virtual environment not found!
    echo [INFO] Installing to system Python...
    pip install kivy[base] PyQt6 -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ==========================================
echo       修复完成！(Fix Completed)
echo ==========================================
echo.
echo 现在请重新运行 "3.启动电脑端.bat"
pause
