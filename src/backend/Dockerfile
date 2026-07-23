FROM maven:3.9.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY src/backend/pom.xml ./pom.xml
COPY src/backend/src ./src
RUN mvn -B package

FROM eclipse-temurin:21-jre
WORKDIR /app
ENV JAVA_OPTS=""
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/core-api-0.1.0-SNAPSHOT.jar ./app.jar
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
