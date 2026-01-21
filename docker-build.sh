#!/bin/bash
# Скрипт для сборки Docker образа

DOCKERHUB_USERNAME=${1:-"your-dockerhub-username"}
VERSION=${2:-"latest"}

echo "🔨 Сборка Docker образа..."
docker build -t ${DOCKERHUB_USERNAME}/adminbot:${VERSION} .

if [ $? -eq 0 ]; then
    echo "✅ Образ успешно собран: ${DOCKERHUB_USERNAME}/adminbot:${VERSION}"
    echo ""
    echo "Для публикации в Docker Hub выполните:"
    echo "  docker login"
    echo "  docker push ${DOCKERHUB_USERNAME}/adminbot:${VERSION}"
else
    echo "❌ Ошибка при сборке образа"
    exit 1
fi
