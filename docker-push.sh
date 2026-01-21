#!/bin/bash
# Скрипт для публикации Docker образа в Docker Hub

DOCKERHUB_USERNAME=${1:-"your-dockerhub-username"}
VERSION=${2:-"latest"}

echo "📤 Публикация образа в Docker Hub..."
echo "Пользователь: ${DOCKERHUB_USERNAME}"
echo "Версия: ${VERSION}"
echo ""

# Проверка входа в Docker Hub
if ! docker info | grep -q "Username"; then
    echo "⚠️  Вы не вошли в Docker Hub. Выполните: docker login"
    exit 1
fi

# Публикация образа
docker push ${DOCKERHUB_USERNAME}/adminbot:${VERSION}

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Образ успешно опубликован!"
    echo "URL: https://hub.docker.com/r/${DOCKERHUB_USERNAME}/adminbot"
else
    echo "❌ Ошибка при публикации образа"
    exit 1
fi
