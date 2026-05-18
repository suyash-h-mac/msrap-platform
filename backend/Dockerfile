# ── Build stage: compile Spring Boot jar (Alpine is fine for Maven) ──────────
FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app
COPY backend/pom.xml .
COPY backend/src ./src
RUN apk add --no-cache maven && mvn clean package -DskipTests

# ── Runtime stage: Ubuntu (Jammy) so pip can use pre-built binary wheels ─────
# Alpine lacks the C++ toolchain needed to compile scipy/numpy from source.
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 \
      python3-pip \
      python3-dev \
      gcc \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install analytics deps with --prefer-binary so pip uses pre-built wheels
COPY analytics/requirements.txt /tmp/analytics-requirements.txt
RUN pip3 install --no-cache-dir --prefer-binary -r /tmp/analytics-requirements.txt

COPY --from=build /app/target/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
