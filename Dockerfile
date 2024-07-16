FROM python:3.11

WORKDIR /app

# Копируем файл requirements.txt в текущую директорию внутри контейнера
COPY requirements.txt .

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы из текущего контекста сборки внутрь контейнера (но не перезаписываем старые)
COPY . .
