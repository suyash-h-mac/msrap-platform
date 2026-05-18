# Build stage — maven:3.9-eclipse-temurin-21 has Maven + JDK 21 pre-installed
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY backend/pom.xml .
COPY backend/src ./src
RUN mvn clean package -DskipTests

# Runtime stage — Ubuntu Jammy has pre-built pip wheels for scipy/numpy
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-dev gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY analytics/requirements.txt /tmp/analytics-requirements.txt
RUN pip3 install --no-cache-dir --prefer-binary -r /tmp/analytics-requirements.txt

COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
