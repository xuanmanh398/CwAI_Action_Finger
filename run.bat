@echo off
title Hand Gesture Computer Controller
cd /d "%~dp0"

echo ========================================================
echo   KHOI CHAY PHAN MEM DIEU KHIEN MAY TINH BANG CU CHI TAY
echo ========================================================
echo.

:: Kiem tra Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thấy Python trong he thong!
    echo Vui long cai dat Python 3.10 tro len va tich chon "Add Python to PATH".
    pause
    exit /b
)

echo [INFO] Dang khoi chay ung dung Hand Gesture Controller...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [LOI] Ung dung da dung lai voi ma loi %errorlevel%.
    pause
)
