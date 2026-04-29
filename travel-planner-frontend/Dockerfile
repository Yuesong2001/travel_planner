# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1: Build the Vite/React bundle
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Bake /api as the API base URL so the bundle calls same-origin
# /api/* paths, which nginx then reverse-proxies to the backend.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ============================================================
# Stage 2: Serve with nginx
# ============================================================
FROM nginx:alpine

# nginx:alpine automatically runs envsubst on every file in
# /etc/nginx/templates/*.template at container start and writes
# the result to /etc/nginx/conf.d/*.conf.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

COPY --from=builder /app/dist /usr/share/nginx/html

# Default to host.docker.internal so the image works out of the box on
# Docker Desktop (Win/Mac) when the backend runs on the host.
# Override at runtime with `-e BACKEND_URL=http://<host>:<port>`.
ENV BACKEND_URL=http://host.docker.internal:8000

# Only substitute the variables we actually use, so nginx-internal
# tokens like $host / $remote_addr stay untouched.
ENV NGINX_ENVSUBST_FILTER_VARIABLES="BACKEND_URL"

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
