@echo off
title Campus Digital Twin - ONE CLICK DEMO LAUNCHER
echo ===================================================
echo   Campus Digital Twin Copilot -- One-Click Demo
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Ollama Local LLM Daemon...
where ollama >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Ollama CLI detected. Starting daemon...
    start "Ollama LLM Daemon" cmd /k "ollama serve"
    timeout /t 3 >nul
) else (
    echo [INFO] Ollama not found in PATH. Will run in Fallback Engine mode.
)

echo.
echo [2/4] Running Model Warmup & System Pre-Flight Checklist...
python warmup.py

echo.
echo [3/4] Starting FastAPI Backend & Frontend Servers...
start "Campus Twin Backend (Port 8000)" cmd /k "python -m app.main"
timeout /t 2 >nul

start "Campus Twin Frontend (Port 5173)" cmd /k "python -m http.server 5173 --directory frontend"
timeout /t 2 >nul

echo.
echo [4/4] Opening Demo Dashboard in Browser...
start http://127.0.0.1:5173/demo.html

echo.
echo ===================================================
echo   ALL SYSTEMS GO! DEMO IS LIVE!
echo   - Dashboard: http://127.0.0.1:5173/demo.html
echo   - REST Docs: http://127.0.0.1:8000/docs
echo ===================================================
echo.
pause
