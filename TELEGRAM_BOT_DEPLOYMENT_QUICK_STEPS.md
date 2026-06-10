# ⚡ Telegram Bot Railway Deployment — 5 шагов

## ШАГИ (в порядке выполнения)

### 1️⃣ Получить Telegram Bot Token
- Telegram → поиск @BotFather
- `/mybots` → выберите бота → `/api_token`
- Скопируйте токен

### 2️⃣ Установить переменные в Railway

**Dashboard → Project → Environment (или Settings → Environment)**

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCDefgh...
TELEGRAM_BOT_USERNAME=YourBotName
DATABASE_URL=postgresql://...  # или DB_HOST, DB_USER, DB_PASSWORD
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
```

**НЕ добавляйте TELEGRAM_WEBHOOK_URL пока!** (будет позже)

### 3️⃣ Добавить telegram-bot-setup сервис

**Вариант A (CLI):**
```bash
railway link  # если ещё не связаны
# Railway автоматически подхватит docker-compose.prod.yml
```

**Вариант B (Dashboard):**
1. New Service → Docker
2. Dockerfile: `docker/telegram/Dockerfile`
3. Deploy

### 4️⃣ После первого успешного деплоя

- Дождитесь `django` Status: "Up" ✅
- Railway сгенерирует домен: `questflow-production.railway.app`
- Добавьте новую переменную:
  ```
  TELEGRAM_WEBHOOK_URL=https://questflow-production.railway.app/telegram/webhook/
  ```
- Нажмите **Redeploy**

### 5️⃣ Проверьте регистрацию webhook

```bash
# Логи telegram-bot-setup
railway logs -s telegram-bot-setup

# Должно быть:
# ✅ Webhook set to: https://questflow-production.railway.app/telegram/webhook/

# Тест в Telegram:
# Отправьте боту /start → должен ответить
```

---

## 🔗 Связанные сервисы (уже подключены!)

| Сервис | Что делает | Статус |
|--------|-----------|--------|
| **django** | Слушает /telegram/webhook/ | ✅ Готов |
| **celery** | Отправляет уведомления в Telegram | ✅ Готов |
| **celery-beat** | Расписание (напоминания каждый день) | ✅ Готов |
| **telegram-bot-setup** | Регистрирует webhook при старте | ✅ Готов |

**Они уже интегрированы через:**
- Celery tasks в `apps/telegram_bot/tasks.py`
- Handlers в `apps/telegram_bot/handlers.py`
- Models в `apps/telegram_bot/models.py`

---

## ✅ Быстрая проверка

```bash
# 1. Статус webhook
curl https://questflow-production.railway.app/telegram/webhook/
# Ответ: {"status": "ok", "bot_configured": true, ...}

# 2. Логи
railway logs -s telegram-bot-setup | grep "Webhook"
# Должно быть: "Webhook set to: https://..."

# 3. В Telegram
# Отправить боту: /start
# Должен ответить

# 4. Админ-панель
# https://your-domain/admin → Account → Telegram
# Должна быть кнопка "Connect with Telegram"
```

---

## 🚨 Если что-то не работает

| Ошибка | Решение |
|--------|---------|
| "telegram-bot-setup Exited with error" | Проверьте `DATABASE_URL` и `TELEGRAM_BOT_TOKEN` |
| "Connection refused" на /telegram/webhook/ | Проверьте что `django` Status = "Up" |
| "Webhook set failed" | Проверьте интернет и что TOKEN верный |
| Бот не отвечает | Перезапустите `telegram-bot-setup`: redeploy |

---

**Полная документация:** см. `TELEGRAM_BOT_RAILWAY_DEPLOYMENT.md`
