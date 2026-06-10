# 🚀 Telegram Bot Webhook — Quick Start Guide

## Что изменилось?

**ДО:** Бот запускался через polling (`:8001` порт, постоянное соединение)
**ПОСЛЕ:** Бот работает через webhook (получает updates от Telegram на `/telegram/webhook/`)

---

## Локальное тестирование (Development)

### Способ 1: С webhook (как в prod)
```bash
# Требует публичный HTTPS URL (ngrok или туннель)
export TELEGRAM_WEBHOOK_URL=https://abc123.ngrok.io/telegram/webhook/
docker compose up

# Проверить регистрацию
docker compose logs telegram-bot-setup
```

### Способ 2: С polling (для локальной разработки БЕЗ ngrok)
```bash
# Запустить основные сервисы
docker compose up -d db redis django celery celery-beat

# Запустить бота в polling режиме в отдельном терминале
docker compose exec django python manage.py telegram_run_polling

# Бот будет получать обновления через polling
# Отправляйте команды боту в Telegram — всё работает
```

---

## Production Deployment (Railway)

### 1. Переменные окружения
Добавить в Railway dashboard:
```
TELEGRAM_BOT_TOKEN=123456789:ABCDefgh...
TELEGRAM_BOT_USERNAME=YourBotName
TELEGRAM_WEBHOOK_URL=https://your-railway-domain.com/telegram/webhook/
```

### 2. Deploy
```bash
git push origin main
# Railway автоматически:
# 1. Собирает Docker образы
# 2. Запускает telegram-bot-setup
# 3. Регистрирует webhook
# 4. Запускает основное приложение
```

### 3. Проверка
```bash
# Логи регистрации webhook
railway logs -s telegram-bot-setup

# Проверить статус webhook
curl https://your-domain.com/telegram/webhook/
# Ответ: {"status": "ok", "bot_configured": true, "webhook_reachable_by_telegram": true}
```

---

## Архитектура

```
PRODUCTION:
  Telegram API → nginx → Django (:8000/telegram/webhook/) → python-telegram-bot → Celery

DEVELOPMENT (polling):
  Telegram API → polling ← management command → python-telegram-bot
```

---

## Файлы

| Файл | Назначение |
|------|-----------|
| `docker/telegram/Dockerfile` | Образ для webhook регистрации |
| `scripts/telegram_setup_webhook_init.sh` | Скрипт регистрации webhook |
| `docker-compose.yml` | Сервис telegram-bot-setup для dev |
| `docker-compose.prod.yml` | Сервис telegram-bot-setup для prod |
| `apps/telegram_bot/bot.py` | Webhook логика (не менялась) |
| `apps/telegram_bot/views.py` | TelegramWebhookView (не менялась) |

---

## Команды управления

```bash
# Регистрация webhook вручную
python manage.py telegram_setup_webhook

# Запуск бота в polling режиме (для локальной разработки)
python manage.py telegram_run_polling

# Проверка логов webhook
docker compose logs telegram-bot-setup

# Проверка статуса
curl http://localhost:8000/telegram/webhook/
```

---

## Возможные проблемы

| Проблема | Решение |
|----------|---------|
| "Cannot use local URL" | Используйте ngrok или polling режим |
| "Failed to register webhook" | Проверьте TELEGRAM_BOT_TOKEN и интернет |
| Бот не отвечает | Проверьте django логи и nginx конфиг |

---

**Больше информации:** см. `TELEGRAM_BOT_WEBHOOK_MIGRATION.md`
