# Decisions

Choices the design doc leaves open, and changes made to the repo. One entry each.

## Reset of `main` to the v0.4 design (2026-11-23)

- The v0.3 code and docs are kept on the branch `v0.3-alert-fatigue-herding` (created at `fe1165a`, which is also `origin/main` at that time). `main` was emptied of tracked files except `.gitignore` and then given `README.md` and `docs/designs/`.
- Reason: the operator chose to keep the name Agent Society Lab and replace the repo's contents with the v0.4 design. The v0.3 pilots showed ceilings in most models, and the `prereg-v2` tag was never created.
- Ignored local files (`engine/.env`, `deploy/.env`, `engine/.venv`, `api/target`) were left on disk.
- The v0.3 `.github/workflows/ci.yml` was removed with the code. It returns in C1 and C2 when the API and engine are copied back.
- The same database and Flyway history are kept: `V3__cascade.sql` will clear the v0.3 runs, as `V2__pivot.sql` did for v0.2.
