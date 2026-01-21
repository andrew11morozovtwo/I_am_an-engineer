# 🚀 Быстрый старт с Docker

## Шаг 1: Подготовка

1. Скопируйте `env.example` в `.env`:
   ```bash
   cp env.example .env
   ```

2. Отредактируйте `.env` и укажите ваши данные:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_IDS=123456789
   OWNER_ID=123456789
   DB_URL=sqlite+aiosqlite:///data/app.db
   OPENAI_API_KEY=your_openai_api_key
   ```

## Шаг 2: Запуск

### Вариант A: Локальная разработка

```bash
docker-compose up -d --build
```

### Вариант B: Продакшен

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## Шаг 3: Проверка

```bash
# Просмотр логов
docker-compose logs -f

# Проверка статуса
docker-compose ps
```

## Шаг 4: Публикация в Docker Hub

1. Соберите образ:
   ```bash
   docker build -t your-username/adminbot:latest .
   ```

2. Войдите в Docker Hub:
   ```bash
   docker login
   ```

3. Опубликуйте:
   ```bash
   docker push your-username/adminbot:latest
   ```

## Использование образа с Docker Hub

На сервере создайте `docker-compose.yml`:

```yaml
version: '3.8'
services:
  adminbot:
    image: your-username/adminbot:latest
    container_name: adminbot
    restart: always
    env_file:
      - .env
    volumes:
      - ./data:/app/data
```

Запуск:
```bash
docker-compose up -d
```

## Полезные команды

```bash
# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f adminbot

# Выполнение команды в контейнере
docker-compose exec adminbot python -m app.scripts.init_db
```

## Структура данных

База данных сохраняется в `./data/app.db` на хосте.
