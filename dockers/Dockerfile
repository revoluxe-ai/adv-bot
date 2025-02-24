FROM python:3.11

# Установка рабочего каталога
WORKDIR /app

COPY linux_requirements.txt ./

# Установка необходимых библиотек
RUN apt-get update && apt-get install -y \
    logrotate \
    cron \
    rsyslog \
    libsystemd-dev \
    pkg-config \
    wget \
    ca-certificates && \
    # Установка virtualenv
    pip install --upgrade pip && \
    pip install virtualenv && \
    # Установка сертификатов для работы с Yandex PostgreSQL
    mkdir -p ~/.postgresql && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" --output-document ~/.postgresql/root.crt && \
    chmod 0600 ~/.postgresql/root.crt && \
    mkdir --parents /usr/local/share/ca-certificates/Yandex && \
    wget "https://storage.yandexcloud.net/cloud-certs/RootCA.pem" --output-document /usr/local/share/ca-certificates/Yandex/RootCA.crt && \
    wget "https://storage.yandexcloud.net/cloud-certs/IntermediateCA.pem" --output-document /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt && \
    chmod 655 /usr/local/share/ca-certificates/Yandex/RootCA.crt /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt && \
    update-ca-certificates

# Создание виртуального окружения
RUN python -m venv /app/venv

# Активируем виртуальное окружение и устанавливаем зависимости
RUN /bin/bash -c "source /app/venv/bin/activate && pip install -r linux_requirements.txt"

# Настройка cron для запуска logrotate
RUN echo "*/5 * * * * /usr/sbin/logrotate /etc/logrotate.conf" > /etc/cron.d/logrotate && \
    chmod 0644 /etc/cron.d/logrotate

# Копирование исходного кода
COPY . .

# Устанавливаем переменную окружения для использования виртуального окружения по умолчанию
ENV PATH="/app/venv/bin:$PATH"