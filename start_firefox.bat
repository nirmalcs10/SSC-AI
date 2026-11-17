@echo off
chcp 65001 >nul
title Indian Stock Market Paper Trading Tool - Firefox Launcher
cd /d "%~dp0"

echo ======================================================================
echo    INDIAN STOCK MARKET MULTI-TIMEFRAME PAPER TRADING TOOL
echo    Target Browser: Mozilla Firefox
echo    Zero Real-Money Risk: 100%% Simulation Mode Active
echo ======================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.10+ or add it to PATH.
    pause
    exit /b 1
)

echo Starting application server and launching Mozilla Firefox...
python launch.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTICE] Application process exited.
    pause
)
