@echo off
REM Скрипт для очистки варнов и банов из базы данных
cd /d "%~dp0"
python -m app.scripts.clear_warns_bans
pause
