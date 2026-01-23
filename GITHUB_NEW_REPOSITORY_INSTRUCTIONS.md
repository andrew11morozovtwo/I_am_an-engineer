# Инструкция: Создание нового репозитория на GitHub и отправка проекта

## 📋 Подготовка

### Шаг 1: Проверка текущего состояния

```powershell
# Проверьте текущий статус репозитория
git status

ответ:
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   app/application/services/comment_service.py        

Untracked files:
  (use "git add <file>..." to include in what will be committed)       
        AI_API_CALLS.md
        GITHUB_NEW_REPOSITORY_INSTRUCTIONS.md

no changes added to commit (use "git add" and/or "git commit -a")

# Проверьте текущий remote (подключенный репозиторий)
git remote -v

ответ:
origin  https://github.com/andrew11morozovtwo/I_am_an-engineer.git (fetch)
origin  https://github.com/andrew11morozovtwo/I_am_an-engineer.git (push)

# Убедитесь, что .env файл игнорируется
git check-ignore .env
# Должно вывести: .env
```

ответ:
.env

### Шаг 2: Проверка .gitignore

Убедитесь, что в `.gitignore` есть:
- `.env` и `**/.env`
- `app.db` и другие базы данных
- `__pycache__/`
- `*.log`
- Временные скрипты

---

## 🆕 Создание нового репозитория на GitHub

### Шаг 3: Создание репозитория через веб-интерфейс GitHub

1. **Откройте GitHub:**
   - Перейдите на https://github.com
   - Войдите в свой аккаунт

2. **Создайте новый репозиторий:**
   - Нажмите на значок "+" в правом верхнем углу
   - Выберите "New repository"

3. **Настройте репозиторий:**
   - **Repository name:** `Always_safe` (или другое имя на ваше усмотрение)
   - **Description:** `Telegram Bot для канала "Безопасность всегда" - автоматическая модерация и AI-комментирование`
   - **Visibility:** Выберите Public или Private
   - **⚠️ ВАЖНО:** НЕ создавайте README, .gitignore или лицензию (у вас уже есть эти файлы)
   - Нажмите "Create repository"

4. **Скопируйте URL нового репозитория:**
   - После создания GitHub покажет URL
   - Он будет выглядеть так: `https://github.com/ваш_username/Always_safe.git`
   https://github.com/andrew11morozovtwo/Always_safe.git
   - Или SSH: `git@github.com:ваш_username/Always_safe.git`
   git@github.com:andrew11morozovtwo/Always_safe.git

---

## 🔄 Подключение к новому репозиторию

### Шаг 4: Изменение remote URL

```powershell
# Удалите старый remote (если нужно)
git remote remove origin

# Или просто измените URL существующего remote
git remote set-url origin https://github.com/ваш_username/Always_safe.git
PS C:\zero_code\Always_safe> git remote set-url origin https://github.com/andrew11morozovtwo/Always_safe.git

# Проверьте, что URL изменился
git remote -v
```
PS C:\zero_code\Always_safe> git remote -v
origin  https://github.com/andrew11morozovtwo/Always_safe.git (fetch)
origin  https://github.com/andrew11morozovtwo/Always_safe.git (push)

Что это значит:
Локальный репозиторий подключен к Always_safe на GitHub
git push отправит изменения в Always_safe
git pull получит изменения из Always_safe

**Замените `ваш_username` и `Always_safe` на ваши реальные значения!**

---

## 📝 Подготовка и отправка изменений

### Шаг 5: Добавление изменений

```powershell
# Проверьте, какие файлы будут добавлены
git status

# Добавьте все измененные и новые файлы
git add .

# Или выборочно:
git add app/application/services/comment_service.py
git add AI_API_CALLS.md

# Проверьте, что .env НЕ в списке!
git status
```

ответ:
PS C:\zero_code\Always_safe> git status
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   app/application/services/comment_service.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
        AI_API_CALLS.md
        GITHUB_NEW_REPOSITORY_INSTRUCTIONS.md

no changes added to commit (use "git add" and/or "git commit -a")

Расшифровка:
On branch mainYour branch is up to date with 'origin/main'.
Вы на ветке main
Локальная ветка синхронизирована с удаленной (но это может быть устаревшая информация, так как вы только что изменили remote URL)
Changes not staged for commit:  modified:   app/application/services/comment_service.py
Файл изменен, но не добавлен в staging (не готов к коммиту)
Нужно добавить: git add app/application/services/comment_service.py
Untracked files:  AI_API_CALLS.md  GITHUB_NEW_REPOSITORY_INSTRUCTIONS.md
Два новых файла, которые Git еще не отслеживает
Нужно добавить: git add AI_API_CALLS.md и git add GITHUB_NEW_REPOSITORY_INSTRUCTIONS.md
no changes added to commit
В staging area нет файлов, готовых к коммиту
Сначала нужно выполнить git add

PS C:\zero_code\Always_safe> # осмотреть все отслеживаемые файлы
PS C:\zero_code\Always_safe> git ls-files
.dockerignore
.gitignore
ADMIN_DATA_STORAGE.md
ADMIN_PANEL_INSTRUCTIONS.md
AI_API_CALLS.md
AI_DATA_COLLECTION.md
CHECK_ENV_FILES.md
DOCKER.md
Dockerfile
GITHUB_COMMIT_COMMANDS.md
GITHUB_NEW_REPOSITORY_INSTRUCTIONS.md
GITHUB_PUSH_INSTRUCTIONS.md
MODERATION_SYSTEM_DETAILS.md
PREPARE_FOR_GITHUB.md
QUICKSTART_DOCKER.md
README.md
RENAME_REPOSITORY.md
app/__init__.py
app/application/__init__.py
app/application/services/__init__.py
app/application/services/admin_service.py
app/application/services/comment_service.py
app/application/services/content_service.py
app/application/services/log_service.py
app/application/services/moderation_service.py
app/application/services/stats_service.py
app/application/services/user_service.py
app/config/__init__.py
app/config/settings.py
app/infrastructure/__init__.py
app/infrastructure/ai_clients.py
app/infrastructure/db/__init__.py
app/infrastructure/db/models.py
app/infrastructure/db/repositories.py
app/infrastructure/db/session.py
app/main.py
app/presentation/middlewares/__init__.py
app/presentation/middlewares/admin_mw.py
app/presentation/routers/__init__.py
app/presentation/routers/admin_router.py
app/presentation/routers/channel_router.py
app/presentation/routers/user_router.py
app/scripts/__init__.py
app/scripts/add_words_to_blacklist.py
app/scripts/clear_all_data.py
app/scripts/clear_warns_bans.py
app/scripts/export_logs_to_excel.py
app/scripts/init_db.py
app/scripts/init_default_blacklist.py
app/scripts/migrate_db.py
app/scripts/view_logs.py
check_bot_processes.ps1
clear_warns_bans.ps1
docker-build.ps1
docker-build.sh
docker-compose.prod.yml
docker-compose.yml
docker-push.ps1
docker-push.sh
env.example
requirements.txt
PS C:\zero_code\Always_safe>
PS C:\zero_code\Always_safe> # осмотреть количество отслеживаемых файлов
PS C:\zero_code\Always_safe> git ls-files | Measure-Object -Line

### Шаг 6: Создание коммита

```powershell
# Создайте коммит с описанием изменений
git commit -m "Update: Удалены упоминания канала из кода для универсальности

- Удалено упоминание 'Безопасность всегда' из prepare_conversation_history()
- Добавлен документ AI_API_CALLS.md с полным списком обращений к ИИ
- Обновлена документация по системным промптам"
```

### Шаг 7: Отправка в новый репозиторий

```powershell
# Если это первый push в новый репозиторий
git push -u origin main

ответ:
PS C:\zero_code\Always_safe> git push -u origin main
Enumerating objects: 234, done.
Counting objects: 100% (234/234), done.
Delta compression using up to 4 threads
Compressing objects: 100% (220/220), done.
Writing objects: 100% (234/234), 151.83 KiB | 631.00 KiB/s, done.
Total 234 (delta 91), reused 0 (delta 0), pack-reused 0 (from 0)
remote: Resolving deltas: 100% (91/91), done.
To https://github.com/andrew11morozovtwo/Always_safe.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.

# Если ветка называется master вместо main:
# git push -u origin master

# В дальнейшем можно просто использовать:
# git push origin main
```

---

## ✅ Проверка

### Шаг 8: Проверка на GitHub

1. Откройте ваш новый репозиторий на GitHub
2. Убедитесь, что все файлы загружены
3. Проверьте, что `.env` и `app.db` НЕ видны в репозитории
4. Проверьте, что `AI_API_CALLS.md` присутствует

---

## 🔍 Дополнительные проверки безопасности

### Перед отправкой убедитесь:

```powershell
# Проверьте, что .env не будет закоммичен
git check-ignore .env
# Должно вывести: .env

# Проверьте, что app.db не будет закоммичен
git check-ignore app.db
# Должно вывести: app.db

# Посмотрите, что будет отправлено
git status
git diff --cached
```

---

## ⚠️ Если что-то пошло не так

### Отмена последнего коммита (если еще не отправили):

```powershell
git reset --soft HEAD~1
```

### Отмена изменений в файле:

```powershell
git restore имя_файла
```

### Если случайно добавили .env:

```powershell
# Удалите из индекса (но оставьте файл локально)
git rm --cached .env

# Проверьте .gitignore
# Убедитесь, что .env там есть

# Создайте коммит с удалением
git commit -m "Remove .env from repository"
```

---

## 📌 Быстрая шпаргалка команд

```powershell
# 1. Проверка
git status
git remote -v

# 2. Изменение remote
git remote set-url origin https://github.com/ваш_username/Always_safe.git

# 3. Добавление и коммит
git add .
git commit -m "Описание изменений"

# 4. Отправка
git push -u origin main
```

---

## 🎯 Итоговый чеклист

- [ ] Проверен `.gitignore` (`.env`, `app.db` в списке)
- [ ] Создан новый репозиторий на GitHub
- [ ] Скопирован URL нового репозитория
- [ ] Изменен `remote` URL в локальном репозитории
- [ ] Проверено, что `.env` не будет закоммичен
- [ ] Добавлены все нужные файлы (`git add .`)
- [ ] Создан коммит с описанием
- [ ] Отправлено в новый репозиторий (`git push -u origin main`)
- [ ] Проверено на GitHub, что все файлы на месте
- [ ] Проверено, что чувствительные файлы (`.env`, `app.db`) отсутствуют

---

**Готово!** Ваш проект теперь в новом репозитории на GitHub.
