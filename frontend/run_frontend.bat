@echo off
title Campus Digital Twin Launcher
echo ===================================================
echo   Campus Digital Twin Copilot Launcher
echo ===================================================
echo.

cd /d "%~dp0.."

echo [1/3] Starting Python FastAPI Backend Server on http://127.0.0.1:8000 ...
start "Campus Twin FastAPI Backend" cmd /k "python -m app.main"

timeout /t 2 >nul

echo [2/3] Starting Frontend Web Server on http://127.0.0.1:5173 ...
start "Campus Twin Frontend Server" cmd /k "python -m http.server 5173 --directory frontend"

timeout /t 2 >nul

echo [3/3] Opening Dashboard in Default Browser...
start http://127.0.0.1:5173/demo.html

echo.
echo ===================================================
echo   Both servers are running!
echo   - Frontend: http://127.0.0.1:5173/demo.html
echo   - Backend Docs: http://127.0.0.1:8000/docs
echo ===================================================
echo.
pause
