# Brevo Email Setup на Railway

Этот документ описывает, как настроить отправку email через **Brevo API** на платформе Railway для надёжной доставки приглашений.

## 📋 Почему Brevo API, а не SMTP?

- **Надёжнее на Railway:** SMTP часто падает с `socket.gaierror` (DNS ошибка)
- **HTTP API:** Более стабилен, правильная обработка ошибок и retry logic
- **Масштабируемость:** Встроенная поддержка rate limiting и шаг-за-шагом статус трекинг
- **Отсутствие необходимости управлять соединениями:** HTTP request → готово

## 🚀 Пошаговая инструкция

### Шаг 1: Создать аккаунт Brevo (если ещё нет)

1. Перейти на https://www.brevo.com
2. Нажать "Start for free" (или "Sign up")
3. Заполнить форму (email, пароль, компания)
4. Подтвердить email
5. Выбрать план (Free плана достаточно для начала)

### Шаг 2: Получить API Key

1. Залогиниться на https://app.brevo.com
2. Перейти в **Settings** → **Account** → **API**
3. В разделе "SMTP & API" нажать на **"Create a new API key"**
4. Дать ему имя (например: "QuestFlow Production")
5. Скопировать полученный API key
6. **Сохранить его в безопасном месте!** (потом можно только переиздать)

### Шаг 3: Добавить и проверить Sender (отправителя)

**ВАЖНО:** Брево требует, чтобы адрес отправителя был **verified** (проверенным).

#### Вариант A: Использовать свой домен (Recommended)

1. Перейти на https://app.brevo.com/settings/senders-ip (Senders & IP)
2. Нажать **"Add a Sender"** (или **"Add a new sender"**)
3. Выбрать **"Domain"** (если у вас уже есть домен)
4. Ввести домен (например: `noreply.questflow.com`)
5. Брево выдаст DKIM records для добавления в DNS:
   ```
   v=DKIM1; k=rsa; p=MIGfMA0BgkqhkiG9w0BAQEFA...
   ```
6. Добавить эти DKIM records в DNS вашего домена (у вашего хостинга / Railway)
7. После добавления в DNS, вернуться в Брево и нажать **"Check DNS"**
8. Когда статус станет ✓ Verified, можно использовать любой адрес вида `*@questflow.com`

#### Вариант B: Использовать свой email (для тестирования)

1. Перейти на https://app.brevo.com/settings/senders-ip
2. Нажать **"Add a Sender"**
3. Выбрать **"Email"**
4. Ввести реальный email (например: `noreply@your-company-email.com`)
5. Брево отправит письмо на этот email с ссылкой подтверждения
6. Перейти по ссылке в письме для подтверждения
7. После подтверждения адрес будет verified и готов к использованию

### Шаг 4: Настроить переменные в Railway

1. Открыть проект на https://railway.app
2. Перейти в **Settings** → **Variables**
3. Добавить две переменные:

```
BREVO_API_KEY=<скопированный API key из шага 2>
DEFAULT_FROM_EMAIL="QuestFlow <noreply@questflow.com>"
```

**Примеры для DEFAULT_FROM_EMAIL:**
- `"QuestFlow <noreply@questflow.com>"` — с display name
- `"support@questflow.com"` — просто адрес
- `"Support Team <support@questflow.com>"` — другой display name
- Главное: адрес после `<>` или весь адрес должен быть **verified** в Brevo!

### Шаг 5: Перезапустить приложение на Railway

1. Перейти в **Deployments**
2. Нажать на последний деплой
3. Нажать **"Redeploy"** (или просто задеплоить новую версию из GitHub)
4. Дождаться завершения деплоя

### Шаг 6: Проверить что работает

1. Открыть приложение на Railway
2. Попытаться отправить приглашение сотруднику
3. Проверить логи на Railway (**Logs** → выбрать ваше приложение)
4. Ищите строки:
   ```
   Brevo API response: status=201 to=... (успех!)
   Email delivered via Brevo: ...
   ```

## 🔍 Диагностика проблем

### Ошибка: "Email service authentication failed (401)"
- **Причина:** Неправильный или истёкший API key
- **Решение:** 
  1. Перейти на https://app.brevo.com/settings/account/api
  2. Удалить старый API key
  3. Создать новый
  4. Обновить BREVO_API_KEY на Railway
  5. Перезапустить приложение

### Ошибка: "Email service error. Please try again (400+)"
- **Причина:** Часто это проблема с отправителем (DEFAULT_FROM_EMAIL)
- **Решение:**
  1. Убедиться что DEFAULT_FROM_EMAIL — это **verified sender** в Brevo
  2. Адрес **не должен содержать** `@smtp-brevo.com` или `@smtp-relay.brevo.com`
  3. Перейти на https://app.brevo.com/settings/senders-ip и проверить статус
  4. Если статус не ✓ Verified — выполнить верификацию (добавить DKIM или подтвердить email)

### Ошибка: "Could not reach email service"
- **Причина:** Network issue между Railway и Brevo API
- **Решение:**
  1. Проверить что Railway имеет интернет доступ
  2. Посмотреть логи на Railway (**Logs**)
  3. Убедиться что переменные BREVO_API_KEY и DEFAULT_FROM_EMAIL установлены
  4. Попробовать простой curl на Railway для проверки соединения

### Как проверить конфигурацию локально

```bash
# Убедиться что .env содержит:
cat .env | grep BREVO

# Должны выдать:
# BREVO_API_KEY=sk-xxx...
# DEFAULT_FROM_EMAIL=...

# Запустить test на Django shell
python manage.py shell

>>> from apps.notifications.services import BrevoEmailService
>>> service = BrevoEmailService()
>>> service.send_email(
...     subject="Test",
...     body_html="<p>Test email</p>",
...     to_email="test@example.com",
...     from_email="noreply@questflow.com",
... )
# Должно выдать: True (если успешно)
```

## 📝 Логирование

BrevoEmailService логирует все операции в приложение. На Railway логи видны в:
- **Railway Dashboard** → **Logs** → выбрать приложение
- **Фильтр:** Ищите `Brevo` или `Email`

Примеры полезных логов:
```
INFO: Brevo API response: status=201 to=user@example.com from=noreply@questflow.com subject='Welcome'
ERROR: Brevo API: Invalid API key (401). Check BREVO_API_KEY in .env
WARNING: Brevo API: Rate limit exceeded (429). Retry after delay.
```

## 🔐 Security Best Practices

1. **API Key:** Никогда не коммитить в Git
   - Только в `.env` файл (добавлен в `.gitignore`)
   - Или в переменные среды Railway/Heroku/etc
   
2. **DEFAULT_FROM_EMAIL:** Не использовать личные email адреса
   - Лучше создать dedicated email вида `noreply@company.com`
   - Или использовать domain sender через DKIM (более профессионально)

3. **DKIM Records:** Если используете domain sender
   - Убедиться что DKIM records корректно добавлены в DNS
   - Это улучшает deliverability и снижает chance что письма попадут в spam

## 📚 Полезные ссылки

- **Документация Brevo:** https://developers.brevo.com/
- **API Reference:** https://developers.brevo.com/reference/sendtransactionalemail
- **Управление Senders:** https://app.brevo.com/settings/senders-ip
- **API Keys:** https://app.brevo.com/settings/account/api
- **Railway Environment Variables:** https://docs.railway.app/develop/variables

## ✅ Чек-лист перед production

- [ ] Создан аккаунт Brevo и выбран план
- [ ] Получен BREVO_API_KEY из Brevo Settings
- [ ] Добавлен и verified sender (domain или email)
- [ ] BREVO_API_KEY добавлена в Railway Variables
- [ ] DEFAULT_FROM_EMAIL установлена в Railway Variables
- [ ] Приложение перезапущено на Railway
- [ ] Отправлено тестовое приглашение и получено письмо
- [ ] Проверены логи в Railway Dashboard
- [ ] API Key сохранена в secure месте (e.g. 1Password, LastPass)

## 🐛 Отладка на Railway

Если письмо не отправляется, проверить логи:

```
Railway Dashboard 
  → Deployments 
  → Latest Deployment 
  → Logs
  → (выбрать контейнер Django)
  → Поиск по "Brevo" или "Email"
```

Должны увидеть одну из этих строк:
- ✅ `Email delivered via Brevo: status=201` — письмо отправлено успешно
- ❌ `Brevo API: Invalid API key (401)` — неправильный API key
- ❌ `DEFAULT_FROM_EMAIL has invalid format` — неправильный формат адреса
- ❌ `Could not connect to email service` — network issue

---

**Если остались вопросы:** Проверить логи, убедиться что все переменные установлены, и если всё ещё не работает — контактировать поддержку Brevo через https://app.brevo.com (есть live chat).
