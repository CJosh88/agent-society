# Decisions

Choices the design doc leaves open, and files added beyond its Target files table (one-line reason each).

- The Target files table labels the Dockerfile and deploy files "M6", but the milestone list ends at M5 (Deploy). They are built in M5.
- The `/api/results` row in the REST table is truncated. The `differences` shape is derived from J2: `{model, comparison: "group5-alone" | "owner-group5", diff, ciLow, ciHigh}` (Newcombe).
