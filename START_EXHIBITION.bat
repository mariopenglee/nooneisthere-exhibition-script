@echo off
title Exhibition Controller - DO NOT CLOSE
mode con cols=70 lines=30
color 0A
cls

echo ==============================================================
echo                  EXHIBITION SYSTEM
echo ==============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    pause
    exit /b 1
)

REM Check if config exists
if not exist exhibition_config.json (
    echo ERROR: exhibition_config.json not found!
    echo Please make sure the config file is in the same folder.
    pause
    exit /b 1
)

echo Starting exhibition controller...
echo.
echo The system will:
echo   - Auto-detect your directories
echo   - Generate new objects every 10 minutes
echo   - Auto-refresh the 3D viewer
echo   - Open browser automatically
echo.
echo ==============================================================
echo            PRESS CTRL+C TO STOP EVERYTHING
echo ==============================================================
echo.

REM Run the controller
python exhibition_controller.py

echo.
echo Exhibition stopped.
pause
