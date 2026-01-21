# Команды для коммита в GitHub

## ✅ Быстрая подготовка и отправка

### Шаг 1: Проверка безопасности

```powershell
# Убедитесь, что .env не будет закоммичен
git check-ignore .env
# Должно вывести: .env

# Проверьте статус
git status
```

### Шаг 2: Добавление файлов

```powershell
# Добавить все измененные и новые файлы
git add .

# Или выборочно:
git add README.md
git add PREPARE_FOR_GITHUB.md
git add .gitignore
git add app/
git add Dockerfile
git add docker-compose.yml
git add env.example
git add requirements.txt
git add DOCKER.md
git add QUICKSTART_DOCKER.md
```

### Шаг 3: Проверка перед коммитом

```powershell
# Посмотреть, что будет закоммичено
git status

# Убедитесь, что .env НЕ в списке!
```

### Шаг 4: Создание коммита

```powershell
git commit -m "Update: Telegram bot for 'Безопасность всегда' channel

- Updated AI prompts for safety channel theme
- Added comprehensive README.md
- Added Docker support and documentation
- Added log viewing and export scripts
- Updated project structure and configuration
- Removed old channel references"
```

### Шаг 5: Отправка в GitHub

```powershell
# Отправить изменения
git push origin main

# Если нужно создать новую ветку:
# git push -u origin main
```

## 🔍 Детальная проверка

### Проверка игнорируемых файлов:

```powershell
# Проверить, что важные файлы игнорируются
git status --ignored | Select-String -Pattern "\.env|app\.db|__pycache__"
```

### Просмотр изменений:

```powershell
# Посмотреть изменения в файлах
git diff --cached

# Или для конкретного файла
git diff --cached README.md
```

## 📋 Полный список команд (по порядку)

```powershell
# 1. Проверка статуса
git status

# 2. Добавление файлов
git add .

# 3. Проверка, что будет закоммичено
git status

# 4. Создание коммита
git commit -m "Your commit message"

# 5. Отправка в GitHub
git push origin main
```

## ⚠️ Если нужно отменить изменения

```powershell
# Отменить добавление файла (но сохранить изменения)
git restore --staged <file>

# Отменить все изменения в файле
git restore <file>

# Отменить последний коммит (но сохранить изменения)
git reset --soft HEAD~1
```

## 🚀 Готово!

После выполнения этих команд все изменения будут отправлены в GitHub.
