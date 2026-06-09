Детальный план реализации Telegram-бота
1. Общая архитектура

Приложение: apps/telegram_bot
Библиотека: python-telegram-bot v21+
Рассылка: через Celery tasks
Хранение связи: модель TelegramUser
Метод подключения: Webhook

2. Модели (уже должно быть или нужно проверить)

TelegramUser (OneToOne с User)
telegram_id
username
is_active


3. Основные компоненты (по приоритету)
Этап 1: Базовая настройка бота

Создать/дополнить apps/telegram_bot/bot.py — инициализация Application
handlers.py — базовые команды (/start, /help, /profile)
views.py — Webhook view (/telegram/webhook/)
Настройка URL в config/urls.py
Добавление приложения в INSTALLED_APPS

Этап 2: Привязка аккаунта

Команда /start + генерация кода привязки или кнопка "Connect Account"
В профиле пользователя кнопка "Connect Telegram"
Сохранение telegram_id в модель TelegramUser

Этап 3: Основные уведомления (Celery)
Создать задачи в apps/telegram_bot/tasks.py:

send_daily_reminder() — 09:00 каждый день
send_assessment_reminder() — пятница 17:00
send_burnout_alert(user_id, new_status) — при изменении Burnout Score
send_level_up_notification()
send_real_reward_notification()
send_new_task_notification()

Этап 4: Команды бота

/profile — показать уровень, XP, streak, Burnout status
/tasks — список активных задач
/badges — полученные бейджи
Inline-кнопки для удобства

Этап 5: Интеграция с основным кодом

В GamificationEngine — после level up / badge вызывать Celery task
В Burnout calculator — при изменении статуса отправлять алерт
В TaskService — при создании задачи отправлять уведомление
В RealReward — уведомление о награде