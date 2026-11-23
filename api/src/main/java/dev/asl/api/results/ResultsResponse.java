package dev.asl.api.results;

import java.util.List;

/** traceLinks carries asl.trace-links so the About section can link public LangSmith traces. */
public record ResultsResponse(List<ScenarioResults> scenarios, List<String> traceLinks) {

	public record ScenarioResults(String scenario, List<Row> rows, List<Difference> differences) {
	}

	public record Row(String model, String condition, int n, int helped, double rate, double ciLow, double ciHigh,
			double earlyRate, Double medianHelpTick, double parseFailureRate, double truncationRate,
			Double recognitionRate) {
	}

	/** comparison is "{condition}-{baseline}", for example "fatigue_6-calm" or "dismiss-alone": the condition minus its baseline. */
	public record Difference(String model, String comparison, double diff, double ciLow, double ciHigh) {
	}
}
