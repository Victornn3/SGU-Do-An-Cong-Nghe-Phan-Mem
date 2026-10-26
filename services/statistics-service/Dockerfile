FROM python:3.10-slim

WORKDIR /app

COPY services/statistics-service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/statistics-service/app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]