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
		List<String> traceLinks) {

	public AslProperties {
		studyModels = studyModels == null ? List.of() : studyModels;
		featuredRunIds = featuredRunIds == null ? List.of() : featuredRunIds;
		traceLinks = traceLinks == null ? List.of() : traceLinks;
	}
}
