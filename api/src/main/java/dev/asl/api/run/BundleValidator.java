package dev.asl.api.run;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import dev.asl.api.run.RunExceptions.BadRequest;
import dev.asl.api.run.dto.RunBundle;
import dev.asl.api.run.dto.RunBundle.AgentInfo;
import dev.asl.api.run.dto.RunBundle.EventInfo;

import org.springframework.stereotype.Component;

/** The semantic ingest rules from the design doc (shape is already checked by Bean Validation). */
@Component
class BundleValidator {

	void validate(RunBundle b) {
		List<AgentInfo> agents = b.agents();
		Set<String> ids = new HashSet<>();
		for (AgentInfo a : agents) {
			if (!ids.add(a.agentId())) {
				throw new BadRequest("Duplicate agent_id: " + a.agentId());
			}
		}
		if (count(agents, "focal") != 1) {
			throw new BadRequest("Exactly one focal agent is required");
		}
		int scripted = b.run().condition().equals("alone") ? 0 : 4;
		if (count(agents, "scripted") != scripted) {
			throw new BadRequest("Condition " + b.run().condition() + " requires " + scripted + " scripted agents");
		}
		int victims = b.run().scenario().equals("town_square") ? 1 : 0;
		if (count(agents, "victim") != victims) {
			throw new BadRequest("Scenario " + b.run().scenario() + " requires " + victims + " victim agents");
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
	}

	private static long count(List<AgentInfo> agents, String role) {
		return agents.stream().filter(a -> a.role().equals(role)).count();
	}
}
