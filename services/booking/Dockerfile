# Contexte de build attendu : racine du repo (voir docker-compose.yml)
FROM python:3.12-slim

WORKDIR /srv

COPY libs/common /srv/libs/common
COPY services/booking/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir /srv/libs/common

COPY services/booking /srv/service
WORKDIR /srv/service

EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--proxy-headers"]
