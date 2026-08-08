@echo off
title Campus Digital Twin Backend (FastAPI)
echo ===================================================
echo   Campus Digital Twin - FastAPI Backend Server
echo ===================================================
echo.

cd /d "%~dp0"

echo Starting Python FastAPI Server (app.main)...
echo Server will be live at: http://127.0.0.1:8000
echo Swagger API Docs at:   http://127.0.0.1:8000/docs
echo.

python -m app.main

pause
