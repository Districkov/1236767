@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Запуск локального зеркала ФГИС...
python server.py --port 8017
pause
