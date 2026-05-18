# Build stage — compile the Spring Boot jar
FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app
COPY backend/pom.xml .
COPY backend/src ./src
RUN apk add --no-cache maven && mvn clean package -DskipTests

# Runtime stage
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Python + build deps needed by psycopg2-binary / numpy / arch
RUN apk add --no-cache \
      python3 \
      py3-pip \
      gcc \
      musl-dev \
      postgresql-dev \
      python3-dev \
      libffi-dev

# Install all analytics Python dependencies so Java subprocess workers can import them
COPY analytics/requirements.txt /tmp/analytics-requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages \
      -r /tmp/analytics-requirements.txt

COPY --from=build /app/target/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
