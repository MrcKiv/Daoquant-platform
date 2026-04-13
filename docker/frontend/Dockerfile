FROM node:20-bookworm-slim AS build

WORKDIR /app

ARG VITE_API_BASE_URL=
ARG VITE_ENABLE_AUTO_TRADE=false
ARG VITE_TRADE_API_BASE_URL=/trade-api

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_ENABLE_AUTO_TRADE=${VITE_ENABLE_AUTO_TRADE}
ENV VITE_TRADE_API_BASE_URL=${VITE_TRADE_API_BASE_URL}

COPY frontend/package.json /app/package.json
COPY frontend/package-lock.json /app/package-lock.json

RUN npm ci --include=dev

COPY frontend /app

RUN npm run build

FROM nginx:1.27-alpine

COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
