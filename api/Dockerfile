# Build stage: Maven wrapper, tests skipped (CI runs them)
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY .mvn .mvn
COPY mvnw pom.xml ./
RUN ./mvnw -B -q dependency:go-offline
COPY src src
RUN ./mvnw -B package -DskipTests

# Run stage: JRE only
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/api-*-SNAPSHOT.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=60", "-jar", "app.jar"]
