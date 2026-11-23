package dev.asl.api.run.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public record RunDetail(RunView run, List<AgentView> agents) {

	public record RunView(UUID id, String experiment, String scenario, String condition, String population,
			long worldSeed, String promptVersion, Instant startedAt, Instant endedAt, Double accuracy, int ratedCount,
			int probeCount, int recognisedSample) {
	}

	public record AgentView(String agentId, String name, String role, Map<String, Object> persona) {
	}
}
