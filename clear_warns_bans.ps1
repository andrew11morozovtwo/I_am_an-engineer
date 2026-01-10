# Скрипт для очистки варнов и банов из базы данных
Set-Location $PSScriptRoot
Write-Host "Очистка варнов и банов из базы данных..." -ForegroundColor Yellow
python app\scripts\clear_warns_bans.py
Read-Host "`nНажмите Enter для выхода"
