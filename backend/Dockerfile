FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY pom.xml .
COPY monitoring-common/pom.xml monitoring-common/pom.xml
COPY monitoring-api/pom.xml monitoring-api/pom.xml
COPY monitoring-api-rpc/pom.xml monitoring-api-rpc/pom.xml
COPY monitoring-core/pom.xml monitoring-core/pom.xml
COPY monitoring-application/pom.xml monitoring-application/pom.xml
RUN mvn -q -DskipTests dependency:go-offline
COPY monitoring-common/src monitoring-common/src
COPY monitoring-api/src monitoring-api/src
COPY monitoring-api-rpc/src monitoring-api-rpc/src
COPY monitoring-core/src monitoring-core/src
COPY monitoring-application/src monitoring-application/src
RUN mvn -q -DskipTests -pl monitoring-application -am package

FROM eclipse-temurin:21-jre
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/monitoring-application/target/monitoring-application-0.1.0.jar /app/app.jar
EXPOSE 8081
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
