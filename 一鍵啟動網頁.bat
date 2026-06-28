@echo off
chcp 65001 >nul
title 公開觀課紀錄自動產生系統
cd /d "%~dp0"

echo ==========================================
echo   公開觀課紀錄自動產生系統 - 一鍵啟動
echo ==========================================
echo.

echo [1/3] 檢查 Python...
py --version >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=py
) else (
    python --version >nul 2>nul
    if %errorlevel%==0 (
        set PYTHON_CMD=python
    ) else (
        echo 找不到 Python。
        echo 請先安裝 Python 3.10 以上版本，再重新執行本檔案。
        echo 下載位置：https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo [2/3] 安裝或檢查必要套件，第一次會需要比較久...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 套件安裝失敗，請檢查網路連線或 Python 環境。
    pause
    exit /b 1
)

echo [3/3] 啟動網頁...
echo.
echo 若瀏覽器沒有自動開啟，請手動輸入： http://localhost:8501
echo.
%PYTHON_CMD% -m streamlit run app.py
pause
