@echo off

echo Starting Invoice Generator...

:: -----------------------------
:: Start Backend
:: -----------------------------
cd /d "%~dp0backend"

start cmd /k "venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:: -----------------------------
:: Wait for backend
:: -----------------------------
timeout /t 5 /nobreak > nul

:: -----------------------------
:: Start Frontend
:: -----------------------------
cd /d "%~dp0frontend"

start cmd /k "npm start"

:: -----------------------------
:: Wait and Open Browser
:: -----------------------------
timeout /t 8 /nobreak > nul

start http://localhost:3000

exit