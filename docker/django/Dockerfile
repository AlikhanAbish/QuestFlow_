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

# Собираем статические файлы
RUN python manage.py collectstatic --noinput

# Открываем порт
EXPOSE 8000

# Запуск через entrypoint
CMD ["sh", "/app/scripts/entrypoint.sh"]