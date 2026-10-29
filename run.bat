@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set API_PORT=8000
set WEB_PORT=3000

echo ============================================
echo  INT396 - Sensor Fault Classifier Dashboard
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js / npm not found in PATH.
    pause
    exit /b 1
)

if not exist "backend\results\metrics.json" (
    echo [1/4] Results missing. Generating data and training the model, this takes a few minutes...
    pushd backend
    python -m pip install -r requirements.txt
    if errorlevel 1 goto failed
    python generate_data.py
    if errorlevel 1 goto failed
    python model.py
    if errorlevel 1 goto failed
    popd
) else (
    echo [1/4] Results found, skipping pipeline.
)

if not exist "frontend\node_modules" (
    echo [2/4] Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 goto failed
    popd
) else (
    echo [2/4] Frontend dependencies present.
)

echo Checking port %API_PORT% ...
netstat -ano | findstr /R /C:"LISTENING" | findstr /C:":%API_PORT% " >nul
if not errorlevel 1 (
    echo     port %API_PORT% is busy, using 8010
    set API_PORT=8010
)

echo Clearing any stale Next.js dev server for this directory...
if exist "frontend\.next\dev\lock" (
    for /f "tokens=2 delims=:" %%P in ('type "frontend\.next\dev\lock" 2^>nul ^| findstr /R "[0-9]"') do (
        taskkill /PID %%P /F >nul 2>nul
    )
    del /q "frontend\.next\dev\lock" >nul 2>nul
)

echo Checking port %WEB_PORT% ...
netstat -ano | findstr /R /C:"LISTENING" | findstr /C:":%WEB_PORT% " >nul
if not errorlevel 1 (
    echo     port %WEB_PORT% is busy, using 3010
    set WEB_PORT=3010
)

echo [3/4] Starting API on http://127.0.0.1:%API_PORT% ...
start "INT396 API" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 127.0.0.1 --port %API_PORT%"

echo [4/4] Starting dashboard on http://localhost:%WEB_PORT% ...
set "NEXT_PUBLIC_API_URL=http://127.0.0.1:%API_PORT%"
start "INT396 Dashboard" cmd /k "cd /d %~dp0frontend && npx next dev --port %WEB_PORT%"

echo Waiting for both servers...
timeout /t 14 /nobreak >nul
start "" http://localhost:%WEB_PORT%

echo.
echo   API : http://127.0.0.1:%API_PORT%
echo   App : http://localhost:%WEB_PORT%
echo.
echo Close the two server windows to stop the demo.
echo.
pause
exit /b 0

:failed
echo.
echo [ERROR] Setup failed. Fix the error above and run this file again.
pause
exit /b 1
