# Build stage
FROM node:22-alpine AS builder

ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm config set registry ${NPM_REGISTRY}

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN rm -rf node_modules/.vite dist .vite
RUN npx vite build

# Production stage - serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
