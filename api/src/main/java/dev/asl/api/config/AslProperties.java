package dev.asl.api.config;

import java.util.List;
import java.util.UUID;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("asl")
public record AslProperties(
		String adminKey,
		List<String> studyPopulations,
		String promptVersion,
		List<UUID> featuredRunIds,
		List<String> traceLinks) {

	public AslProperties {
		studyPopulations = studyPopulations == null ? List.of() : studyPopulations;
		featuredRunIds = featuredRunIds == null ? List.of() : featuredRunIds;
		traceLinks = traceLinks == null ? List.of() : traceLinks;
	}
}
