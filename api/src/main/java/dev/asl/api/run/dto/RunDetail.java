package dev.asl.api.run.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public record RunDetail(RunView run, List<AgentView> agents) {

	public record RunView(UUID id, String experiment, String scenario, String condition, String model, long seed,
			String promptVersion, Instant startedAt, Instant endedAt, boolean focalHelped, boolean earlyHelp,
			Integer focalHelpTick, Boolean recognized) {
	}

	public record AgentView(String agentId, String name, String role, Map<String, Object> persona) {
	}
}
