package dev.asl.api.results;

import java.util.List;

/** traceLinks carries asl.trace-links so the About section can link public LangSmith traces. */
public record ResultsResponse(List<PopulationResults> populations, List<String> traceLinks) {

	public record PopulationResults(String population, List<Row> rows, List<Difference> differences) {
	}

	/** Mean world accuracy over n worlds, with a 95% bootstrap interval over worlds. */
	public record Row(String condition, int n, double meanAccuracy, double ciLow, double ciHigh,
			double parseFailureRate, double truncationRate, Double recognitionRate) {
	}

	/** comparison is "{condition}-independent": the condition's mean accuracy minus the baseline's. */
	public record Difference(String comparison, double diff, double ciLow, double ciHigh) {
	}
}
