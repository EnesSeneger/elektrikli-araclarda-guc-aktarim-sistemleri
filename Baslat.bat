@echo off
rem Elektrikli Arac Modeli (MKTS 5081 EV modeli) - web arayuzunu tek tikla baslatir.
rem Ilk calistirmada sanal ortami (.venv) kurar; sonra tarayicida http://localhost:8501 acilir.
rem Kapatmak icin bu pencereyi kapatin (veya Ctrl+C).
chcp 65001 >nul
title Elektrikli Arac Modeli - arayuz
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Sanal ortam kuruluyor: .venv
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo HATA: Python bulunamadi. https://www.python.org adresinden Python 3.12+ kurun
        echo ve kurulumda "Add python.exe to PATH" kutusunu isaretleyin.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import streamlit, plotly, scipy, openpyxl, pandas, matplotlib" 2>nul
if errorlevel 1 (
    echo [2/2] Kutuphaneler kuruluyor - yalnizca ilk seferde, birkac dakika surebilir
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo HATA: kutuphaneler kurulamadi. Internet baglantinizi kontrol edin.
        pause
        exit /b 1
    )
)

echo.
echo Arayuz aciliyor... Tarayici kendiliginden acilmazsa: http://localhost:8501
echo Kapatmak icin bu pencereyi kapatin.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address localhost
pause
