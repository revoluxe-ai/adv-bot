FROM python:3.11

WORKDIR /adv_bot

# Копируем файл requirements.txt в контейнер
COPY requirements.txt .

# Установка зависимостей
RUN pip install -r requirements.txt

COPY python_modules ./python_modules
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY ./app ./app
COPY ./setting.yaml ./setting.yaml
COPY ./logging_config.json ./logging_config.json
RUN mkdir /adv_bot/logs


RUN alembic upgrade head

# Копируем все содержимое проекта внутрь контейнера

COPY ./client_bot_run.py ./client_bot_run.py

# Запуск скриптов
CMD ["python", "client_bot_run.py"]