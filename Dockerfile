# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем переменные окружения (раньше для лучшего кэширования)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем системные зависимости и Python пакеты в одном слое,
# затем удаляем ненужные build-зависимости для уменьшения размера образа
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Создаем директорию для базы данных и логов (до копирования кода)
RUN mkdir -p /app/data && \
    chmod 755 /app/data

# Копируем весь код приложения (последним для лучшего кэширования слоев)
COPY . .

# Точка входа
CMD ["python", "-m", "app.main"]
