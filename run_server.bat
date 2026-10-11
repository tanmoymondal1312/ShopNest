@echo off
setlocal
title ShopNest
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PORT=8000"
set "VENV=venv"
set "SITE=http://localhost:%PORT%"

echo ==================================================
echo   ShopNest - starting local server
echo ==================================================
echo.

REM ---- 1. Find Python 3 --------------------------------------------------
set "PY="
python --version >nul 2>nul
if not errorlevel 1 set "PY=python"
if not defined PY (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    echo [ERROR] Python 3 was not found on this computer.
    echo.
    echo         Install it from https://www.python.org/downloads/
    echo         and tick "Add python.exe to PATH" in the installer.
    echo.
    pause
    exit /b 1
)

REM ---- 2. Create virtual environment (first run only) --------------------
if not exist "%VENV%\Scripts\python.exe" (
    echo Creating virtual environment in .\%VENV% ...
    %PY% -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
    echo.
)
set "VPY=%VENV%\Scripts\python.exe"

REM ---- 3. Install packages (only when something is missing) --------------
"%VPY%" -c "import importlib.util as u,sys;m=['fastapi','uvicorn','jinja2','aiosqlite','PIL','dotenv','itsdangerous','watchfiles'];ok=all(u.find_spec(x) for x in m) and bool(u.find_spec('multipart') or u.find_spec('python_multipart'));sys.exit(0 if ok else 1)"
if errorlevel 1 (
    echo Installing dependencies from requirements.txt ...
    "%VPY%" -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. Check your internet connection.
        echo.
        pause
        exit /b 1
    )
    echo.
)

REM ---- 4. Database: local SQLite file - no external setup needed ---------
if not exist "shop.db" (
    echo Creating database shop.db with sample products ...
    "%VPY%" seed.py
    echo.
)

REM ---- 5. Open the site in the browser a few seconds after start ---------
if not "%SHOPNEST_NO_BROWSER%"=="1" if exist "%VENV%\Scripts\pythonw.exe" (
    start "" "%VENV%\Scripts\pythonw.exe" -c "import time,webbrowser;time.sleep(4);webbrowser.open('%SITE%')"
)

REM ---- 6. Run the server --------------------------------------------------
echo --------------------------------------------------
echo   Site : %SITE%
echo   Admin: %SITE%/admin/login
echo   Stop : press Ctrl+C in this window
echo --------------------------------------------------
echo.

"%VPY%" -m uvicorn main:app --reload --port %PORT%

echo.
if errorlevel 1 (
    echo [ERROR] The server stopped with an error - see message above.
) else (
    echo Server stopped.
)
echo.
pause
exit /b 0
