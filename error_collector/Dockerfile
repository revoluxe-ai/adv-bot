FROM python:3.11-slim

WORKDIR /app

COPY error_collector/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY error_collector/ ./error_collector/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "error_collector.main:app", "--host", "0.0.0.0", "--port", "8000"]

