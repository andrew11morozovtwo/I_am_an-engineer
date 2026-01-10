# Скрипт для проверки статуса бота
Write-Host "=== Проверка статуса бота ===" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка активных процессов Python
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "[OK] Найдены активные процессы Python:" -ForegroundColor Green
    $pythonProcesses | ForEach-Object {
        Write-Host "  - PID: $($_.Id) | Запущен: $($_.StartTime) | Память: $([math]::Round($_.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "[INFO] Один из этих процессов может быть вашим ботом" -ForegroundColor Cyan
    Write-Host "[INFO] Чтобы проверить точно, попробуйте отправить команду /start боту в Telegram" -ForegroundColor Cyan
} else {
    Write-Host "[WARNING] Активные процессы Python не найдены" -ForegroundColor Red
    Write-Host "[INFO] Бот, вероятно, не запущен" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Как проверить, что бот работает ===" -ForegroundColor Cyan
Write-Host "1. Откройте Telegram"
Write-Host "2. Найдите вашего бота"
Write-Host "3. Отправьте команду: /start"
Write-Host "4. Если бот ответит - значит он работает!"
Write-Host ""
Write-Host "Или отправьте команду: /blacklist list"
Write-Host "Эта команда должна показать список запрещенных слов"
