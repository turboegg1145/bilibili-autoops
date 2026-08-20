@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Bilibili-AutoOps

where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    if exist "C:\Program Files\Python39\python.exe" (
        set "PY_CMD=C:\Program Files\Python39\python.exe"
    ) else (
        if exist "%LOCALAPPDATA%\Programs\Python\Python39\python.exe" (
            set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
        ) else (
            set "PY_CMD=py"
        )
    )
)

"%PY_CMD%" main.py
echo.
echo ========================================================
echo [提示] 程序已结束运行。
pause
