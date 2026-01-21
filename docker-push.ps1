# PowerShell скрипт для публикации Docker образа в Docker Hub

param(
    [string]$DockerHubUsername = "your-dockerhub-username",
    [string]$Version = "latest"
)

Write-Host "📤 Публикация образа в Docker Hub..." -ForegroundColor Cyan
Write-Host "Пользователь: $DockerHubUsername" -ForegroundColor Gray
Write-Host "Версия: $Version" -ForegroundColor Gray
Write-Host ""

# Проверка входа в Docker Hub
$dockerInfo = docker info 2>&1
if ($dockerInfo -notmatch "Username") {
    Write-Host "⚠️  Вы не вошли в Docker Hub. Выполните: docker login" -ForegroundColor Yellow
    exit 1
}

# Публикация образа
docker push "${DockerHubUsername}/adminbot:${Version}"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Образ успешно опубликован!" -ForegroundColor Green
    Write-Host "URL: https://hub.docker.com/r/${DockerHubUsername}/adminbot" -ForegroundColor Cyan
} else {
    Write-Host "❌ Ошибка при публикации образа" -ForegroundColor Red
    exit 1
}
