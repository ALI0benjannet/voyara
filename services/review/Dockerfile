# Contexte de build attendu : racine du repo (voir docker-compose.yml)
FROM python:3.12-slim

WORKDIR /srv

COPY libs/common /srv/libs/common
COPY services/review/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir /srv/libs/common

COPY services/review /srv/service
WORKDIR /srv/service

EXPOSE 8005
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--proxy-headers"]
