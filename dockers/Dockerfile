FROM python:3.11-slim AS base

# Настройки Poetry
ENV POETRY_VERSION=1.5.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/app/.venv/bin:$PATH"

# Рабочая директория
WORKDIR /app

# Установка необходимых системных пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    logrotate \
    cron \
    rsyslog \
    libsystemd-dev \
    pkg-config \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Сначала копируем только файлы зависимостей (чтобы кэшировать слои)
COPY pyproject.toml poetry.lock ./

# Установка зависимостей (без dev-зависимостей)
RUN poetry install --no-interaction --no-root --without dev

# Копируем весь исходный код
COPY . .

# Настройка cron для запуска logrotate
RUN echo "*/5 * * * * /usr/sbin/logrotate /etc/logrotate.conf" > /etc/cron.d/logrotate \
    && chmod 0644 /etc/cron.d/logrotate
