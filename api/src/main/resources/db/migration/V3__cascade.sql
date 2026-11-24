-- v0.4 cascade: a world of sequential agents replaces the focal-agent scenarios.
-- Every v0.3 run is removed (agents, events and llm_calls cascade). runs.model holds the population label
-- and runs.seed holds the world seed.
DELETE FROM runs;

ALTER TABLE runs DROP COLUMN focal_helped;
ALTER TABLE runs DROP COLUMN early_help;
ALTER TABLE runs DROP COLUMN focal_help_tick;
ALTER TABLE runs DROP COLUMN decision_count;
ALTER TABLE runs DROP COLUMN recognized;

ALTER TABLE runs ADD COLUMN accuracy DOUBLE PRECISION;
ALTER TABLE runs ADD COLUMN rated_count INT NOT NULL;
ALTER TABLE runs ADD COLUMN probe_count INT NOT NULL;
ALTER TABLE runs ADD COLUMN recognised_sample INT NOT NULL;

ALTER TABLE runs DROP CONSTRAINT runs_scenario_check;
ALTER TABLE runs DROP CONSTRAINT runs_condition_check;
ALTER TABLE agents DROP CONSTRAINT agents_role_check;
ALTER TABLE events DROP CONSTRAINT events_type_check;
ALTER TABLE events DROP CONSTRAINT events_tick_check;

ALTER TABLE runs ADD CONSTRAINT runs_scenario_check CHECK (scenario IN ('triage_cascade'));
ALTER TABLE runs ADD CONSTRAINT runs_condition_check
  CHECK (condition IN ('independent','weak','strong','seeded_wrong'));
ALTER TABLE runs ADD CONSTRAINT runs_population_check
  CHECK (model IN ('llama-3.1-8b','gpt-oss-120b','claude-haiku-5-5','mix_early','mix_late','fake'));
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (role IN ('agent','scripted'));
ALTER TABLE events ADD CONSTRAINT events_type_check
  CHECK (type IN ('AGENT_SPAWNED','TICKETS_SHOWN','AGENT_PICKED','AGENT_RATED','ACTION_PARSE_FAILED',
                  'PROBE_ANSWERED','RUN_ENDED'));
ALTER TABLE events ADD CONSTRAINT events_tick_check CHECK (tick BETWEEN 1 AND 200);

DROP INDEX runs_results;
CREATE INDEX runs_results ON runs (experiment, scenario, condition, model) WHERE pilot = false;
