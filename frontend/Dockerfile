# ─── Stage 1: Build React/Vite Application ─────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build production bundle
COPY . .
RUN npm run build

# ─── Stage 2: Serve with Nginx Alpine ──────────────
FROM nginx:alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build artifacts from Stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 (mapped to 3000 in docker-compose)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
