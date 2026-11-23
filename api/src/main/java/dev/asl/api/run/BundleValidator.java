package dev.asl.api.run;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import dev.asl.api.run.RunExceptions.BadRequest;
import dev.asl.api.run.dto.RunBundle;
import dev.asl.api.run.dto.RunBundle.AgentInfo;
import dev.asl.api.run.dto.RunBundle.EventInfo;

import org.springframework.stereotype.Component;

/** The semantic ingest rules from the design doc (shape is already checked by Bean Validation). */
@Component
class BundleValidator {

	/** A world with seeded_wrong scripts at most this many opening agents. */
	static final int MAX_SCRIPTED = 20;

	void validate(RunBundle b) {
		List<AgentInfo> agents = b.agents();
		String condition = b.run().condition();
		String population = b.run().population();
		if (!RunScenarios.CONDITIONS.get(b.run().scenario()).contains(condition)) {
			throw new BadRequest("Condition " + condition + " does not belong to scenario " + b.run().scenario());
		}
		if (condition.equals("seeded_wrong") && population.startsWith("mix_")) {
			throw new BadRequest("seeded_wrong is defined for single-model populations only");
		}

		// Agents are a1..aN with no gaps; the number is the position in the line.
		Set<String> ids = new HashSet<>();
		for (AgentInfo a : agents) {
			if (!ids.add(a.agentId())) {
				throw new BadRequest("Duplicate agent_id: " + a.agentId());
			}
		}
		int n = agents.size();
		for (int p = 1; p <= n; p++) {
			if (!ids.contains("a" + p)) {
				throw new BadRequest("Agents must be a1..a" + n + " without gaps; missing a" + p);
			}
		}

		// Scripted agents open the line (a1..ak). Only seeded_wrong has them, and it has at least one.
		long scripted = agents.stream().filter(a -> a.role().equals("scripted")).count();
		if (condition.equals("seeded_wrong") ? scripted < 1 || scripted > MAX_SCRIPTED : scripted != 0) {
			throw new BadRequest("Condition " + condition + " has " + scripted + " scripted agents");
		}
		for (AgentInfo a : agents) {
			if (a.role().equals("scripted") && position(a.agentId()) > scripted) {
				throw new BadRequest("Scripted agents must be a1.." + "a" + scripted + ", found " + a.agentId());
			}
		}

		List<EventInfo> events = b.events();
		Set<Integer> seqs = new HashSet<>();
		int maxSeq = -1;
		for (EventInfo e : events) {
			seqs.add(e.seq());
			maxSeq = Math.max(maxSeq, e.seq());
			if (e.agentId() != null && !ids.contains(e.agentId())) {
				throw new BadRequest("Event seq " + e.seq() + " references unknown agent_id " + e.agentId());
			}
		}
		if (seqs.size() != events.size() || maxSeq != events.size() - 1) {
			throw new BadRequest("Event seq values must be exactly 0.." + (events.size() - 1));
		}
		long ended = events.stream().filter(e -> e.type().equals("RUN_ENDED")).count();
		int lastSeq = maxSeq;
		boolean lastIsEnd = events.stream().anyMatch(e -> e.seq() == lastSeq && e.type().equals("RUN_ENDED"));
		if (ended != 1 || !lastIsEnd) {
			throw new BadRequest("Exactly one RUN_ENDED event is required, and it must be last");
		}
		b.llmCalls().forEach(c -> {
			if (!ids.contains(c.agentId())) {
				throw new BadRequest("LLM call references unknown agent_id " + c.agentId());
			}
		});

		validateEvents(events, n, condition);
	}

	/** Per-type payload rules the schema expresses and the API relies on when it derives fields. */
	private void validateEvents(List<EventInfo> events, int n, String condition) {
		Map<String, Integer> spawned = new HashMap<>();
		Map<String, Set<String>> picked = new HashMap<>();
		Map<String, Set<String>> rated = new HashMap<>();
		for (EventInfo e : events) {
			Map<String, Object> pl = e.payload();
			switch (e.type()) {
				case "RUN_ENDED" -> {
					if (e.agentId() != null) {
						throw new BadRequest("RUN_ENDED must not name an agent");
					}
					if (e.tick() != n) {
						throw new BadRequest("RUN_ENDED tick must be the last position, " + n);
					}
				}
				case "PROBE_ANSWERED" -> {
					requireAgent(e);
					if (!(pl.get("recognized") instanceof Boolean) || !(pl.get("text") instanceof String)) {
						throw new BadRequest("PROBE_ANSWERED needs text and recognized");
					}
					if (e.tick() != n) {
						throw new BadRequest("PROBE_ANSWERED tick must be the last position, " + n);
					}
				}
				default -> {
					requireAgent(e);
					if (e.tick() != position(e.agentId())) {
						throw new BadRequest("Event seq " + e.seq() + " must carry tick " + position(e.agentId())
								+ " (the position of " + e.agentId() + ")");
					}
					switch (e.type()) {
						case "AGENT_SPAWNED" -> {
							if (!(pl.get("position") instanceof Number p) || p.intValue() != position(e.agentId())) {
								throw new BadRequest("AGENT_SPAWNED position must match " + e.agentId());
							}
							if (spawned.put(e.agentId(), e.seq()) != null) {
								throw new BadRequest("Two AGENT_SPAWNED events for " + e.agentId());
							}
						}
						case "TICKETS_SHOWN" -> {
							boolean hasCounts = pl.get("counts") != null;
							if (hasCounts == condition.equals("independent")) {
								throw new BadRequest("TICKETS_SHOWN counts must be " + (hasCounts ? "null" : "present")
										+ " in condition " + condition);
							}
						}
						case "AGENT_PICKED" -> {
							if (!(pl.get("ticket_ids") instanceof List<?> ids) || ids.size() != 4) {
								throw new BadRequest("AGENT_PICKED needs four ticket_ids");
							}
							Set<String> set = new HashSet<>();
							ids.forEach(t -> set.add(String.valueOf(t)));
							if (set.size() != 4 || picked.put(e.agentId(), set) != null) {
								throw new BadRequest("AGENT_PICKED must be once per agent with four distinct tickets");
							}
						}
						case "AGENT_RATED" -> {
							if (!(pl.get("correct") instanceof Boolean) || !(pl.get("ticket_id") instanceof String t)) {
								throw new BadRequest("AGENT_RATED needs ticket_id and correct");
							}
							if (!rated.computeIfAbsent(e.agentId(), k -> new HashSet<>()).add(t)) {
								throw new BadRequest("Ticket " + t + " rated twice by " + e.agentId());
							}
						}
						default -> {
						}
					}
				}
			}
		}
		for (Map.Entry<String, Set<String>> r : rated.entrySet()) {
			if (!r.getValue().equals(picked.get(r.getKey()))) {
				throw new BadRequest("Ratings of " + r.getKey() + " must match its picked tickets");
			}
		}
		if (!spawned.keySet().containsAll(picked.keySet())) {
			throw new BadRequest("An agent that picked tickets was never spawned");
		}
	}

	private static void requireAgent(EventInfo e) {
		if (e.agentId() == null) {
			throw new BadRequest("Event seq " + e.seq() + " of type " + e.type() + " needs an agent_id");
		}
	}

	private static int position(String agentId) {
		return Integer.parseInt(agentId.substring(1));
	}
}
