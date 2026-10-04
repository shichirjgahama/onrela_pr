@echo off
chcp 65001 >nul
title ISP ERP - Frontend
cd /d "%~dp0"

echo ============================================================
echo   Frontend (Vue + Vite) - порт 5173
echo ============================================================
echo.

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr LISTENING') do (
    echo [i] Освобождаем порт 5173 ^(PID %%p^)
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo Запуск: npm run dev
echo.
npm run dev
pause