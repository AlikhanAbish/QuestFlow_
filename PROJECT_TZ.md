

**ТЕХНИЧЕСКОЕ ЗАДАНИЕ**

на разработку B2B SaaS-платформы

**QuestFlow**

*Gamified Productivity Platform for Remote & Hybrid Teams*

| Версия документа | 1.0.0 — Апрель 2026 |
| :---- | :---- |
| **Статус** | Draft — Ready for Development |
| **Проект** | QuestFlow B2B SaaS Platform |
| **Технологии** | Django · PostgreSQL · Redis · HTMX · Alpine.js · Tailwind CSS |
| **Целевая аудитория** | Удалённые и гибридные команды 10–100 человек |

# **1\. Общее описание проекта**

## **1.1 Назначение и цели**

QuestFlow — это B2B SaaS веб\-платформа для удалённых и гибридных команд численностью от 10 до 100 сотрудников. Платформа геймифицирует ежедневную рабочую деятельность, превращая выполнение задач в увлекательный игровой процесс с элементами прогрессии, конкуренции и наград.

**Ключевые цели платформы:**

* Повышение дисциплины и вовлечённости сотрудников через механики геймификации

* Проактивное выявление риска профессионального выгорания через анализ активности и еженедельный self-assessment (MBI)

* Предоставление менеджерам инструментов для создания, назначения и отслеживания задач

* Обеспечение privacy-first подхода: данные burnout видны только сотруднику и HR

* Простота внедрения: онбординг команды за один рабочий день

## **1.2 Целевая аудитория**

| Роль | Описание | Основные задачи в системе |
| :---- | :---- | :---- |
| **Employee** | Рядовой сотрудник команды | Выполнение задач, прогресс по уровням, еженедельный self-assessment |
| **Manager / Team Lead** | Руководитель команды | Создание задач, управление командой, просмотр burnout-отчётов, выдача наград |
| **Admin** | Системный администратор | Управление компаниями, пользователями, правилами геймификации |

## **1.3 Ключевые метрики успеха**

* Retention Rate: 80%+ пользователей активны спустя 30 дней после регистрации

* Engagement Rate: 70%+ сотрудников заходят на платформу ежедневно

* Burnout Detection: точность классификации \>= 85% на основе MBI

* Onboarding Time: полная настройка компании менее 4 часов

* Uptime: \>= 99.5% SLA

# **2\. Функциональные требования по ролям**

## **2.1 Employee (Сотрудник)**

### **2.1.1 Личный кабинет (Dashboard)**

* Отображение текущего уровня (1–50), прогресс-бар до следующего уровня

* Счётчик очков (XP): общий и за текущую неделю

* Streak-счётчик: количество дней подряд, когда сотрудник заходил и выполнял задачи

* Статус Burnout Score (Зелёный / Жёлтый / Красный) — только для текущего пользователя

* Список активных задач с дедлайнами, приоритетами и статусами

* Раздел «Достижения»: список полученных бейджей с датами

* Место в командном лидерборде (топ-10 с выделением своей позиции)

### **2.1.2 Управление задачами**

* Просмотр назначенных задач с фильтрацией по статусу (To Do, In Progress, Done, Overdue)

* Изменение статуса задачи через HTMX без перезагрузки страницы

* Просмотр деталей задачи: описание, дедлайн, приоритет, назначенный менеджер

* Комментирование задачи

* При выполнении задачи — автоматическое начисление XP с анимацией

### **2.1.3 Геймификация**

* Очки (XP): начисляются за выполнение задач в срок (+100 XP), досрочное выполнение (+150 XP), комментарии (+10 XP), ежедневный вход (+20 XP)

* Streak: за каждый день подряд активности бонус \+10% к XP. Streak сбрасывается при пропуске дня

* Уровни (1–50): пороги XP растут по формуле level \* 500\. Level 1 \= 0 XP, Level 2 \= 500 XP, Level 3 \= 1500 XP...

* Бейджи: автоматически выдаются за достижения (первая задача, первый streak 7 дней, топ-3 лидерборда и др.)

* На уровнях 10, 20, 30, 40, 50 — менеджер получает уведомление о возможности выдать реальную награду

### **2.1.4 Weekly Self-Assessment (Burnout Check)**

* Каждый понедельник сотруднику доступна форма из 9 вопросов (сокращённый MBI: 3 вопроса на Exhaustion, 3 на Cynicism, 3 на Efficacy)

* Шкала ответов: 0–6 (Never → Every day)

* После отправки: автоматический расчёт Burnout Score и обновление статуса

* Если форма не заполнена до пятницы 18:00 — Telegram-бот отправляет напоминание

* Пропуск 2+ недель подряд автоматически повышает Burnout Score на одну категорию

### **2.1.5 Уведомления**

* Email-уведомления: еженедельный отчёт по прогрессу, напоминание о self-assessment

* Telegram-бот: ежедневное утреннее напоминание о входе, алерт при изменении Burnout Score

* In-app уведомления (bell icon): новые задачи, достижения, награды от менеджера

## **2.2 Manager / Team Lead**

### **2.2.1 Управление командой**

* Просмотр списка сотрудников своей команды

* Приглашение новых сотрудников по email (с автогенерацией invite-токена)

* Смена роли сотрудника (Employee ↔ Manager) с подтверждением

* Просмотр профиля сотрудника: уровень, XP, streak, список задач, история бейджей

* Burnout Score агрегированный по команде (анонимизированный): % Зелёных / Жёлтых / Красных без имён

* Детальный Burnout Score конкретного сотрудника — только если сотрудник дал явное согласие в настройках

### **2.2.2 Таск-трекер**

* Создание задачи: название (обяз.), описание, дедлайн, приоритет (Low/Medium/High/Critical), назначение на сотрудника(ов)

* Редактирование и удаление задач (только своих)

* Просмотр задач в формате: список и Kanban-доска (4 колонки: To Do / In Progress / Done / Overdue)

* Фильтрация по сотруднику, приоритету, статусу, дедлайну

* Bulk-действия: перенос дедлайна, смена статуса нескольких задач

* Экспорт задач в CSV

### **2.2.3 Аналитика и отчёты**

* Dashboard метрики: % задач выполнено в срок за последние 30 дней, среднее время выполнения задачи, активность по дням недели

* График динамики XP команды за 30/90 дней

* Рейтинг вовлечённости: топ-активные и наименее активные сотрудники

* Burnout Trend: изменение статусов по неделям (агрегированно)

### **2.2.4 Система наград**

* При достижении сотрудником уровней 10, 20, 30, 40, 50 — менеджеру приходит уведомление

* Менеджер может выдать «Реальную награду» через форму: выбор типа (Сертификат, Бонус, Выходной день, Кастомная), описание

* Награда отображается в профиле сотрудника и добавляет специальный бейдж

* История всех выданных наград в разделе «Rewards»

## **2.3 Admin (Системный администратор)**

### **2.3.1 Управление компаниями**

* CRUD для компаний: создание, редактирование, деактивация

* Просмотр статистики по компании: кол-во пользователей, активность, burnout-сводка

* Настройка лимитов тарифа: макс. кол-во пользователей, доступные функции

* Экспорт данных компании в JSON/CSV (GDPR-совместимый)

### **2.3.2 Управление пользователями**

* Поиск и просмотр всех пользователей системы

* Смена роли, деактивация/активация аккаунта

* Принудительный сброс пароля

* Просмотр audit log действий пользователя

### **2.3.3 Настройка правил геймификации**

* Редактирование таблицы XP: сколько очков за каждое действие

* Управление бейджами: создание, редактирование, привязка к триггерам

* Настройка порогов уровней

* Управление milestone-уровнями для реальных наград (по умолчанию: 10, 20, 30, 40, 50\)

### **2.3.4 Системные настройки**

* Управление Telegram-ботом: токен, шаблоны сообщений

* Email-шаблоны: редактирование HTML/текстовых шаблонов уведомлений

* Просмотр Celery-очередей и статуса задач (интеграция с Flower)

* Системный audit log: все admin-действия с timestamp и IP

# **3\. Структура проекта**

## **3.1 Рекомендуемые Django-приложения**

| Django App | Ответственность |
| :---- | :---- |
| **accounts** | Кастомная модель User, авторизация, роли, профили |
| **companies** | Модели Company, Team, Invitation, управление участниками |
| **tasks** | Task, Comment, история изменений, Kanban, фильтры |
| **gamification** | XP, уровни, бейджи, streak, GamificationEngine, правила |
| **burnout** | Self-assessment формы (MBI), расчёт BurnoutScore, история |
| **notifications** | In-app и email уведомления, шаблоны, Celery-задачи |
| **telegram\_bot** | Telegram-бот: handlers, webhook, Celery-задачи рассылки |
| **analytics** | Агрегированные отчёты для Manager и Admin |
| **core** | Базовые абстрактные модели, утилиты, middleware |

## **3.2 Дерево папок проекта**

questflow/

├── config/                    \# Django project settings

│   ├── \_\_init\_\_.py

│   ├── settings/

│   │   ├── \_\_init\_\_.py

│   │   ├── base.py            \# Common settings

│   │   ├── development.py     \# Dev overrides

│   │   └── production.py      \# Prod overrides

│   ├── urls.py                \# Root URL configuration

│   ├── wsgi.py

│   └── asgi.py                \# For Django Channels

│

├── apps/

│   ├── accounts/              \# Auth, User mod

│   │   ├── models.py          \# User, UserProfile, Rel, rolesole

│   │   ├── views.py

│   │   ├── urls.py

│   │   ├── forms.py

│   │   ├── signals.py

│   │   ├── managers.py        \# Custom UserManager

│   │   ├── mixins.py          \# RoleRequiredMixin, etc.

│   │   ├── admin.py

│   │   └── tests/

│   │

│   ├── companies/             \# Company & Team management

│   │   ├── models.py          \# Company, Team, Invitation

│   │   ├── views.py

│   │   ├── urls.py

│   │   ├── services.py        \# InvitationService

│   │   └── tests/

│   │

│   ├── tasks/                 \# Task tracker

│   │   ├── models.py          \# Task, Comment, TaskHistory

│   │   ├── views.py           \# HTMX-powered views

│   │   ├── urls.py

│   │   ├── forms.py

│   │   ├── services.py        \# TaskService

│   │   ├── filters.py         \# django-filter

│   │   └── tests/

│   │

│   ├── gamification/          \# XP, Levels, Badges, Streaks

│   │   ├── models.py          \# XPTransaction, Badge, UserBadge,

│   │   │                      \# UserLevel, Streak, GamificationRule

│   │   ├── engine.py          \# GamificationEngine (core logic)

│   │   ├── signals.py         \# Event hooks

│   │   ├── services.py        \# LevelUpService, BadgeService

│   │   ├── views.py

│   │   ├── urls.py

│   │   └── tests/

│   │

│   ├── burnout/               \# Burnout tracking & MBI

│   │   ├── models.py          \# AssessmentForm, BurnoutScore

│   │   ├── calculator.py      \# MBICalculator

│   │   ├── views.py

│   │   ├── urls.py

│   │   ├── forms.py

│   │   └── tests/

│   │

│   ├── notifications/         \# In-app \+ Email notifications

│   │   ├── models.py          \# Notification, NotificationTemplate

│   │   ├── services.py        \# NotificationService

│   │   ├── tasks.py           \# Celery tasks for notifications

│   │   ├── views.py

│   │   └── tests/

│   │

│   ├── telegram\_bot/          \# Telegram bot integration

│   │   ├── bot.py             \# python-telegram-bot setup

│   │   ├── handlers.py        \# Command & message handlers

│   │   ├── tasks.py           \# Celery tasks for bot messages

│   │   ├── models.py          \# TelegramUser

│   │   └── tests/

│   │

│   ├── analytics/             \# Manager & Admin analytics

│   │   ├── services.py        \# AnalyticsService

│   │   ├── views.py

│   │   ├── urls.py

│   │   └── tests/

│   │

│   └── core/                  \# Shared utilities

│       ├── models.py          \# TimeStampedModel, SoftDeleteModel

│       ├── mixins.py

│       ├── utils.py

│       ├── constants.py

│       └── middleware.py      \# SecurityHeadersMiddleware

│

├── templates/

│   ├── base.html              \# Base layout with HTMX

│   ├── partials/              \# HTMX fragments

│   │   ├── \_task\_card.html

│   │   ├── \_xp\_counter.html

│   │   ├── \_leaderboard.html

│   │   ├── \_burnout\_badge.html

│   │   └── \_notifications.html

│   ├── accounts/

│   ├── tasks/

│   ├── gamification/

│   ├── burnout/

│   ├── analytics/

│   └── admin\_panel/

│

├── static/

│   ├── css/

│   │   └── tailwind.css       \# Compiled Tailwind CSS

│   ├── js/

│   │   ├── alpine.js          \# Alpine.js bundle

│   │   ├── htmx.js

│   │   └── app.js             \# Custom JS (animations, etc.)

│   └── img/

│       ├── badges/            \# Badge icons

│       └── levels/            \# Level icons

│

├── media/                     \# User-uploaded files

│

├── tests/                     \# Integration & E2E tests

│   ├── conftest.py

│   └── test\_flows/            \# User journey tests

│

├── docker/

│   ├── nginx/

│   │   ├── nginx.conf

│   │   └── Dockerfile

│   ├── django/

│   │   └── Dockerfile

│   └── celery/

│       └── Dockerfile

│

├── scripts/

│   ├── entrypoint.sh

│   └── wait\_for\_db.sh

│

├── .env.example

├── docker-compose.yml

├── docker-compose.prod.yml

├── pyproject.toml             \# Dependencies via pip (requirements.txt)

├── manage.py

└── README.md

# **4\. Полный список URL-адресов**

Все URL-адреса следуют принципу HTML-over-the-wire: POST/HTMX-запросы возвращают HTML-фрагменты (partials), а не JSON. Полноценные страницы возвращаются только на GET-запросы.

## **4.1 Auth & Accounts**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
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

## **4.2 Dashboard**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
| **GET** | /dashboard/ | EmployeeDashboardView | Главная Employee: XP, streak, задачи |
| **GET** | /dashboard/manager/ | ManagerDashboardView | Главная Manager: обзор команды |
| **GET** | /dashboard/xp-counter/ | XPCounterPartialView | HTMX partial: актуальный XP и уровень |
| **GET** | /dashboard/leaderboard/ | LeaderboardPartialView | HTMX partial: командный лидерборд |
| **GET** | /dashboard/burnout-badge/ | BurnoutBadgePartialView | HTMX partial: burnout статус |

## **4.3 Tasks**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
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

## **4.4 Gamification**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
| **GET** | /gamification/profile/\<user\_id\>/ | GamificationProfileView | Профиль геймификации пользователя |
| **GET** | /gamification/badges/ | BadgeListView | Все доступные бейджи |
| **GET** | /gamification/leaderboard/ | LeaderboardView | Полный лидерборд команды |
| **GET** | /gamification/level-up/partial/ | LevelUpPartialView | HTMX partial: анимация level-up |
| **POST** | /gamification/reward/grant/ | GrantRewardView | Manager: выдать реальную награду |
| **GET** | /gamification/rewards/history/ | RewardHistoryView | История реальных наград |

## **4.5 Burnout**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
| **GET** | /burnout/assessment/ | BurnoutAssessmentView | Форма еженедельного self-assessment |
| **POST** | /burnout/assessment/submit/ | BurnoutAssessmentSubmitView | HTMX: отправить MBI-форму |
| **GET** | /burnout/history/ | BurnoutHistoryView | История burnout-оценок (только Employee) |
| **GET** | /burnout/team/summary/ | TeamBurnoutSummaryView | Manager: агрегированный burnout команды |
| **POST** | /burnout/consent/toggle/ | BurnoutConsentToggleView | HTMX: вкл/выкл согласие на показ менеджеру |

## **4.6 Companies & Teams**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
| **GET** | /company/settings/ | CompanySettingsView | Настройки компании (Manager/Admin) |
| **POST** | /company/settings/update/ | CompanyUpdateView | HTMX: обновить настройки компании |
| **GET** | /team/members/ | TeamMembersView | Список участников команды |
| **POST** | /team/invite/ | InviteUserView | Отправить invite по email |
| **GET** | /invite/\<token\>/ | AcceptInviteView | Принять приглашение |
| **POST** | /team/members/\<id\>/role/ | UpdateMemberRoleView | HTMX: изменить роль участника |
| **POST** | /team/members/\<id\>/remove/ | RemoveMemberView | HTMX: удалить из команды |

## **4.7 Analytics**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
| **GET** | /analytics/team/ | TeamAnalyticsView | Manager: дашборд аналитики команды |
| **GET** | /analytics/team/tasks-chart/ | TasksChartPartialView | HTMX partial: chart выполнения задач |
| **GET** | /analytics/team/xp-chart/ | XPChartPartialView | HTMX partial: chart XP команды |
| **GET** | /analytics/team/burnout-trend/ | BurnoutTrendPartialView | HTMX partial: тренд burnout |

## **4.8 Notifications**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
| **GET** | /notifications/ | NotificationsListView | Список in-app уведомлений |
| **GET** | /notifications/partial/ | NotificationsPartialView | HTMX partial: bell dropdown |
| **POST** | /notifications/\<id\>/read/ | MarkNotificationReadView | HTMX: пометить как прочитанное |
| **POST** | /notifications/read-all/ | MarkAllReadView | HTMX: все прочитаны |

## **4.9 Admin Panel**

| M | URL Pattern | View / Partial | Описание |
| :---- | :---- | :---- | :---- |
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

# **5\. Модели Django (высокоуровневый дизайн)**

Все модели наследуются от базовых абстрактных классов из apps/core/models.py. Ниже приведены ключевые поля и связи.

## **5.1 Core (Базовые абстрактные модели)**

\# apps/core/models.py

class TimeStampedModel(models.Model):

    created\_at \= models.DateTimeField(auto\_now\_add=True)

    updated\_at \= models.DateTimeField(auto\_now=True)

    class Meta: abstract \= True

class SoftDeleteModel(TimeStampedModel):

    is\_deleted    \= models.BooleanField(default=False)

    deleted\_at    \= models.DateTimeField(null=True, blank=True)

    objects       \= SoftDeleteManager()   \# Фильтрует is\_deleted=True

    all\_objects   \= models.Manager()

    class Meta: abstract \= True

## **5.2 Accounts**

\# apps/accounts/models.py

class User(AbstractBaseUser, PermissionsMixin):

    email          \= models.EmailField(unique=True)  \# Логин через email

    username       \= models.CharField(max\_length=150, unique=True)

    first\_name     \= models.CharField(max\_length=100)

    last\_name      \= models.CharField(max\_length=100)

    role           \= models.CharField(choices=Role.choices, default=Role.EMPLOYEE)

    company        \= models.ForeignKey('companies.Company', on\_delete=PROTECT, null=True)

    team           \= models.ForeignKey('companies.Team', on\_delete=SET\_NULL, null=True)

    is\_active      \= models.BooleanField(default=True)

    is\_staff       \= models.BooleanField(default=False)

    date\_joined    \= models.DateTimeField(auto\_now\_add=True)

    avatar         \= models.ImageField(upload\_to='avatars/', null=True, blank=True)

    USERNAME\_FIELD \= 'email'

    REQUIRED\_FIELDS \= \['username', 'first\_name', 'last\_name'\]

class Role(models.TextChoices):

    EMPLOYEE \= 'employee', 'Employee'

    MANAGER  \= 'manager',  'Manager'

    ADMIN    \= 'admin',    'Admin'

## **5.3 Companies**

\# apps/companies/models.py

class Company(SoftDeleteModel):

    name          \= models.CharField(max\_length=255)

    slug          \= models.SlugField(unique=True)

    owner         \= models.ForeignKey(User, on\_delete=PROTECT, related\_name='owned\_companies')

    max\_users     \= models.PositiveIntegerField(default=50)

    is\_active     \= models.BooleanField(default=True)

    settings      \= models.JSONField(default=dict)  \# Feature flags

class Team(TimeStampedModel):

    name          \= models.CharField(max\_length=200)

    company       \= models.ForeignKey(Company, on\_delete=CASCADE, related\_name='teams')

    manager       \= models.ForeignKey(User, on\_delete=SET\_NULL, null=True)

class Invitation(TimeStampedModel):

    email         \= models.EmailField()

    company       \= models.ForeignKey(Company, on\_delete=CASCADE)

    team          \= models.ForeignKey(Team, on\_delete=SET\_NULL, null=True)

    invited\_by    \= models.ForeignKey(User, on\_delete=SET\_NULL, null=True)

    token         \= models.UUIDField(default=uuid.uuid4, unique=True)

    role          \= models.CharField(choices=Role.choices, default=Role.EMPLOYEE)

    is\_accepted   \= models.BooleanField(default=False)

    expires\_at    \= models.DateTimeField()  \# now \+ 7 days

## **5.4 Tasks**

\# apps/tasks/models.py

class Priority(models.IntegerChoices):

    LOW      \= 1, 'Low'

    MEDIUM   \= 2, 'Medium'

    HIGH     \= 3, 'High'

    CRITICAL \= 4, 'Critical'

class TaskStatus(models.TextChoices):

    TODO       \= 'todo',        'To Do'

    IN\_PROGRESS= 'in\_progress', 'In Progress'

    DONE       \= 'done',        'Done'

    OVERDUE    \= 'overdue',     'Overdue'

class Task(SoftDeleteModel):

    title        \= models.CharField(max\_length=500)

    description  \= models.TextField(blank=True)

    company      \= models.ForeignKey(Company, on\_delete=CASCADE)

    team         \= models.ForeignKey(Team, on\_delete=SET\_NULL, null=True)

    created\_by   \= models.ForeignKey(User, on\_delete=PROTECT, related\_name='created\_tasks')

    assigned\_to  \= models.ForeignKey(User, on\_delete=SET\_NULL, null=True, related\_name='tasks')

    status       \= models.CharField(choices=TaskStatus.choices, default=TaskStatus.TODO)

    priority     \= models.IntegerField(choices=Priority.choices, default=Priority.MEDIUM)

    deadline     \= models.DateTimeField(null=True, blank=True)

    completed\_at \= models.DateTimeField(null=True, blank=True)

class Comment(TimeStampedModel):

    task         \= models.ForeignKey(Task, on\_delete=CASCADE, related\_name='comments')

    author       \= models.ForeignKey(User, on\_delete=CASCADE)

    body         \= models.TextField(max\_length=2000)

class TaskHistory(TimeStampedModel):

    task         \= models.ForeignKey(Task, on\_delete=CASCADE, related\_name='history')

    changed\_by   \= models.ForeignKey(User, on\_delete=SET\_NULL, null=True)

    field\_name   \= models.CharField(max\_length=100)

    old\_value    \= models.TextField(blank=True)

    new\_value    \= models.TextField(blank=True)

## **5.5 Gamification**

\# apps/gamification/models.py

class GamificationRule(TimeStampedModel):

    company      \= models.ForeignKey(Company, on\_delete=CASCADE, null=True)  \# null \= global

    action       \= models.CharField(max\_length=100)  \# 'task\_done', 'task\_early', 'daily\_login'

    xp\_reward    \= models.PositiveIntegerField()

    is\_active    \= models.BooleanField(default=True)

class UserLevel(TimeStampedModel):

    user         \= models.OneToOneField(User, on\_delete=CASCADE, related\_name='level\_data')

    level        \= models.PositiveIntegerField(default=1)

    total\_xp     \= models.PositiveIntegerField(default=0)

    weekly\_xp    \= models.PositiveIntegerField(default=0)

class XPTransaction(TimeStampedModel):

    user         \= models.ForeignKey(User, on\_delete=CASCADE, related\_name='xp\_transactions')

    amount       \= models.IntegerField()  \# Может быть отрицательным

    action       \= models.CharField(max\_length=100)

    related\_task \= models.ForeignKey(Task, on\_delete=SET\_NULL, null=True, blank=True)

    note         \= models.CharField(max\_length=255, blank=True)

class Streak(TimeStampedModel):

    user         \= models.OneToOneField(User, on\_delete=CASCADE, related\_name='streak')

    current      \= models.PositiveIntegerField(default=0)

    longest      \= models.PositiveIntegerField(default=0)

    last\_active  \= models.DateField(null=True)

class Badge(TimeStampedModel):

    name         \= models.CharField(max\_length=100)

    description  \= models.TextField()

    icon         \= models.ImageField(upload\_to='badges/')

    trigger      \= models.CharField(max\_length=100)  \# 'first\_task', 'streak\_7', etc.

    trigger\_value= models.JSONField(default=dict)    \# {'count': 7}

    is\_active    \= models.BooleanField(default=True)

class UserBadge(TimeStampedModel):

    user         \= models.ForeignKey(User, on\_delete=CASCADE, related\_name='badges')

    badge        \= models.ForeignKey(Badge, on\_delete=CASCADE)

    class Meta: unique\_together \= \[\['user', 'badge'\]\]

class RealReward(TimeStampedModel):

    recipient    \= models.ForeignKey(User, on\_delete=CASCADE, related\_name='rewards')

    granted\_by   \= models.ForeignKey(User, on\_delete=SET\_NULL, null=True)

    reward\_type  \= models.CharField(choices=RewardType.choices)

    description  \= models.TextField()

    milestone\_level \= models.PositiveIntegerField()  \# 10, 20, 30...

## **5.6 Burnout**

\# apps/burnout/models.py

class AssessmentForm(TimeStampedModel):

    user         \= models.ForeignKey(User, on\_delete=CASCADE, related\_name='assessments')

    week\_number  \= models.PositiveIntegerField()  \# ISO week

    year         \= models.PositiveIntegerField()

    \# Exhaustion subscale (0-6 each)

    ex1 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    ex2 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    ex3 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    \# Cynicism subscale

    cy1 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    cy2 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    cy3 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    \# Professional Efficacy subscale (reversed scoring)

    ef1 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    ef2 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    ef3 \= models.PositiveSmallIntegerField(validators=\[MaxValueValidator(6)\])

    tasks\_completion\_rate \= models.FloatField()  \# % задач в срок за неделю

    class Meta:

        unique\_together \= \[\['user', 'week\_number', 'year'\]\]

class BurnoutScore(TimeStampedModel):

    user         \= models.OneToOneField(User, on\_delete=CASCADE, related\_name='burnout\_score')

    score        \= models.CharField(choices=BurnoutLevel.choices, default=BurnoutLevel.GREEN)

    last\_calculated \= models.DateTimeField(auto\_now=True)

    exhaustion\_avg  \= models.FloatField(default=0)

    cynicism\_avg    \= models.FloatField(default=0)

    efficacy\_avg    \= models.FloatField(default=0)

    manager\_consent \= models.BooleanField(default=False)

class BurnoutLevel(models.TextChoices):

    GREEN  \= 'green',  'Healthy'

    YELLOW \= 'yellow', 'At Risk'

    RED    \= 'red',    'Burned Out'

## **5.7 Notifications**

\# apps/notifications/models.py

class Notification(TimeStampedModel):

    recipient    \= models.ForeignKey(User, on\_delete=CASCADE, related\_name='notifications')

    type         \= models.CharField(choices=NotificationType.choices)

    title        \= models.CharField(max\_length=255)

    body         \= models.TextField()

    is\_read      \= models.BooleanField(default=False)

    action\_url   \= models.CharField(max\_length=500, blank=True)

    metadata     \= models.JSONField(default=dict)

class TelegramUser(TimeStampedModel):

    user         \= models.OneToOneField(User, on\_delete=CASCADE, related\_name='telegram')

    telegram\_id  \= models.BigIntegerField(unique=True)

    username     \= models.CharField(max\_length=100, blank=True)

    is\_active    \= models.BooleanField(default=True)

# **6\. Требования к коду и архитектуре**

## **6.1 Принципы разработки**

| Принцип | Детали реализации |
| :---- | :---- |
| **DRY** | Вся бизнес-логика в services.py, не в views.py. Базовые модели в core/models.py. Переиспользуемые mixins. |
| **OOP** | GamificationEngine как класс с методами award\_xp(), check\_level\_up(), check\_badges(). Service-слой через классы. |
| **SOLID** | Каждый сервис отвечает за одну задачу. Зависимости инжектируются, не хардкодятся. Абстракции через ABC. |
| **Безопасность** | CSRF на всех POST. Login required. Role-based mixins. Параметризованные SQL-запросы. Секреты только в .env. |
| **HTMX-first** | Views проверяют request.htmx: если True — возвращают partial template; если False — полную страницу. |
| **Тестирование** | Минимум 80% coverage. Unit-тесты для services/ и calculator/. Integration-тесты для views. Pytest \+ factory\_boy. |
| **Type hints** | Все функции и методы должны иметь type annotations. Проверка через mypy. |

## **6.2 Безопасность**

* Аутентификация через email \+ пароль. Обязательный HTTPS в production.

* Django Allauth или кастомный бэкенд. Блокировка аккаунта после 5 неудачных попыток (django-axes).

* CSP (Content-Security-Policy) заголовки через django-csp. HSTS, X-Frame-Options, X-Content-Type-Options в Nginx.

* Все секреты (SECRET\_KEY, DB\_PASSWORD, TELEGRAM\_TOKEN) только через переменные окружения (.env).

* RBAC: RoleRequiredMixin проверяет role пользователя. Менеджер не может видеть данные другой команды.

* Rate limiting на /login/ и /telegram/webhook/ через django-ratelimit.

* Privacy-first: BurnoutScore сотрудника не передаётся менеджеру без явного согласия (manager\_consent=True).

* Audit logging: все критические действия (смена роли, деактивация, выдача наград) логируются в AuditLog модель.

## **6.3 Паттерны HTMX**

\# Стандартный HTMX-view паттерн

class TaskStatusUpdateView(LoginRequiredMixin, RoleRequiredMixin, View):

    def post(self, request, pk):

        task \= get\_object\_or\_404(Task, pk=pk, company=request.user.company)

        new\_status \= request.POST.get('status')

        task\_service \= TaskService(task=task, user=request.user)

        task\_service.update\_status(new\_status)

        if request.htmx:

            return render(request, 'partials/\_task\_card.html', {'task': task})

        return redirect('tasks:detail', pk=task.pk)

## **6.4 GamificationEngine**

\# apps/gamification/engine.py

class GamificationEngine:

    def \_\_init\_\_(self, user: User):

        self.user \= user

        self.rules \= self.\_load\_rules()

    def award\_xp(self, action: str, task: Task | None \= None) \-\> XPTransaction:

        """Award XP for action, apply streak multiplier, check level-up."""

        rule \= self.rules.get(action)

        if not rule: return

        base\_xp \= rule.xp\_reward

        multiplier \= self.\_get\_streak\_multiplier()

        final\_xp \= int(base\_xp \* multiplier)

        txn \= XPTransaction.objects.create(user=self.user, amount=final\_xp, action=action, related\_task=task)

        self.\_update\_user\_level(final\_xp)

        self.check\_badges(action)

        return txn

    def check\_level\_up(self) \-\> bool:

        """Return True if user leveled up after XP award."""

    def check\_badges(self, action: str) \-\> list\[UserBadge\]:

        """Evaluate all badge triggers and award if criteria met."""

    def \_get\_streak\_multiplier(self) \-\> float:

        streak \= self.user.streak.current

        return 1.0 \+ (min(streak, 30\) \* 0.01)  \# Max \+30%

## **6.5 MBICalculator**

\# apps/burnout/calculator.py

class MBICalculator:

    EXHAUSTION\_THRESHOLD  \= {'yellow': 2.0, 'red': 4.0}

    CYNICISM\_THRESHOLD    \= {'yellow': 1.5, 'red': 3.0}

    EFFICACY\_THRESHOLD    \= {'yellow': 3.5, 'red': 2.0}  \# Reversed: low \= bad

    COMPLETION\_THRESHOLD  \= {'yellow': 0.7, 'red': 0.5}

    def calculate(self, form: AssessmentForm) \-\> BurnoutLevel:

        ex\_avg \= mean(\[form.ex1, form.ex2, form.ex3\])

        cy\_avg \= mean(\[form.cy1, form.cy2, form.cy3\])

        ef\_avg \= mean(\[form.ef1, form.ef2, form.ef3\])

        completion \= form.tasks\_completion\_rate

        red\_flags \= sum(\[

            ex\_avg \>= self.EXHAUSTION\_THRESHOLD\['red'\],

            cy\_avg \>= self.CYNICISM\_THRESHOLD\['red'\],

            ef\_avg \<= self.EFFICACY\_THRESHOLD\['red'\],

            completion \< self.COMPLETION\_THRESHOLD\['red'\],

        \])

        if red\_flags \>= 2: return BurnoutLevel.RED

        yellow\_flags \= sum(\[

            ex\_avg \>= self.EXHAUSTION\_THRESHOLD\['yellow'\],

            cy\_avg \>= self.CYNICISM\_THRESHOLD\['yellow'\],

            ef\_avg \<= self.EFFICACY\_THRESHOLD\['yellow'\],

            completion \< self.COMPLETION\_THRESHOLD\['yellow'\],

        \])

        if yellow\_flags \>= 2: return BurnoutLevel.YELLOW

        return BurnoutLevel.GREEN

## **6.6 Celery-задачи**

| Задача | Расписание | Описание |
| :---- | :---- | :---- |
| send\_daily\_reminders | Ежедневно 09:00 | Telegram-сообщения всем активным пользователям |
| send\_assessment\_reminders | Пт 17:00 | Напоминание о незаполненном self-assessment |
| mark\_overdue\_tasks | Каждый час | Обновить статус просроченных задач |
| reset\_weekly\_xp | Пн 00:01 | Обнулить weekly\_xp для всех пользователей |
| check\_streak\_breaks | Ежедневно 00:05 | Сброс streak у неактивных пользователей |
| send\_burnout\_alerts | После расчёта MBI | Уведомить пользователя при изменении статуса |
| cleanup\_old\_notifications | Еженедельно Вс 02:00 | Удалить прочитанные уведомления старше 90 дней |

# **7\. Docker Compose и Production-настройки**

## **7.1 docker-compose.yml (Development)**

version: '3.9'

services:

  db:

    image: postgres:16-alpine

    env\_file: .env

    environment:

      POSTGRES\_DB: ${DB\_NAME}

      POSTGRES\_USER: ${DB\_USER}

      POSTGRES\_PASSWORD: ${DB\_PASSWORD}

    volumes: \['postgres\_data:/var/lib/postgresql/data'\]

    healthcheck:

      test: \['CMD-SHELL', 'pg\_isready \-U ${DB\_USER}'\]

      interval: 10s

      retries: 5

  redis:

    image: redis:7-alpine

    command: redis-server \--appendonly yes

    volumes: \['redis\_data:/data'\]

  django:

    build: ./docker/django

    env\_file: .env

    command: \>

      sh \-c 'python manage.py migrate &&

             python manage.py collectstatic \--noinput &&

             gunicorn config.wsgi:application \--bind 0.0.0.0:8000 \--workers 4'

    volumes: \['./:/app', 'static\_volume:/app/staticfiles', 'media\_volume:/app/media'\]

    depends\_on: {db: {condition: service\_healthy}, redis: {condition: service\_started}}

    ports: \['8000:8000'\]

  celery:

    build: ./docker/django

    env\_file: .env

    command: celery \-A config worker \-l info \-Q default,notifications,telegram

    depends\_on: \[django, redis\]

  celery-beat:

    build: ./docker/django

    env\_file: .env

    command: celery \-A config beat \-l info \--scheduler django\_celery\_beat.schedulers:DatabaseScheduler

    depends\_on: \[django, redis\]

  nginx:

    build: ./docker/nginx

    ports: \['80:80', '443:443'\]

    volumes:

      \- static\_volume:/app/staticfiles

      \- media\_volume:/app/media

      \- ./docker/nginx/nginx.conf:/etc/nginx/conf.d/default.conf

    depends\_on: \[django\]

volumes:

  postgres\_data: redis\_data: static\_volume: media\_volume:

## **7.2 Nginx Configuration**

upstream django {

    server django:8000;

}

server {

    listen 80;

    server\_name your-domain.com;

    return 301 https://$server\_name$request\_uri;

}

server {

    listen 443 ssl http2;

    server\_name your-domain.com;

    ssl\_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;

    ssl\_certificate\_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    ssl\_protocols       TLSv1.2 TLSv1.3;

    ssl\_ciphers         HIGH:\!aNULL:\!MD5;

    \# Security headers

    add\_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;

    add\_header X-Frame-Options DENY;

    add\_header X-Content-Type-Options nosniff;

    add\_header Referrer-Policy strict-origin-when-cross-origin;

    client\_max\_body\_size 10M;

    location /static/ { alias /app/staticfiles/; expires 1y; }

    location /media/  { alias /app/media/;       expires 7d; }

    location / {

        proxy\_pass http://django;

        proxy\_set\_header Host $host;

        proxy\_set\_header X-Real-IP $remote\_addr;

        proxy\_set\_header X-Forwarded-For $proxy\_add\_x\_forwarded\_for;

        proxy\_set\_header X-Forwarded-Proto $scheme;

    }

}

## **7.3 Переменные окружения (.env.example)**

\# Django

SECRET\_KEY=your-secret-key-here

DEBUG=False

ALLOWED\_HOSTS=your-domain.com,www.your-domain.com

DJANGO\_SETTINGS\_MODULE=config.settings.production

\# Database

DB\_NAME=questflow\_db

DB\_USER=questflow\_user

DB\_PASSWORD=strong-password-here

DB\_HOST=db

DB\_PORT=5432

\# Redis & Celery

REDIS\_URL=redis://redis:6379/0

CELERY\_BROKER\_URL=redis://redis:6379/0

CELERY\_RESULT\_BACKEND=redis://redis:6379/1

\# Email (SendGrid / SMTP)

EMAIL\_BACKEND=django.core.mail.backends.smtp.EmailBackend

EMAIL\_HOST=smtp.sendgrid.net

EMAIL\_PORT=587

EMAIL\_USE\_TLS=True

EMAIL\_HOST\_USER=apikey

EMAIL\_HOST\_PASSWORD=your-sendgrid-key

DEFAULT\_FROM\_EMAIL=noreply@questflow.app

\# Telegram Bot

TELEGRAM\_BOT\_TOKEN=your-telegram-bot-token

TELEGRAM\_WEBHOOK\_URL=https://your-domain.com/telegram/webhook/

\# Security

CSRF\_TRUSTED\_ORIGINS=https://your-domain.com

SECURE\_SSL\_REDIRECT=True

SESSION\_COOKIE\_SECURE=True

CSRF\_COOKIE\_SECURE=True

## **7.4 Production Checklist**

1. DEBUG=False и SECRET\_KEY из переменной окружения

2. PostgreSQL с подключением через SSL (sslmode=require)

3. Redis с паролём (requirepass в redis.conf)

4. Gunicorn с 4+ workers (формула: 2 \* CPU \+ 1\)

5. Nginx как reverse proxy \+ Let's Encrypt SSL

6. Django collectstatic перед запуском

7. Celery workers \+ Celery Beat в отдельных контейнерах

8. Sentry для мониторинга ошибок (sentry-sdk\[django\])

9. Healthcheck endpoints для всех сервисов

10. Ежедневный backup PostgreSQL (pg\_dump) в S3-совместимое хранилище

11. Ротация логов Nginx и Django через logrotate

12. Ограничение доступа к /admin/ и /admin-panel/ по IP (опционально)

# **8\. Зависимости и технологический стек**

## **8.1 Backend зависимости (pyproject.toml)**

> **Важно:** Проект переведен на `pip` для установки зависимостей. 
> * Вместо `uv sync` используйте `pip install -r requirements.txt`
> * Вместо `uv add` используйте `pip install`

| Пакет | Версия | Назначение |
| :---- | :---- | :---- |
| django | ^5.1 | Основной фреймворк |
| psycopg\[binary\] | ^3.2 | PostgreSQL адаптер (psycopg3) |
| django-redis | ^5.4 | Redis cache backend |
| celery\[redis\] | ^5.4 | Асинхронные задачи |
| django-celery-beat | ^2.7 | Планировщик Celery Beat |
| channels\[daphne\] | ^4.1 | WebSocket / Django Channels |
| django-htmx | ^1.21 | HTMX request detection middleware |
| python-telegram-bot | ^21.0 | Telegram Bot API |
| django-filter | ^24.3 | ORM-фильтрация для views |
| django-axes | ^7.0 | Защита от брутфорса |
| django-csp | ^3.8 | Content-Security-Policy заголовки |
| pillow | ^11.0 | Обработка изображений (аватары, бейджи) |
| sentry-sdk\[django\] | ^2.0 | Мониторинг ошибок в production |
| pytest-django | ^4.9 | Тестирование Django |
| factory-boy | ^3.3 | Фабрики тестовых данных |

## **8.2 Frontend зависимости**

| Библиотека | Версия | Назначение |
| :---- | :---- | :---- |
| HTMX | 2.0+ | HTML-over-the-wire, динамика без JS |
| Alpine.js | 3.x | Реактивность на клиенте (dropdown, toggle) |
| Tailwind CSS | 3.4+ | Utility-first CSS фреймворк |
| Chart.js | 4.x | Графики в аналитике (динамически через HTMX) |
| Sortable.js | 1.x | Drag-and-drop в Kanban-доске |

# **9\. Дополнительные требования**

## **9.1 Интернационализация**

* Сайт полностью на английском языке (все labels, messages, templates)

* i18n поддержка заложена через Django's translation framework для будущей локализации

* Временные зоны: хранить все timestamps в UTC, конвертировать в часовой пояс пользователя на фронте

## **9.2 Производительность**

* select\_related() и prefetch\_related() обязательны для всех list-views, чтобы избежать N+1 запросов

* django-debug-toolbar в development для анализа SQL-запросов

* Кэширование лидерборда в Redis (TTL 5 минут)

* Пагинация на всех list-views: 20 элементов на страницу

* Индексы БД: Task.deadline, Task.status, Task.assigned\_to, XPTransaction.user, BurnoutScore.user

## **9.3 Тестирование**

* pytest \+ pytest-django как основной фреймворк

* factory\_boy для генерации тестовых данных (UserFactory, TaskFactory, etc.)

* Минимальное покрытие: 80% для services/, engine.py, calculator.py

* Integration-тесты: полные user journeys (create task → complete → xp awarded)

* Тесты безопасности: проверка что Employee не может получить данные другой компании

## **9.4 Масштабируемость**

* Архитектура поддерживает горизонтальное масштабирование: несколько Django workers за Nginx

* Celery workers масштабируются независимо от web-процесса

* При росте нагрузки: вынести статику на CDN (Cloudflare), Redis Cluster, PostgreSQL read replicas

* Все tenant-данные изолированы через ForeignKey на Company — foundation для multi-tenancy

## **9.5 Roadmap (вне текущего скоупа)**

* v2.0: REST API (DRF) для мобильного приложения

* v2.0: Slack-бот (аналог Telegram-бота)

* v2.5: AI-подсказки менеджеру по улучшению вовлечённости

* v3.0: Интеграции с Jira, Asana, Trello через Webhooks

## **9.6 Глоссарий**

| Термин | Определение |
| :---- | :---- |
| **XP (Experience Points)** | Очки опыта, начисляемые за действия в системе |
| **Streak** | Серия дней подряд, когда пользователь был активен в системе |
| **MBI** | Maslach Burnout Inventory — научно-validated инструмент оценки выгорания |
| **Burnout Score** | Итоговый уровень выгорания: Green (здоров), Yellow (под риском), Red (выгорание) |
| **HTMX** | HTML-over-the-wire библиотека: сервер возвращает HTML-фрагменты вместо JSON |
| **Celery Beat** | Планировщик периодических задач для Celery |
| **Partial / Fragment** | HTML-фрагмент, возвращаемый HTMX-view для обновления части страницы |
| **Milestone Level** | Уровни (10, 20, 30...) на которых менеджер может выдать реальную награду |

