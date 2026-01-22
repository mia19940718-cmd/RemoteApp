@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo       PyRemoteControl Server Launcher
echo ==========================================
echo.

REM Try to find the virtual environment
set "VENV_PATH=..\PyRemoteControl\venv\Scripts\python.exe"
set "VENV_PATH_OLD=..\venv\Scripts\python.exe"

if exist "%VENV_PATH%" (
    echo [INFO] Found environment at: %VENV_PATH%
    "%VENV_PATH%" pc_server.py
) else if exist "%VENV_PATH_OLD%" (
    echo [INFO] Found environment at: %VENV_PATH_OLD%
    "%VENV_PATH_OLD%" pc_server.py
) else (
    echo [WARN] Virtual environment not found.
    echo [INFO] Trying system Python...
    python pc_server.py
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The program crashed or failed to start.
    echo Please check the error message above.
)

echo.
echo Press any key to exit...
pause >nul
