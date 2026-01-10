# Скрипт для проверки активных процессов Python, которые могут запускать бота
Write-Host "🔍 Проверяем активные процессы Python..." -ForegroundColor Yellow

$processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*python*" }

if ($processes) {
    Write-Host "⚠️  Найдены активные процессы Python:" -ForegroundColor Red
    $processes | Format-Table Id, ProcessName, Path, StartTime -AutoSize
    
    Write-Host "`n❓ Хотите остановить все процессы Python? (y/n)" -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -eq "y" -or $answer -eq "Y") {
        $processes | Stop-Process -Force
        Write-Host "✅ Все процессы Python остановлены" -ForegroundColor Green
    }
} else {
    Write-Host "✅ Активные процессы Python не найдены" -ForegroundColor Green
}

Write-Host "`n💡 Совет: Убедитесь, что вы не запускаете бота в нескольких терминалах одновременно" -ForegroundColor Cyan
