FROM python:3.11

# Установка рабочего каталога
WORKDIR /app

# Копирование только файла зависимостей (requirements.txt)
COPY requirements.txt ./

# Установка необходимых библиотек
RUN apt-get update && apt-get install -y \
    logrotate \
    cron \
    rsyslog \
    libsystemd-dev \
    pkg-config \
    wget \
    ca-certificates


# Установка virtualenv
RUN pip install --upgrade pip && pip install virtualenv

# Создание виртуального окружения
RUN python -m venv /app/venv


# Активируем виртуальное окружение и устанавливаем зависимости
RUN /bin/bash -c "source /app/venv/bin/activate && pip install -r requirements.txt"

# Установка сертификатов для работы с Yandex PostgreSQL
RUN mkdir -p ~/.postgresql && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" --output-document ~/.postgresql/root.crt && \
    chmod 0600 ~/.postgresql/root.crt && \
    mkdir --parents /usr/local/share/ca-certificates/Yandex && \
    wget "https://storage.yandexcloud.net/cloud-certs/RootCA.pem" --output-document /usr/local/share/ca-certificates/Yandex/RootCA.crt && \
    wget "https://storage.yandexcloud.net/cloud-certs/IntermediateCA.pem" --output-document /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt && \
    chmod 655 /usr/local/share/ca-certificates/Yandex/RootCA.crt /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt && \
    update-ca-certificates

# Копирование конфигурации logrotate
#COPY logrotate.conf /etc/logrotate.conf
#COPY logrotate.d/ /etc/logrotate.d/

# Устанавливаем переменную окружения для использования виртуального окружения по умолчанию
ENV PATH="/app/venv/bin:$PATH"

# Настройка cron для запуска logrotate
RUN echo "*/5 * * * * /usr/sbin/logrotate /etc/logrotate.conf" > /etc/cron.d/logrotate
RUN chmod 0644 /etc/cron.d/logrotate

# Копирование всего проекта
COPY ../../ ./


# Запуск rsyslog, cron и твоего приложения
CMD ["bash", "-c", "service cron start && python client_bot_run.py"]
