# 🚀 Telegram Bot Railway Deployment Guide

## Полный чек-лист деплоя Telegram бота на Railway

---

## 📋 ШАГ 1: Подготовка переменных окружения

### 1.1 Telegram Bot Token
1. Откройте Telegram → поиск **@BotFather**
2. Команда `/mybots` → выберите бота → `/api_token`
3. Скопируйте токен (формат: `123456789:ABCDefgh...`)

### 1.2 Railway переменные
В Railway dashboard → Project → Environment (или Settings → Environment):

```bash
# ========== TELEGRAM ==========
TELEGRAM_BOT_TOKEN=123456789:ABCDefgh...  # Из BotFather
TELEGRAM_BOT_USERNAME=YourBotName  # Имя бота (как в /start@YourBotName)

# ⚠️ ВАЖНО: TELEGRAM_WEBHOOK_URL устанавливается ПОСЛЕ первого деплоя
# (Railway сначала генерирует домен, потом можно установить URL)
```

---

## 📦 ШАГ 2: Добавление Telegram Bot Setup сервиса на Railway

### 2.1 Вариант A: Через Railway CLI

```bash
# Если ещё не установлен:
npm install -g @railway/cli

# Логин в Railway
railway login

# Перейти в проект
railway link

# Добавить telegram-bot-setup сервис из docker-compose.prod.yml
# Railway должен автоматически подхватить его
```

### 2.2 Вариант B: Через Railway Dashboard (Рекомендуется)

1. **Откройте Railway Dashboard** → ваш проект
2. **New Service** → **Docker**
3. Заполните:
   - **Name:** `telegram-bot-setup`
   - **Dockerfile:** `docker/telegram/Dockerfile`
   - **Registry:** оставить пусто
   - **Source:** GitHub (свяжите репо)
4. **Deploy** → Railway начнёт сборку

---

## 🔗 ШАГ 3: Связывание сервисов

### 3.1 Зависимости сервисов

После добавления `telegram-bot-setup`, должна быть такая структура:

```
Сервис                Зависит от          Запускается
────────────────────────────────────────────────────
db (PostgreSQL)       -                   Всегда (1-я)
redis                 -                   Всегда (1-я)
django                db, redis           После DB + Redis
celery                db, redis           После DB + Redis
celery-beat           db, redis           После DB + Redis
telegram-bot-setup    db, redis           После DB + Redis (один раз, потом exit)
nginx                 django              После Django
```

### 3.2 Установка зависимостей в Railway

**Через Railway CLI:**
```bash
railway run --service telegram-bot-setup bash
# Внутри:
# Нет нужно в Railway — используется docker-compose.prod.yml
```

**Через Dashboard:**
1. Перейти на каждый сервис
2. Settings → **Dependencies** (если доступно)
3. Выбрать зависимые сервисы

**Или через `railway.json`:**
```json
{
  "services": {
    "db": {
      "builder": "docker",
      "dockerfile": "docker/django/Dockerfile"
    },
    "telegram-bot-setup": {
      "builder": "docker",
      "dockerfile": "docker/telegram/Dockerfile",
      "depends_on": ["db", "redis"]
    }
  }
}
```

---

## 🎯 ШАГ 4: Установка TELEGRAM_WEBHOOK_URL

### 4.1 После первого успешного деплоя

1. Дождитесь пока `django` сервис запустится и будет Health: "Up" ✅
2. Railway сгенерирует домен (например: `questflow-production.railway.app`)
3. Откройте Settings → Environment для `django` сервиса
4. **Добавьте новую переменную:**
   ```
   TELEGRAM_WEBHOOK_URL=https://questflow-production.railway.app/telegram/webhook/
   ```
5. **Redeploy** → Railway перезапустит всё с новой переменной

### 4.2 Проверка домена

```bash
# На локальной машине:
curl https://questflow-production.railway.app/

# Должно показать ошибку 404 или редирект на Django (это нормально)
# Главное — нет 502/503 (сервис работает)
```

---

## ✅ ШАГ 5: Проверка регистрации webhook

### 5.1 Логи telegram-bot-setup

```bash
# После Redeploy, сервис telegram-bot-setup должен запуститься:
railway logs -s telegram-bot-setup

# Ожидаемый вывод:
# ⏳ Waiting for database...
# 🔗 Setting up Telegram webhook...
# ✅ Webhook initialized
# (сервис выходит — это нормально!)
```

### 5.2 Проверить статус webhook

```bash
# Оба варианта работают:
curl https://questflow-production.railway.app/telegram/webhook/
# или
railroad run --service django python manage.py shell
# >>> from apps.telegram_bot.bot import setup_webhook
# >>> setup_webhook()
# True  ← успех
```

### 5.3 Проверка в Telegram

1. Откройте Telegram
2. Отправьте боту `/start`
3. Бот должен **ответить** (не зависнуть)
4. Если ответил — webhook работает! ✅

---

## 🔗 ШАГ 6: Интеграция с остальными сервисами

### 6.1 Celery + Telegram Bot

**Уже подключено!** Celery отправляет уведомления через Telegram Bot:

```python
# Примеры интеграции (уже работают):
from apps.telegram_bot.tasks import (
    send_level_up_notification,
    send_badge_notification,
    send_new_task_notification,
)

# В любом месте кода:
send_level_up_notification.delay(user_id=123, level=5)
```

### 6.2 Django + Telegram Bot

**Webhook получение updates:**
```
GET/POST /telegram/webhook/
  ↓
TelegramWebhookView
  ↓
python-telegram-bot handlers
  ↓
/start, /help, /profile, /tasks, /badges, etc.
```

### 6.3 Celery Beat + Telegram Bot

**Расписание уведомлений (уже настроено):**
```
Celery Beat
  ↓ (каждый день 09:00 UTC)
send_daily_reminders
  ↓
Celery Worker
  ↓
Telegram Bot (уведомление)
```

### 6.4 Проверка интеграций

```bash
# 1. Залогиньтесь в админ-панель
# 2. Перейдите на Account → Telegram Link
# 3. Нажмите "Connect with Telegram" → отправьте /start боту
# 4. Проверьте, что аккаунт связан

# 5. Проверьте логи:
railway logs -s django     # основное приложение
railway logs -s celery     # отправка уведомлений
railway logs -s celery-beat  # расписание
```

---

## 🚨 Troubleshooting

| Проблема | Причина | Решение |
|----------|---------|---------|
| `telegram-bot-setup` крашится | БД не готова | Проверьте `wait_for_db.sh`, добавьте задержку |
| Webhook не регистрируется | TOKEN неверный | Проверьте `TELEGRAM_BOT_TOKEN` |
| "Connection refused" при webhook | nginx не запущен | Проверьте `django` → Settings → Health |
| Бот не отвечает на /start | webhook не зарегистрирована | Проверьте логи `telegram-bot-setup` |
| Ошибка БД в telegram-bot-setup | `DATABASE_URL` не установлена | Установите переменные БД (смотри выше) |

---

## 📊 Архитектура на Railway

```
┌─────────────────────────────────────────────────────────────┐
│                    RAILWAY INFRASTRUCTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐     ┌──────────────┐                      │
│  │  PostgreSQL  │     │    Redis     │                      │
│  │  (DB)        │     │  (Cache/Q)   │                      │
│  └──────────────┘     └──────────────┘                      │
│       ↑                    ↑                                  │
│       │                    │                                  │
│  ┌────────────────────────────────────┐                     │
│  │         Django (WSGI)              │                     │
│  │ ├─ /telegram/webhook/ endpoint ✓  │                     │
│  │ ├─ migrations ✓                    │                     │
│  │ ├─ collectstatic ✓                 │                     │
│  │ └─ gunicorn :8000                  │                     │
│  └────────────────────────────────────┘                     │
│       ↑                    ↑                                  │
│       │                    │                                  │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │  Celery     │  │  Celery-Beat   │  │ telegram-bot     │  │
│  │  (Worker)   │  │  (Scheduler)   │  │ -setup (init)    │  │
│  │ Processes   │  │ Scheduled      │  │ Runs once →exit  │  │
│  │ Telegram    │  │ tasks          │  │ Sets webhook     │  │
│  │ tasks       │  │                │  └──────────────────┘  │
│  └─────────────┘  └────────────────┘                        │
│       ↑                    ↑                                  │
│       └────────────────────┘                                 │
│              ↓                                                │
│       ┌─────────────────────────────────┐                   │
│       │    Telegram Bot Notifications   │                   │
│       └─────────────────────────────────┘                   │
│              ↑                                                │
│       ┌──────────────────────┐                              │
│       │  Telegram Bot API    │                              │
│       │  (sendMessage, etc)  │                              │
│       └──────────────────────┘                              │
│              ↑                                                │
│       ┌──────────────────────┐                              │
│       │  Telegram Users      │                              │
│       │  (Receive messages)  │                              │
│       └──────────────────────┘                              │
│                                                               │
│  ┌──────────────────────────────────────────┐               │
│  │   nginx (Reverse Proxy)                  │               │
│  │   Port 80/443 → Django :8000             │               │
│  │   ┌─ Static files (/static/)             │               │
│  │   ├─ Media files (/media/)               │               │
│  │   └─ API endpoints (/api/*, /admin/)    │               │
│  └──────────────────────────────────────────┘               │
│       ↑                                                       │
│       │ HTTPS                                                │
│       │                                                       │
│   ┌───────────────────────────────────────┐                │
│   │  Telegram API (sends Updates to)      │                │
│   │  POST /telegram/webhook/              │                │
│   └───────────────────────────────────────┘                │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Telegram User → Telegram API → nginx → Django → TelegramWebhookView → python-telegram-bot → handlers
```

---

## 📝 Итоговый чек-лист

- [ ] **TELEGRAM_BOT_TOKEN** установлен в Railway
- [ ] **TELEGRAM_BOT_USERNAME** установлен в Railway
- [ ] **DATABASE_URL** или **DB_*** переменные установлены
- [ ] **django** сервис запущен (Status: Up ✅)
- [ ] **telegram-bot-setup** запущен, выполнился и вышел (Status: Exited)
- [ ] **TELEGRAM_WEBHOOK_URL** установлен в Railway
- [ ] Логи показывают "Webhook set to: https://..."
- [ ] `/telegram/webhook/` возвращает `{"status": "ok"}`
- [ ] Бот ответил на `/start` в Telegram
- [ ] **celery** сервис запущен (обработка задач)
- [ ] **celery-beat** сервис запущен (расписание)
- [ ] Аккаунт можно связать в админ-панели

---

## 🎓 Как работает интеграция

### Поток сообщения от пользователя:

```
Пользователь: /start @YourBot
    ↓
Telegram API
    ↓
POST https://your-domain.com/telegram/webhook/
    ↓
nginx (прокси-сервер)
    ↓
Django (порт 8000)
    ↓
TelegramWebhookView.post()
    ↓
python-telegram-bot Application.process_update()
    ↓
handlers.start_command()  ← обработчик команды
    ↓
TelegramService.send_message(user_id, "Привет! 👋")
    ↓
Celery task: send_telegram_message (асинхронно)
    ↓
Bot.send_message(text="...", chat_id=..., parse_mode="HTML")
    ↓
Telegram API
    ↓
Пользователь получает сообщение ✅
```

### Поток уведомления (из системы):

```
Действие (новая задача, уровень up, и т.д.)
    ↓
TaskService.create_task() / GamificationEngine.level_up()
    ↓
Signal: post_save или custom signal
    ↓
Celery task: send_telegram_notification
    ↓
TelegramService.send_message()
    ↓
Bot.send_message()
    ↓
Telegram API
    ↓
Пользователь получает уведомление ✅
```

---

## 🔐 Security Notes

✅ **Webhook CSRF-exempt** — Telegram не отправляет CSRF token
✅ **TG Update验证** — Telegram подписывает все обновления
✅ **Токен в ENV** — НЕ хранится в коде
✅ **Секреты в .gitignore** — защищены
✅ **HTTPS only** — webhook работает только через HTTPS

---

## 📞 Support

Если что-то не работает:

1. **Проверьте логи:**
   ```bash
   railway logs -s django
   railway logs -s telegram-bot-setup
   railway logs -s celery
   ```

2. **Проверьте переменные:**
   ```bash
   railway var list
   ```

3. **Перезапустите сервисы:**
   ```bash
   railway redeploy --service django
   railway redeploy --service telegram-bot-setup
   ```

4. **Читайте документацию:**
   - `TELEGRAM_BOT_WEBHOOK_MIGRATION.md` — техническое описание
   - `TELEGRAM_BOT_WEBHOOK_QUICK_START.md` — быстрый старт
   - Railway docs: https://docs.railway.app

---

**Бот готов к production! 🚀**
