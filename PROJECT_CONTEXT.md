# PROJECT CONTEXT — QuestFlow (для ИИ-ассистентов)

**Проект:** Gamified Productivity Platform для удалённых и гибридных команд (B2B SaaS).

**Статус:** Почти завершён. Завтра предзащита диплома.

## 1. Основные документы проекта

- **Главное ТЗ:** `PROJECT_TZ.md` (полное техническое задание)
- **План проекта:** `PROJECT_PLAN.md`
- **Правила разработки:** `.agents/rules/questflow-rules.md`
- **Навыки/принципы:** `.agents/skills/`

**Инструкция:** При необходимости читай эти файлы для точного понимания требований.

## Ключевые архитектурные принципы (обязательно соблюдать)

- HTMX-first — все действия по возможности через HTML-over-the-wire
- Бизнес-логика только в `services.py` и `engine.py` (не в views)
- Все модели наследуются от `TimeStampedModel` / `SoftDeleteModel` из `core/`
- Privacy-first: Burnout Score виден только сотруднику и HR (manager_consent)
- Role-based access через `RoleRequiredMixin`
- Компания-тенантность (каждый пользователь привязан к `company`)

## Структура проекта (важные приложения)

- `apps/accounts` — User, роли, аутентификация, дашборды
- `apps/companies` — Company, Team, Invitation
- `apps/tasks` — Task, Comment, TaskService, Kanban
- `apps/gamification` — GamificationEngine, XP, Streak, Badges, Levels
- `apps/burnout` — MBICalculator, Self-assessment
- `apps/notifications` — In-app уведомления
- `apps/admin_panel` — Админка
- `apps/core` — mixins, base models, utils

**Остались проблемы:**
- Burnout Score — корректное отображение статуса на дашборде + история



## Что уже работает

- Отправка приглашений на реальную почту
- Геймификация (в основном)
- Burnout assessment
- Базовая структура и модели
- Manager Dashboard vs Employee Dashboard
- Права доступа Manager к задачам
- Кнопка "+ New Task"

## Важные фичи по ТЗ, которые нужно проверить / доработать:

- Система реальных наград:
    - Уведомление менеджера при достижении сотрудником уровней 10, 20, 30, 40, 50
    - Возможность менеджера выдавать реальную награду (Сертификат, Бонус, Выходной день, Кастомная)
    -Отображение выданных наград в профиле сотрудника

- Раздел «Достижения» — список полученных бейджей у пользователя
- Командный лидерборд (правильное отображение места пользователя)
- Burnout Score — корректное отображение статуса на дашборде + история
- Уведомления:
    - In-app уведомления (bell dropdown)
    - Telegram-бот: ежедневные утренние напоминания + алерты при изменении Burnout Score



**Инструкция для ИИ:**
Ты — Senior Django Architect, хорошо знакомый с проектом QuestFlow. 
Всегда учитывай принципы из ТЗ и `.agents/rules/questflow-rules.md`. 
При внесении изменений сохраняй чистоту архитектуры.
