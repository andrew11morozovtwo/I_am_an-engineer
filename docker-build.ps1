# PowerShell скрипт для сборки Docker образа

param(
    [string]$DockerHubUsername = "your-dockerhub-username",
    [string]$Version = "latest"
)

Write-Host "🔨 Сборка Docker образа..." -ForegroundColor Cyan
Write-Host "Пользователь: $DockerHubUsername" -ForegroundColor Gray
Write-Host "Версия: $Version" -ForegroundColor Gray
Write-Host ""

docker build -t "${DockerHubUsername}/adminbot:${Version}" .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Образ успешно собран: ${DockerHubUsername}/adminbot:${Version}" -ForegroundColor Green
    Write-Host ""
    Write-Host "Для публикации в Docker Hub выполните:" -ForegroundColor Yellow
    Write-Host "  docker login" -ForegroundColor White
    Write-Host "  docker push ${DockerHubUsername}/adminbot:${Version}" -ForegroundColor White
} else {
    Write-Host "❌ Ошибка при сборке образа" -ForegroundColor Red
    exit 1
}
