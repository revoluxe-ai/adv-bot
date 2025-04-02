# Этап сборки
FROM python:3.11-slim as builder

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    pkg-config \
    wget \
    libsystemd-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка virtualenv и создание окружения
RUN python -m venv /app/venv

# Активация виртуального окружения
ENV PATH="/app/venv/bin:$PATH"

# Копирование только requirements.txt
WORKDIR /app
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Установка сертификатов Yandex
RUN mkdir -p ~/.postgresql && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" -O ~/.postgresql/root.crt && \
    chmod 0600 ~/.postgresql/root.crt && \
    mkdir -p /usr/local/share/ca-certificates/Yandex && \
    wget "https://storage.yandexcloud.net/cloud-certs/RootCA.pem" -O /usr/local/share/ca-certificates/Yandex/RootCA.crt && \
    wget "https://storage.yandexcloud.net/cloud-certs/IntermediateCA.pem" -O /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt && \
    chmod 655 /usr/local/share/ca-certificates/Yandex/RootCA.crt /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt

# Финальный этап
FROM python:3.11-slim

# Копирование необходимых системных пакетов
RUN apt-get update && apt-get install -y \
    logrotate \
    cron \
    rsyslog \
    && rm -rf /var/lib/apt/lists/*

# Настройка rsyslog
RUN sed -i '/imklog/s/^/#/' /etc/rsyslog.conf && \
    echo "*.* /dev/stdout" >> /etc/rsyslog.conf

# Копирование виртуального окружения и сертификатов из этапа сборки
COPY --from=builder /app/venv /app/venv
COPY --from=builder /root/.postgresql /root/.postgresql
COPY --from=builder /usr/local/share/ca-certificates/Yandex /usr/local/share/ca-certificates/Yandex

# Обновление сертификатов
RUN update-ca-certificates

# Настройка переменных окружения
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Настройка logrotate
RUN echo "*/5 * * * * /usr/sbin/logrotate /etc/logrotate.conf" > /etc/cron.d/logrotate && \
    chmod 0644 /etc/cron.d/logrotate

# Рабочая директория
WORKDIR /app

# Копирование кода приложения
COPY . .

# Точка входа для всех сервисов
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# CMD будет переопределяться для каждого сервиса
CMD ["echo", "Please specify a service command"]