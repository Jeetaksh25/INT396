@echo off
setlocal
cd /d "%~dp0"

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
    echo [1/5] Results missing. Building dataset and running the experiment...
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
    popd
) else (
    echo [1/5] Results found, skipping pipeline run.
)

if not exist "frontend\node_modules" (
    echo [2/5] Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 goto failed
    popd
) else (
    echo [2/5] Frontend dependencies present.
)

echo [3/5] Starting API on http://127.0.0.1:8000 ...
start "INT396 API" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo [4/5] Starting dashboard on http://localhost:3000 ...
start "INT396 Dashboard" cmd /k "cd /d %~dp0frontend && npm run dev"

echo [5/5] Waiting for servers, then opening the browser...
timeout /t 12 /nobreak >nul
start "" http://localhost:3000

echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the demo.
echo.
pause
exit /b 0

:failed
echo.
echo [ERROR] Setup failed. Fix the error above and run this file again.
pause
exit /b 1
