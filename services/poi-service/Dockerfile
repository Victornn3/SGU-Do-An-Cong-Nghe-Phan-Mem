FROM python:3.10-slim

WORKDIR /app

COPY services/poi-service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/poi-service/app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]