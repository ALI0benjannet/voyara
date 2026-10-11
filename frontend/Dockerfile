# Contexte de build attendu : racine du repo (voir docker-compose.yml)
# Étape 1 : build de l'app ADMIN (Vite). Le site client (Next.js) a sa propre
# image : frontend/Dockerfile.client — nginx proxy / vers ce conteneur.
FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
COPY frontend/apps ./apps
COPY frontend/packages ./packages
RUN npm ci --no-audit --no-fund && npm run build -w @voyara/admin

# Étape 2 : nginx sert l'admin (/admin/), proxy / → client Next et /api → gateway
FROM nginx:alpine

COPY infra/nginx/web.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/admin/dist /usr/share/nginx/html/admin

EXPOSE 80
