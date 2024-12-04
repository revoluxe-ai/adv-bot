FROM python:3.11.8-slim

WORKDIR /app

# Устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    python3-dev \
    libpq-dev \
    python3-systemd \
    libsystemd-dev \
    systemd && \
    rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt сначала
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

EXPOSE 8000

CMD ["python", "updater.py"]