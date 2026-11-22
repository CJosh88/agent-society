package dev.asl.api.config;

import java.util.List;
import java.util.UUID;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("asl")
public record AslProperties(
		String adminKey,
		List<String> studyModels,
		String promptVersion,
		List<UUID> featuredRunIds,
		List<String> traceLinks,
		Baseline baseline) {

	public AslProperties {
		studyModels = studyModels == null ? List.of() : studyModels;
		featuredRunIds = featuredRunIds == null ? List.of() : featuredRunIds;
		traceLinks = traceLinks == null ? List.of() : traceLinks;
	}

	/** Human baseline for the town square: before-the-end-of-seizure helping, plus optional eventual helping. */
	public record Baseline(Cell alone, Cell group) {
	}

	public record Cell(Integer n, Integer helped, Integer eventualHelped) {
	}
}
