package dev.asl.api.run;

import java.util.List;
import java.util.Map;

/** The scenarios, their conditions in display order, and the tick at which the real problem starts. */
public final class RunScenarios {

	public static final Map<String, List<String>> CONDITIONS = Map.of(
			"alert_fatigue", List.of("calm", "fatigue_3", "fatigue_6"),
			"triage_herding", List.of("alone", "dismiss", "endorse"));

	public static final Map<String, Integer> ONSET_TICK = Map.of("alert_fatigue", 9, "triage_herding", 3);

	private RunScenarios() {
	}
}
