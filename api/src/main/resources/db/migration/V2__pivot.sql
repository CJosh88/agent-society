-- v0.3 pivot: alert fatigue and herding in triage replace the bystander scenarios.
-- Every v0.2 run is removed (agents, events and llm_calls cascade).
DELETE FROM runs;

ALTER TABLE runs DROP CONSTRAINT runs_scenario_check;
ALTER TABLE runs DROP CONSTRAINT runs_condition_check;
ALTER TABLE agents DROP CONSTRAINT agents_role_check;
ALTER TABLE events DROP CONSTRAINT events_type_check;

ALTER TABLE runs ADD CONSTRAINT runs_scenario_check CHECK (scenario IN ('alert_fatigue','triage_herding'));
ALTER TABLE runs ADD CONSTRAINT runs_condition_check
  CHECK (condition IN ('calm','fatigue_3','fatigue_6','alone','dismiss','endorse'));
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (role IN ('focal','scripted'));
ALTER TABLE events ADD CONSTRAINT events_type_check
  CHECK (type IN ('AGENT_SPAWNED','NOTICE_SHOWN','AGENT_SAID','AGENT_WAITED','AGENT_CALLED',
                  'AGENT_PRIORITY_SET','ACTION_PARSE_FAILED','PROBE_ANSWERED','RUN_ENDED'));
