# Docker инструкции для Telegram бота

## 📦 Быстрый старт

### 1. Подготовка

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321
OWNER_ID=123456789
DB_URL=sqlite+aiosqlite:///data/app.db
OPENAI_API_KEY=your_openai_api_key
```

### 2. Сборка и запуск

#### Локальная разработка:

```bash
# Сборка образа
docker-compose build

# Запуск контейнера
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

#### Продакшен:

```bash
# Сборка и запуск с продакшен конфигурацией
docker-compose -f docker-compose.prod.yml up -d --build

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Остановка
docker-compose -f docker-compose.prod.yml down
```

## 🐳 Работа с Docker Hub

### 1. Сборка образа для Docker Hub

```bash
# Сборка образа с тегом
docker build -t your-dockerhub-username/adminbot:latest .

# Или с версией
docker build -t your-dockerhub-username/adminbot:v1.0.0 .
```

### 2. Тестирование образа локально

```bash
# Запуск образа локально
docker run -d \
  --name adminbot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  your-dockerhub-username/adminbot:latest
```

### 3. Публикация в Docker Hub

```bash
# Вход в Docker Hub
docker login

# Отправка образа
docker push your-dockerhub-username/adminbot:latest
docker push your-dockerhub-username/adminbot:v1.0.0
```

### 4. Использование образа с Docker Hub на сервере

```bash
# На сервере создайте docker-compose.yml:

version: '3.8'
services:
  adminbot:
    image: your-dockerhub-username/adminbot:latest
    container_name: adminbot
    restart: always
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    networks:
      - adminbot-network

networks:
  adminbot-network:
    driver: bridge

# Запуск
docker-compose up -d
```

## 📁 Структура данных

При использовании Docker, база данных и логи сохраняются в директории `./data` на хосте:

```
./data/
├── app.db          # SQLite база данных
└── logs_export_*.xlsx  # Экспортированные логи (если есть)
```

## 🔧 Полезные команды

### Просмотр логов

```bash
# Все логи
docker-compose logs

# Последние 100 строк
docker-compose logs --tail=100

# Следить за логами в реальном времени
docker-compose logs -f
```

### Выполнение команд в контейнере

```bash
# Войти в контейнер
docker-compose exec adminbot bash

# Выполнить скрипт инициализации БД
docker-compose exec adminbot python -m app.scripts.init_db

# Выполнить скрипт экспорта логов
docker-compose exec adminbot python -m app.scripts.export_logs_to_excel
```

### Обновление образа

```bash
# Остановить контейнер
docker-compose down

# Обновить образ (если используете Docker Hub)
docker-compose pull

# Пересобрать образ (если используете локальную сборку)
docker-compose build --no-cache

# Запустить заново
docker-compose up -d
```

### Очистка

```bash
# Остановить и удалить контейнеры
docker-compose down

# Удалить образы
docker rmi adminbot

# Удалить неиспользуемые образы и контейнеры
docker system prune -a
```

## ⚠️ Важные замечания

1. **База данных**: База данных SQLite сохраняется в volume `./data`. При удалении контейнера данные сохранятся.

2. **Переменные окружения**: Используйте `.env` файл или передавайте переменные через `docker-compose.yml`. НЕ коммитьте `.env` в git!

3. **Логи**: Логи контейнера можно просматривать через `docker-compose logs`. Также логи сохраняются в БД.

4. **Ресурсы**: Для продакшена рекомендуется использовать `docker-compose.prod.yml` с ограничениями ресурсов.

5. **Безопасность**: 
   - Храните `.env` файл в безопасном месте
   - Не публикуйте токены в Docker Hub описаниях
   - Используйте secrets для продакшена (Docker Swarm или Kubernetes)

## 🚀 Развертывание на сервере

### Вариант 1: Использование образа с Docker Hub

```bash
# На сервере
mkdir adminbot
cd adminbot

# Создайте .env файл
nano .env

# Создайте docker-compose.yml
nano docker-compose.yml

# Запустите
docker-compose up -d
```

### Вариант 2: Локальная сборка на сервере

```bash
# Клонируйте репозиторий
git clone <repository_url>
cd Always_safe

# Создайте .env файл
cp .env.example .env
nano .env

# Соберите и запустите
docker-compose -f docker-compose.prod.yml up -d --build
```

## 📊 Мониторинг

```bash
# Статус контейнера
docker-compose ps

# Использование ресурсов
docker stats adminbot

# Проверка здоровья
docker-compose exec adminbot python -c "import sys; sys.exit(0)"
```
ээээээээээээээээээээээээээээээээээээээ