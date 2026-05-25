---
trigger: always_on
---

# QuestFlow Development Rules (обязательно соблюдать)

1. Структура проекта — ТОЧНО по разделу 3.2 ТЗ
2. Все бизнес-логика только в services.py и engine.py
3. Views — HTMX-first: если request.htmx → возвращать partial, иначе полную страницу
4. Все модели наследуются от TimeStampedModel / SoftDeleteModel из core/
5. Privacy-first: BurnoutScore виден только самому сотруднику и HR (manager_consent)
6. Использовать RoleRequiredMixin и company-изоляцию
7. 80%+ coverage для services/, engine.py, calculator.py
8. Django 5.1 + все пакеты из раздела 8.1