import dotenv
dotenv.load_dotenv()
from celery import Celery
import celeryconfig
# Создайте приложение Celery
app = Celery()

app.config_from_object(celeryconfig)


# Настройки (опционально)
# app.conf.update(
#     task_serializer='json',
#     result_serializer='json',
#     accept_content=['json'],
# )
