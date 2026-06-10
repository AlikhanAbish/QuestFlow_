# 📋 Telegram Bot Railway Deploy — Финальный чек-лист

## ✅ ЧТО УЖЕ СДЕЛАНО

- ✅ Код бота написан и протестирован
- ✅ Webhook интеграция готова (вместо polling)
- ✅ Docker-compose конфигурация готова
- ✅ Celery + Celery-Beat интегрированы
- ✅ Static files исправлены
- ✅ Database конфигурация гибкая (DATABASE_URL + DB_*)
- ✅ Документация полная (4 файла)
- ✅ Git коммиты готовы к пушу

---

## 🚀 ДЕПЛОЙ НА RAILWAY (ТЫ ДЕЛАЕШЬ СЕЙЧАС)

### Шаг 1️⃣ : Получить Telegram Bot Token
```
Telegram → @BotFather → /mybots → /api_token
↓
Скопируй токен (формат: 123456789:ABCDefgh...)
```

### Шаг 2️⃣ : Railway Environment Variables
```
Railway Dashboard → Project → Settings → Environment
↓
Добавь переменные:

TELEGRAM_BOT_TOKEN=<ТВОЙ_ТОКЕН>
TELEGRAM_BOT_USERNAME=<имя_бота>
DATABASE_URL=<от Railway PostgreSQL plugin>  ИЛИ
DB_HOST=<адрес>
DB_USER=<юзер>
DB_PASSWORD=<пароль>
DB_NAME=questflow_db
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
```

### Шаг 3️⃣ : Add telegram-bot-setup Service
```
Railway Dashboard → New Service → Docker

Name: telegram-bot-setup
Dockerfile: docker/telegram/Dockerfile
Deploy
```

### Шаг 4️⃣ : После первого успешного деплоя Django
```
Когда Django Status = "Up" ✅

Railway сгенерирует домен: questflow-production.railway.app

Добавь переменную:
TELEGRAM_WEBHOOK_URL=https://questflow-production.railway.app/telegram/webhook/

Redeploy все сервисы
```

### Шаг 5️⃣ : Проверка регистрации Webhook
```bash
# Логи telegram-bot-setup:
railway logs -s telegram-bot-setup

# Ожидаемый результат:
# ✅ Webhook set to: https://questflow-production.railway.app/telegram/webhook/

# Тест в Telegram:
# Отправь боту: /start
# Бот должен ответить
```

---

## 📊 Что подключится автоматически

| Компонент | Статус | Интеграция |
|-----------|--------|-----------|
| Django | ✅ Слушает /telegram/webhook/ | Получает обновления от Telegram |
| Celery | ✅ Отправляет уведомления | Асинхронная отправка сообщений |
| Celery-Beat | ✅ Расписание | Ежедневные напоминания (09:00 UTC) |
| telegram-bot-setup | ✅ Регистрирует webhook | Выполняется один раз и выходит |
| nginx | ✅ Reverse proxy | Маршрутизирует на Django |

---

## 🔧 Команды для отладки

```bash
# Просмотр логов telegram-bot-setup
railway logs -s telegram-bot-setup --tail 50

# Просмотр всех переменных
railway var list

# Просмотр статуса сервиса
railway status

# Перезапуск сервиса (если он повис)
railway redeploy --service telegram-bot-setup

# SSH в контейнер
railway run --service django python manage.py shell

# Проверить webhook вручную
railway run --service django python manage.py telegram_setup_webhook
```

---

## 🚨 Troubleshooting (если что-то не работает)

### Проблема: "telegram-bot-setup" Exited with error
**Решение:**
1. Проверьте переменные: `railway var list`
2. Убедитесь что `DATABASE_URL` или `DB_*` установлены
3. Проверьте `TELEGRAM_BOT_TOKEN` верный
4. Посмотрите логи: `railway logs -s telegram-bot-setup --tail 100`

### Проблема: "Connection refused" на /telegram/webhook/
**Решение:**
1. Проверьте что django Status = "Up": `railway status`
2. Проверьте nginx логи: `railway logs -s nginx`
3. Перезапустите: `railway redeploy --service django`

### Проблема: Webhook не регистрируется
**Решение:**
1. Проверьте TELEGRAM_BOT_TOKEN верный
2. Проверьте что URL публичный HTTPS (не localhost)
3. Проверьте интернет соединение
4. Запустите вручную: `railway run --service django python manage.py telegram_setup_webhook`

### Проблема: Бот не отвечает на /start
**Решение:**
1. Проверьте что webhook зарегистрирована (логи telegram-bot-setup)
2. Проверьте celery работает: `railway logs -s celery | grep "Ready to accept"`
3. Проверьте бот токен в Telegram: `@BotFather → /mybots → информация`
4. Пошлите боту `/help` - должен ответить общей помощью

---

## 📞 Если всё равно не работает

**Сделайте сброс:**
```bash
# 1. Удалить webhook
railway run --service django python manage.py telegram_run_polling
# (это удалит webhook из Telegram)

# 2. Дождитесь выхода команды
Ctrl+C

# 3. Переустановить webhook
railway redeploy --service telegram-bot-setup

# 4. Проверить логи
railway logs -s telegram-bot-setup
```

---

## ✨ Результат

После всех шагов бот будет:
- ✅ Получать обновления через webhook (вместо polling)
- ✅ Отвечать на /start, /help, /profile, /tasks, /badges
- ✅ Отправлять уведомления через Celery
- ✅ Поддерживать аккаунт-линкинг через deep links
- ✅ Работать с ролевой системой (Employee/Manager/Admin)
- ✅ Отправлять расписанные напоминания

**Бот полностью ready для production! 🚀**

---

## 📚 Дополнительная документация

Если нужна более подробная информация:

1. **TELEGRAM_BOT_DEPLOYMENT_QUICK_STEPS.md** — 5 шагов (это вкратце)
2. **TELEGRAM_BOT_RAILWAY_DEPLOYMENT.md** — полный гайд (15KB)
3. **TELEGRAM_BOT_WEBHOOK_QUICK_START.md** — техническое описание
4. **TELEGRAM_BOT_WEBHOOK_MIGRATION.md** — как мы пришли к webhook

---

**Успехов с деплоем! 💪**
