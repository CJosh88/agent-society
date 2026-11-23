package dev.asl.api.run.dto;

import java.time.Instant;
import java.util.UUID;

public record RunSummary(UUID id, String scenario, String condition, String population, long worldSeed, boolean pilot,
		Instant createdAt, Double accuracy, int ratedCount, int parseFailures, int truncations, int probeCount,
		int recognisedSample) {
}
