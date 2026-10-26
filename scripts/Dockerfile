FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir pymongo bcrypt

COPY scripts/seed_data.py /app/scripts/seed_data.py

CMD ["python", "/app/scripts/seed_data.py"]