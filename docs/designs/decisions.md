# Decisions

Choices the design doc leaves open, and files added beyond its Target files table (one-line reason each).

- The Target files table labels the Dockerfile and deploy files "M6", but the milestone list ends at M5 (Deploy). They are built in M5.
- The `/api/results` row in the REST table is truncated. The `differences` shape is derived from J2: `{model, comparison: "group5-alone" | "owner-group5", diff, ciLow, ciHigh}` (Newcombe).
- Spring Initializr emitted the parent version `4.1.3.RELEASE`, which is not on Maven Central. Changed to `4.1.3`. Initializr's default is 4.2.0; 4.1.3 was requested explicitly, as the doc pins 4.1.x.
- springdoc `springdoc-openapi-starter-webmvc-ui` 3.2.1 (the 3.x line supports Boot 4). Added with `maven-failsafe-plugin`.
- Boot 4 starter names differ from 3.x (`spring-boot-starter-webmvc`, `...-test` starters). Kept as generated.
- Entities use package-private fields and no getters or setters (Hibernate field access). Mapping happens inside `dev.asl.api.run`, so no accessors are needed.
- `RunExceptions.java` (added): holder for the BadRequest, NotFound and AlreadyExists exceptions that `ApiExceptionHandler` maps to 400, 404 and 409.
- `results/ResultsResponse.java` (added): the response records for `/api/results`.
- `GET /api/runs` takes `scenario`, `condition` and `model` as plain strings, validated by hand (400 on unknown scenario or condition). `size` above 100 is clamped to 100.
- `asl.baseline` is `{alone: {n, helped, eventualHelped}, group: {...}}`. A row appears in the town-square results only when `n` and `helped` are set. Eventual fields are omitted until filled.
- `recognitionRate` = recognized runs / runs with a probe answer. It is null when no run has one. `medianHelpTick` is over runs where the focal agent helped, and null if none did.
- `/api/results` rows are ordered by `asl.study-models`, then alone, group5, group5_owner. A difference entry appears only when both cells exist.
- A concurrent duplicate post surfaces as `DataIntegrityViolationException` from `saveAndFlush`, which the handler maps to 409. A try/catch inside the service was dropped, because after a failed flush Postgres aborts the transaction and any further query in it fails.
- Wilson bounds are set exactly to 0 (no successes) and 1 (all successes) to avoid floating-point residue.
- The test `Fixtures.java` is a helper that loads the contract fixtures as mutable maps. Integration tests use Testcontainers `postgres:16`; the dev compose database is only for running the API by hand (M2 gate).
