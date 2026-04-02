# ─── Frontend Dockerfile (multi-stage) ───────────────────────────────────────

# Stage 1: build
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time API key (injected by docker-compose build args)
ARG VITE_API_KEY=dev-api-key
ENV VITE_API_KEY=$VITE_API_KEY

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: serve with Nginx
FROM nginx:1.27-alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve SPA + proxy API/WebSocket to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
