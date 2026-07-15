# Multi-target image definitions for the Pharma Manager services.
# Build the desired target from compose, for example:
#   docker compose build frontend core-api ai-backend

FROM node:20-alpine AS frontend-dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM frontend-dependencies AS frontend-builder
COPY . .
RUN npm run build
RUN npm prune --omit=dev

FROM node:20-alpine AS frontend
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
COPY --from=frontend-builder /app/package.json /app/package-lock.json ./
COPY --from=frontend-builder /app/node_modules ./node_modules
COPY --from=frontend-builder /app/src/frontend/.next ./src/frontend/.next
COPY --from=frontend-builder /app/src/frontend/next.config.mjs ./src/frontend/next.config.mjs
EXPOSE 3000
CMD ["npm", "run", "start"]

FROM maven:3.9.9-eclipse-temurin-21 AS core-api-builder
WORKDIR /app
COPY src/backend/pom.xml ./pom.xml
COPY src/backend/src ./src
RUN mvn -B package -DskipTests

FROM eclipse-temurin:21-jre AS core-api
WORKDIR /app
ENV JAVA_OPTS=""
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=core-api-builder /app/target/core-api-0.1.0-SNAPSHOT.jar ./app.jar
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]

FROM python:3.12-slim AS ai-backend
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY src/ai-backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ai-backend/app ./app
COPY src/ai-backend/migrations ./migrations
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
