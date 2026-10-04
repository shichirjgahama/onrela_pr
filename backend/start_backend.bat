@echo off
chcp 65001 >nul
title ISP ERP - Backend
cd /d "%~dp0"

echo ============================================================
echo   Backend (FastAPI) - порт 8000
echo ============================================================
echo.

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr LISTENING') do (
    echo [i] Освобождаем порт 8000 ^(PID %%p^)
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo Запуск: uvicorn app.main:app --reload --port 8000
echo.
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
pause