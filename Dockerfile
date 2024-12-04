FROM python:3.11.8-slim

WORKDIR /app

# Устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    python3-dev \
    libpq-dev \
    wget \
    ca-certificates \
    libsystemd-dev \
    systemd \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Загружаем и устанавливаем сертификаты Yandex Cloud
RUN mkdir -p /usr/local/share/ca-certificates/Yandex/ && \
    wget "https://storage.yandexcloud.net/cloud-certs/RootCA.pem" \
        -O /usr/local/share/ca-certificates/Yandex/RootCA.crt && \
    wget "https://storage.yandexcloud.net/cloud-certs/IntermediateCA.pem" \
        -O /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt && \
    chmod 655 \
        /usr/local/share/ca-certificates/Yandex/RootCA.crt \
        /usr/local/share/ca-certificates/Yandex/IntermediateCA.crt && \
    update-ca-certificates

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

EXPOSE 8000

CMD ["python", "updater.py"]