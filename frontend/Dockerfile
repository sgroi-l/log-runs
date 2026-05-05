FROM node:20-slim AS builder

WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx:alpine auto-runs envsubst on /etc/nginx/templates/*.template at startup,
# writing the result to /etc/nginx/conf.d/. Defaults match docker-compose; Fly overrides.
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV BACKEND_HOST=backend:8000
ENV DNS_RESOLVER=127.0.0.11

EXPOSE 80
