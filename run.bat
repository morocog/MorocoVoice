@echo off
setlocal
title VoiceFlow-Win Launcher

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup first.
    pause
    exit /b 1
)

echo Starting VoiceFlow-Win in background...
start "" ".venv\Scripts\pythonw.exe" -m app.main
exit /b 0
