FROM python:3.12-alpine

# Установка системных зависимостей
RUN apk add --no-cache \
    postgresql-client \
    gcc \
    musl-dev \
    libpq-dev \
    nginx \
    curl \
    && rm -rf /var/cache/apk/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY pyproject.toml requirements.txt* ./

# Устанавливаем Python-зависимости через pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём директории для статических файлов (если их нет)
RUN mkdir -p /app/static /app/staticfiles /app/media

# Собираем статические файлы
ENV DATABASE_URL=postgres://dummy:dummy@localhost:5432/dummy
RUN python manage.py collectstatic --noinput 2>&1 || true

# Открываем порт
EXPOSE 8000

# Запуск через entrypoint
CMD ["sh", "/app/scripts/entrypoint.sh"]
