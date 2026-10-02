# Imagen de producción del frontend: build de Vite + nginx sirviendo la SPA.
# Vite "hornea" las variables VITE_* en el bundle en tiempo de build, por eso
# llegan como build args (ver docker-compose.prod.yml).
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .

ARG VITE_APP_NAME="Matriz Administrativa de Obligaciones"
ARG VITE_API_BASE_URL
ENV VITE_APP_NAME=$VITE_APP_NAME \
    VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
