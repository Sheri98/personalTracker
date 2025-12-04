@echo off
REM Run Personal Task Tracker on Windows

cd /d "%~dp0"

REM Try Python from PATH
python personal_tracker.py
if %ERRORLEVEL% NEQ 0 (
    REM Try py launcher
    py personal_tracker.py
)

pause
