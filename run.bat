@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set API_PORT=8000
set WEB_PORT=3000

echo ============================================
echo  INT396 - Sensor Fault Discovery Dashboard
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

if not exist "backend\results\metrics_summary.json" (
    echo [1/4] Results missing. Building the full pipeline, this takes a few minutes...
    pushd backend
    python -m pip install -r requirements.txt
    if errorlevel 1 goto failed
    if not exist "data\raw\DEL.csv" (
        python -m src.acquisition.fetch_open_meteo
        if errorlevel 1 goto failed
    )
    python -m src.acquisition.build_dataset
    if errorlevel 1 goto failed
    python -m src.simulation.build_simulation
    if errorlevel 1 goto failed
    python -m src.evaluation.run_experiment
    if errorlevel 1 goto failed
    python -m src.evaluation.export_rules
    python -m src.evaluation.generate_figures
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

echo Checking port %WEB_PORT% ...
netstat -ano | findstr /R /C:"LISTENING" | findstr /C:":%WEB_PORT% " >nul
if not errorlevel 1 (
    echo     port %WEB_PORT% is busy, using 3010
    set WEB_PORT=3010
)

echo [3/4] Starting API on http://127.0.0.1:%API_PORT% ...
start "INT396 API" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 127.0.0.1 --port %API_PORT%"

echo [4/4] Starting dashboard on http://localhost:%WEB_PORT% ...
start "INT396 Dashboard" cmd /k "cd /d %~dp0frontend && set NEXT_PUBLIC_API_URL=http://127.0.0.1:%API_PORT% && npx next dev -p %WEB_PORT%"

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
