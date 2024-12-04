# Используем официальный образ с Python 3.11
FROM python:3.11.8-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    python3-systemd \
    systemd && \
    rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt сначала, чтобы лучше использовать кэш
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Открываем порт, если необходимо
EXPOSE 8000

# Запуск приложения
CMD ["python", "updater.py"]