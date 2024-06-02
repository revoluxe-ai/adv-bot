FROM python:3.11

WORKDIR /app

COPY ../../ /app

# Установка зависимостей
RUN pip install -r requirements.txt

# Запуск скриптов
CMD ["python", "client_bot_run.py"]

ENTRYPOINT ["top", "-b"]