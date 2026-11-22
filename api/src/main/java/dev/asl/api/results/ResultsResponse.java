package dev.asl.api.results;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;

public record ResultsResponse(List<ScenarioResults> scenarios) {

	public record ScenarioResults(String scenario, List<Row> rows, List<Difference> differences,
			@JsonInclude(JsonInclude.Include.NON_NULL) List<BaselineRow> baseline) {
	}

	public record Row(String model, String condition, int n, int helped, double rate, double ciLow, double ciHigh,
			double earlyRate, Double medianHelpTick, double parseFailureRate, double truncationRate,
			Double recognitionRate) {
	}

	/** comparison is "group5-alone" (group5 minus alone) or "owner-group5" (group5_owner minus group5). */
	public record Difference(String model, String comparison, double diff, double ciLow, double ciHigh) {
	}

	/** Human baseline row. Eventual-rate fields are omitted until filled in. */
	public record BaselineRow(String condition, int n, int helped, double rate, double ciLow, double ciHigh,
			@JsonInclude(JsonInclude.Include.NON_NULL) Integer eventualHelped,
			@JsonInclude(JsonInclude.Include.NON_NULL) Double eventualRate) {
	}
}
