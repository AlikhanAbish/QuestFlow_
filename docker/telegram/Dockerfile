FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN apk update \
    && apk add --no-cache gcc musl-dev postgresql-dev postgresql-client libffi-dev curl \
    && pip install uv

COPY pyproject.toml /app/
RUN uv pip install -r pyproject.toml --system

COPY . /app/
RUN sed -i 's/\r$//' /app/scripts/*.sh && chmod +x /app/scripts/*.sh

# One-time webhook setup: runs command, registers webhook, exits
CMD ["/app/scripts/telegram_setup_webhook_init.sh"]
