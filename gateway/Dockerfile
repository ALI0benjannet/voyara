# Contexte de build attendu : racine du repo (voir docker-compose.yml)
FROM python:3.12-slim

WORKDIR /srv

COPY gateway/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway /srv/service
WORKDIR /srv/service

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
