package dev.asl.api.run.dto;

import java.time.Instant;
import java.util.UUID;

public record RunSummary(UUID id, String scenario, String condition, String model, long seed, boolean pilot,
		Instant createdAt, boolean focalHelped, boolean earlyHelp, Integer focalHelpTick, int parseFailures,
		int truncations, Boolean recognized) {
}
