# Stage 1: Build frontend
FROM node:22-alpine AS builder

WORKDIR /app

COPY frontend/package*.json frontend/.npmrc* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Caddy server
FROM caddy:2-alpine

COPY --from=builder /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
