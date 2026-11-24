package dev.asl.api.run;

import java.util.List;
import java.util.Map;

/** The scenario, its conditions in display order (the first is the baseline), and the populations. */
public final class RunScenarios {

	public static final String SCENARIO = "triage_cascade";

	public static final Map<String, List<String>> CONDITIONS = Map.of(
			SCENARIO, List.of("independent", "weak", "strong", "seeded_wrong"));

	public static final List<String> POPULATIONS = List.of("llama-3.1-8b", "gpt-oss-120b", "claude-haiku-5-5",
			"mix_early", "mix_late", "fake");

	private RunScenarios() {
	}
}
