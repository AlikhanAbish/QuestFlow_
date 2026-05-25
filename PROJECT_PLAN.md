# QuestFlow Project Plan

## 1. Общий roadmap (по неделям, 6 недель)
* **Неделя 1: Базовая инфраструктура и аутентификация**
  * Настройка проекта, Docker, CI/CD, Nginx, PostgreSQL, Celery, Redis.
  * Реализация `core` моделей и утилит.
  * Реализация базовых сущностей `accounts` (кастомная модель пользователя, регистрация, вход).
  * Реализация управления компаниями `companies` (создание команд, инвайты).
* **Неделя 2: Основной функционал Employee и Tasks (HTMX-first)**
  * Приложение `tasks`: CRUD задач, Kanban-доска, фильтрация.
  * Написание HTMX-views и partials для управления задачами без перезагрузки (изменение статусов, drag&drop).
  * Базовое меню и дашборд `Employee`.
* **Неделя 3: Система Геймификации**
  * Приложение `gamification`: XP, Streak, Levels, Badges.
  * Реализация `GamificationEngine` (engine.py) - начисление XP, проверка бейджей.
  * Интеграция геймификации с выполнением задач (Service-level).
* **Неделя 4: Выгорание (Burnout) и Manager интерфейс**
  * Приложение `burnout`: еженедельный assessment (сокращенный MBI), класс `MBICalculator`.
  * Интеграция Burnout Score в дашборды с Privacy-first подходом.
  * Интерфейс `Manager`: агрегированная статистика по команде, Kanban для команды.
* **Неделя 5: Уведомления, Telegram-бот и Аналитика**
  * Приложение `notifications`: In-app/Email уведомления. Реализация Bell dropdown через HTMX.
  * Приложение `telegram_bot`: интеграция, webhooks, расписание (Celery beat).
  * Приложение `analytics`: дашборды Manager (TeamAnalyticsView) с графиками (Chart.js + HTMX).
* **Неделя 6: Admin-панель, Полировка и Тестирование**
  * Приложение `Admin` интерфейсы: управление компаниями, юзерами, правилами геймификации.
  * Покрытие тестами (80%+ coverage для services/, engine.py, calculator.py).
  * Настройка Production Docker Compose с Nginx, SSL, Gunicorn.

## 2. Список Django-приложений
(В точности по разделу 3.1 ТЗ)
1. **accounts**: Кастомная модель User, авторизация, роли, профили
2. **companies**: Модели Company, Team, Invitation, управление участниками
3. **tasks**: Task, Comment, история изменений, Kanban, фильтры
4. **gamification**: XP, уровни, бейджи, streak, GamificationEngine, правила
5. **burnout**: Self-assessment формы (MBI), расчёт BurnoutScore, история
6. **notifications**: In-app и email уведомления, шаблоны, Celery-задачи
7. **telegram_bot**: Telegram-бот: handlers, webhook, Celery-задачи рассылки
8. **analytics**: Агрегированные отчёты для Manager и Admin
9. **core**: Базовые абстрактные модели, утилиты, middleware

## 3. Приоритет разработки
Разработка будет вестись поступательно от базовых нужд сотрудника к административным функциям.
1. **Employee (First Priority)**
   * Личный кабинет, управление своими задачами, геймификация, Streak-система и еженедельная форма MBI (уровень рядового пользователя).
2. **Manager (Second Priority)**
   * Интерфейс для создания/распределения задач, командный Kanban, выдача наград (Milestone Rewards), аналитика команды, командный Burnout без персонализации (пока не получено `manager_consent`).
3. **Admin (Third Priority)**
   * CRUD компаний, пользователей, управление правилами геймификации и бейджами, Audit Log и Telegram настройки.

## 4. Таблица всех URL (HTMX-first)

| M | URL Pattern | View / Partial | Описание |
| :--- | :--- | :--- | :--- |
| **GET** | / | HomeView | Landing page / redirect to dashboard |
| **GET** | /login/ | LoginView | Страница входа |
| **POST** | /login/ | LoginView | Обработка формы входа |
| **POST** | /logout/ | LogoutView | Выход из системы |
| **GET** | /register/ | RegisterView | Регистрация по invite-токену |
| **POST** | /register/ | RegisterView | Создание аккаунта |
| **GET** | /password/reset/ | PasswordResetView | Запрос сброса пароля |
| **POST** | /password/reset/ | PasswordResetView | Отправка письма сброса |
| **GET** | /password/reset/confirm/\<uid\>/\<token\>/ | PasswordResetConfirmView | Форма нового пароля |
| **GET** | /profile/ | ProfileView | Личный профиль пользователя |
| **POST** | /profile/update/ | ProfileUpdateView | HTMX: обновление профиля |
| **POST** | /profile/telegram/connect/ | TelegramConnectView | HTMX: привязка Telegram |
| **GET** | /dashboard/ | EmployeeDashboardView | Главная Employee: XP, streak, задачи |
| **GET** | /dashboard/manager/ | ManagerDashboardView | Главная Manager: обзор команды |
| **GET** | /dashboard/xp-counter/ | XPCounterPartialView | HTMX partial: актуальный XP и уровень |
| **GET** | /dashboard/leaderboard/ | LeaderboardPartialView | HTMX partial: командный лидерборд |
| **GET** | /dashboard/burnout-badge/ | BurnoutBadgePartialView | HTMX partial: burnout статус |
| **GET** | /tasks/ | TaskListView | Список задач (с фильтрами) |
| **GET** | /tasks/kanban/ | TaskKanbanView | Kanban-доска |
| **GET** | /tasks/create/ | TaskCreateView | Форма создания задачи (Manager) |
| **POST** | /tasks/create/ | TaskCreateView | HTMX: создать задачу и вернуть карточку |
| **GET** | /tasks/\<id\>/ | TaskDetailView | Детальная страница задачи |
| **POST** | /tasks/\<id\>/update/ | TaskUpdateView | HTMX: обновить задачу |
| **POST** | /tasks/\<id\>/delete/ | TaskDeleteView | HTMX: удалить задачу |
| **POST** | /tasks/\<id\>/status/ | TaskStatusUpdateView | HTMX: изменить статус задачи |
| **POST** | /tasks/\<id\>/comment/ | TaskCommentView | HTMX: добавить комментарий |
| **GET** | /tasks/\<id\>/comments/ | TaskCommentsPartialView | HTMX partial: список комментариев |
| **GET** | /tasks/export/csv/ | TaskExportCSVView | Экспорт задач в CSV (Manager) |
| **GET** | /tasks/filter/partial/ | TaskFilterPartialView | HTMX: фильтрованный список задач |
| **GET** | /gamification/profile/\<user_id\>/ | GamificationProfileView | Профиль геймификации пользователя |
| **GET** | /gamification/badges/ | BadgeListView | Все доступные бейджи |
| **GET** | /gamification/leaderboard/ | LeaderboardView | Полный лидерборд команды |
| **GET** | /gamification/level-up/partial/ | LevelUpPartialView | HTMX partial: анимация level-up |
| **POST** | /gamification/reward/grant/ | GrantRewardView | Manager: выдать реальную награду |
| **GET** | /gamification/rewards/history/ | RewardHistoryView | История реальных наград |
| **GET** | /burnout/assessment/ | BurnoutAssessmentView | Форма еженедельного self-assessment |
| **POST** | /burnout/assessment/submit/ | BurnoutAssessmentSubmitView | HTMX: отправить MBI-форму |
| **GET** | /burnout/history/ | BurnoutHistoryView | История burnout-оценок (только Employee) |
| **GET** | /burnout/team/summary/ | TeamBurnoutSummaryView | Manager: агрегированный burnout команды |
| **POST** | /burnout/consent/toggle/ | BurnoutConsentToggleView | HTMX: вкл/выкл согласие на показ менеджеру |
| **GET** | /company/settings/ | CompanySettingsView | Настройки компании (Manager/Admin) |
| **POST** | /company/settings/update/ | CompanyUpdateView | HTMX: обновить настройки компании |
| **GET** | /team/members/ | TeamMembersView | Список участников команды |
| **POST** | /team/invite/ | InviteUserView | Отправить invite по email |
| **GET** | /invite/\<token\>/ | AcceptInviteView | Принять приглашение |
| **POST** | /team/members/\<id\>/role/ | UpdateMemberRoleView | HTMX: изменить роль участника |
| **POST** | /team/members/\<id\>/remove/ | RemoveMemberView | HTMX: удалить из команды |
| **GET** | /analytics/team/ | TeamAnalyticsView | Manager: дашборд аналитики команды |
| **GET** | /analytics/team/tasks-chart/ | TasksChartPartialView | HTMX partial: chart выполнения задач |
| **GET** | /analytics/team/xp-chart/ | XPChartPartialView | HTMX partial: chart XP команды |
| **GET** | /analytics/team/burnout-trend/ | BurnoutTrendPartialView | HTMX partial: тренд burnout |
| **GET** | /notifications/ | NotificationsListView | Список in-app уведомлений |
| **GET** | /notifications/partial/ | NotificationsPartialView | HTMX partial: bell dropdown |
| **POST** | /notifications/\<id\>/read/ | MarkNotificationReadView | HTMX: пометить как прочитанное |
| **POST** | /notifications/read-all/ | MarkAllReadView | HTMX: все прочитаны |
| **GET** | /admin-panel/ | AdminDashboardView | Admin: главная панель |
| **GET** | /admin-panel/companies/ | AdminCompanyListView | Admin: список компаний |
| **POST** | /admin-panel/companies/create/ | AdminCompanyCreateView | Admin: создать компанию |
| **GET** | /admin-panel/companies/\<id\>/ | AdminCompanyDetailView | Admin: детали компании |
| **POST** | /admin-panel/companies/\<id\>/deactivate/ | AdminCompanyDeactivateView | Admin: деактивировать компанию |
| **GET** | /admin-panel/users/ | AdminUserListView | Admin: список всех пользователей |
| **POST** | /admin-panel/users/\<id\>/role/ | AdminUserRoleView | Admin: сменить роль |
| **POST** | /admin-panel/users/\<id\>/deactivate/ | AdminUserDeactivateView | Admin: деактивировать пользователя |
| **GET** | /admin-panel/gamification/ | AdminGamificationSettingsView | Admin: настройки геймификации |
| **POST** | /admin-panel/gamification/rules/ | AdminGamificationRulesUpdateView | Admin: обновить XP-правила |
| **GET** | /admin-panel/gamification/badges/ | AdminBadgeListView | Admin: управление бейджами |
| **POST** | /admin-panel/gamification/badges/create/ | AdminBadgeCreateView | Admin: создать бейдж |
| **GET** | /admin-panel/audit-log/ | AdminAuditLogView | Admin: системный audit log |
| **GET** | /telegram/webhook/ | TelegramWebhookView | Webhook для Telegram-бота |

## 5. Список всех моделей с полями (Высокоуровнево)

**Core (Абстрактные модели)**
* `TimeStampedModel`: `created_at`, `updated_at`
* `SoftDeleteModel`: наследует от TimeStampedModel + `is_deleted`, `deleted_at`

**Accounts**
* `User`: (AbstractBaseUser, PermissionsMixin) `email`, `username`, `first_name`, `last_name`, `role`, `company`, `team`, `is_active`, `is_staff`, `date_joined`, `avatar`

**Companies**
* `Company`: `name`, `slug`, `owner`, `max_users`, `is_active`, `settings` (учитывает `SoftDeleteModel`)
* `Team`: `name`, `company`, `manager`
* `Invitation`: `email`, `company`, `team`, `invited_by`, `token`, `role`, `is_accepted`, `expires_at`

**Tasks**
* `Task`: `title`, `description`, `company`, `team`, `created_by`, `assigned_to`, `status` (todo, in_progress, done, overdue), `priority` (1-4), `deadline`, `completed_at` (учитывает `SoftDeleteModel`)
* `Comment`: `task`, `author`, `body`
* `TaskHistory`: `task`, `changed_by`, `field_name`, `old_value`, `new_value`

**Gamification**
* `GamificationRule`: `company` (null=глобальное), `action`, `xp_reward`, `is_active`
* `UserLevel`: `user` (OneToOne), `level`, `total_xp`, `weekly_xp`
* `XPTransaction`: `user`, `amount`, `action`, `related_task`, `note`
* `Streak`: `user`, `current`, `longest`, `last_active`
* `Badge`: `name`, `description`, `icon`, `trigger`, `trigger_value`, `is_active`
* `UserBadge`: `user`, `badge`
* `RealReward`: `recipient`, `granted_by`, `reward_type`, `description`, `milestone_level`

**Burnout**
* `AssessmentForm`: `user`, `week_number`, `year`, `ex1, ex2, ex3` (Exhaustion), `cy1, cy2, cy3` (Cynicism), `ef1, ef2, ef3` (Efficacy), `tasks_completion_rate`
* `BurnoutScore`: `user`, `score` (Green, Yellow, Red), `last_calculated`, `exhaustion_avg`, `cynicism_avg`, `efficacy_avg`, `manager_consent`

**Notifications**
* `Notification`: `recipient`, `type`, `title`, `body`, `is_read`, `action_url`, `metadata`
* `TelegramUser`: `user`, `telegram_id`, `username`, `is_active`

## 6. Список задач для агентов (разбито по приложениям + зависимости)

| ID | Application / Domain | Описание задачи | Зависимости |
| :-- | :-- | :-- | :-- |
| A1 | **Core & Auth Setup** | Инициализация Django 5.1 с Tailwind CSS. Написать базовые модели в `core`. Приложение `accounts` с моделью `User`, кастомной аутентификацией. Приложение `companies` (`Company`, `Team`, `Invitation`). | None |
| A2 | **Base Templates & UI** | Настройка `base.html`, подключить HTMX, Alpine.js. Верстка Login/Register (Alpine + HTMX-first). Базовые layout для ролей. | A1 |
| A3 | **Tasks (HTMX First)** | Приложение `tasks`. Модели. Создание HTMX-сервисов (`services.py`). Views (partial/full render). Канбан доска (Sortable.js+HTMX). | A1, A2 |
| A4 | **Gamification Logic** | Приложение `gamification`. Модели, правила. Написать `engine.py` (`GamificationEngine`). Интегрировать с выполнением `Task` в сервисе `TaskService`. Написать тесты (coverage 80%+). | A3 |
| A5 | **Burnout Tracking** | Приложение `burnout`. Форма MBI + HTMX submit. Написание логики в `calculator.py`. Дашборды лояльности (`manager_consent`). | A2 |
| A6 | **Manager / Analytics** | Приложение `analytics`. Дашборды, Chart.js визуализации, экспорт в CSV. Разделение скоупов команд (RoleRequiredMixin). | A3, A4, A5 |
| A7 | **Notifications & Async**| Настройка Celery + Redis. Приложение `notifications` (bell widget HTMX). Приложение `telegram_bot` (Celery Tasks, Handlers). Уведомления об XP/Level/Burnout. | A4, A5 |
| A8 | **Admin Panel & Polish** | Admin Views для управления Company, Rules, Users. Настройка Docker/Nginx/CeleryBeat. Финальный рефакторинг и доведение тестов (>80%). | A6, A7 |

## 7. Checklist соответствия ТЗ

- [ ] **Архитектура проекта:** Соблюдено дерево папок из `3.2` (папки `config/`, `apps/`, `templates/`, `static/` и т.д.).
- [ ] **Data Моделирование:** Все сущности наследуются от `core.models.TimeStampedModel` или `core.models.SoftDeleteModel`.
- [ ] **HTMX & Alpine.js:** Вся интерактивность идет через HTMX с проверкой `if request.htmx` во view, Alpine.js используется только для клиентского стейта (дропдауны/табы/нативные всплывающие окна).
- [ ] **Privacy-First (Burnout):** `BurnoutScore` виден только самому пользователю/HR; он виден Менеджеру только при `manager_consent=True`.
- [ ] **Business Logic:** Соблюдено разделение — вся логика в `services.py`, расчет выгорания строго в `burnout/calculator.py`, а правила XP в `gamification/engine.py`.
- [ ] **Gamification Formula:** Уровень вычисляется по формуле: пороги XP растут как `level * 500`. Реализация `Streak` системы (+10% бонус XP). Выдаются реальные награды (уровни 10, 20, 30, 40, 50).
- [ ] **Аутентификация & RBAC:** Изоляция пользователей друг от друга по `Company` (разные компании не видят чужие таски), использование `RoleRequiredMixin`.
- [ ] **MBI Algorithm:** 9 вопросов для Employee по 3-м шкалам оценкой 0-6. Вычисляется статус Green/Yellow/Red, учитывается `tasks_completion_rate`.
- [ ] **Инфраструктура:** Использование Django 5.1 и пакетов из `8.1`. Минимум 80% coverage тестами для ключевых классов (`services/`, `engine.py`, `calculator.py`).
