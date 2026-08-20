@echo off
chcp 65001 >nul
title Bilibili 自动化运营中台
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo [错误] 脚本运行异常退出。
    pause
)
