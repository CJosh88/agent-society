CREATE TABLE runs (
  id               UUID PRIMARY KEY,
  experiment       TEXT NOT NULL,
  scenario         TEXT NOT NULL CHECK (scenario IN ('town_square','office')),
  condition        TEXT NOT NULL CHECK (condition IN ('alone','group5','group5_owner')),
  model            TEXT NOT NULL,
  seed             BIGINT NOT NULL,
  prompt_version   TEXT NOT NULL,
  engine_version   TEXT NOT NULL,
  pilot            BOOLEAN NOT NULL,
  started_at       TIMESTAMPTZ NOT NULL,
  ended_at         TIMESTAMPTZ NOT NULL,
  focal_helped     BOOLEAN NOT NULL,
  early_help       BOOLEAN NOT NULL,
  focal_help_tick  INT,
  decision_count   INT NOT NULL,
  parse_failures   INT NOT NULL,
  truncations      INT NOT NULL,
  llm_call_count   INT NOT NULL,
  recognized       BOOLEAN,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX runs_results ON runs (scenario, model, condition) WHERE pilot = false;
CREATE INDEX runs_created ON runs (created_at DESC, id);

CREATE TABLE agents (
  run_id    UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  agent_id  TEXT NOT NULL,
  name      TEXT NOT NULL,
  role      TEXT NOT NULL CHECK (role IN ('focal','scripted','victim')),
  persona   JSONB NOT NULL,
  PRIMARY KEY (run_id, agent_id)
);

CREATE TABLE events (
  id        BIGSERIAL PRIMARY KEY,
  run_id    UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  seq       INT NOT NULL,
  tick      INT NOT NULL CHECK (tick BETWEEN 0 AND 12),
  type      TEXT NOT NULL CHECK (type IN ('AGENT_SPAWNED','PROBLEM_STARTED','AGENT_MOVED','AGENT_SAID',
            'AGENT_WAITED','AGENT_APPROACHED','AGENT_CALLED','ACTION_PARSE_FAILED','PROBE_ANSWERED','RUN_ENDED')),
  agent_id  TEXT,
  payload   JSONB NOT NULL,
  UNIQUE (run_id, seq),
  FOREIGN KEY (run_id, agent_id) REFERENCES agents (run_id, agent_id)
);

CREATE TABLE llm_calls (
  id                BIGSERIAL PRIMARY KEY,
  run_id            UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  agent_id          TEXT NOT NULL,
  tick              INT NOT NULL,
  kind              TEXT NOT NULL CHECK (kind IN ('decision','probe')),
  attempt           INT NOT NULL CHECK (attempt IN (1,2)),
  prompt            TEXT NOT NULL,
  response_text     TEXT NOT NULL,
  reasoning_text    TEXT,
  finish_reason     TEXT,
  input_tokens      INT,
  output_tokens     INT,
  tokens_estimated  BOOLEAN NOT NULL,
  parsed_ok         BOOLEAN NOT NULL,
  latency_ms        INT NOT NULL,
  FOREIGN KEY (run_id, agent_id) REFERENCES agents (run_id, agent_id)
);
