@echo off

echo ============================================
echo Setting up Invoice Generator...
echo ============================================

:: -----------------------------
:: Backend Setup
:: -----------------------------
echo.
echo Setting up backend...

cd /d "%~dp0backend"

python -m venv venv

call venv\Scripts\activate

pip install --upgrade pip

pip install -r requirements.txt

:: -----------------------------
:: Frontend Setup
:: -----------------------------
echo.
echo Setting up frontend...

cd /d "%~dp0frontend"

npm install

npm run build

:: -----------------------------
:: Finished
:: -----------------------------
echo.
echo ============================================
echo Setup Complete!
echo ============================================

pause