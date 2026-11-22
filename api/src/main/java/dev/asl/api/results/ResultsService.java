package dev.asl.api.results;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import dev.asl.api.config.AslProperties;
import dev.asl.api.config.AslProperties.Cell;
import dev.asl.api.results.ResultsResponse.BaselineRow;
import dev.asl.api.results.ResultsResponse.Difference;
import dev.asl.api.results.ResultsResponse.Row;
import dev.asl.api.results.ResultsResponse.ScenarioResults;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

@Service
class ResultsService {

	private static final List<String> SCENARIOS = List.of("town_square", "office");
	private static final List<String> CONDITIONS = List.of("alone", "group5", "group5_owner");

	private static final String SQL = """
			SELECT scenario, model, condition,
			       count(*) AS n,
			       count(*) FILTER (WHERE focal_helped) AS helped,
			       count(*) FILTER (WHERE early_help) AS early,
			       percentile_cont(0.5) WITHIN GROUP (ORDER BY focal_help_tick) FILTER (WHERE focal_helped) AS median_tick,
			       coalesce(sum(parse_failures), 0) AS pf, coalesce(sum(decision_count), 0) AS dc,
			       coalesce(sum(truncations), 0) AS tr, coalesce(sum(llm_call_count), 0) AS lc,
			       count(*) FILTER (WHERE recognized) AS rec, count(recognized) AS rec_n
			FROM runs
			WHERE pilot = false AND experiment = 'agent_society_v1'
			  AND prompt_version = :promptVersion AND model IN (:models)
			GROUP BY scenario, model, condition
			""";

	private record Cellrow(String scenario, Row row) {
	}

	private final JdbcClient jdbc;
	private final AslProperties props;

	ResultsService(JdbcClient jdbc, AslProperties props) {
		this.jdbc = jdbc;
		this.props = props;
	}

	ResultsResponse results() {
		List<String> models = props.studyModels();
		List<Cellrow> cells = models.isEmpty() ? List.of()
				: jdbc.sql(SQL).param("promptVersion", props.promptVersion()).param("models", models)
						.query((rs, i) -> {
							int n = rs.getInt("n");
							int helped = rs.getInt("helped");
							double median = rs.getDouble("median_tick");
							Double medianOrNull = rs.wasNull() ? null : median;
							long dc = rs.getLong("dc");
							long lc = rs.getLong("lc");
							int recN = rs.getInt("rec_n");
							double[] ci = WilsonInterval.of(helped, n);
							return new Cellrow(rs.getString("scenario"),
									new Row(rs.getString("model"), rs.getString("condition"), n, helped,
											(double) helped / n, ci[0], ci[1], (double) rs.getInt("early") / n,
											medianOrNull, dc == 0 ? 0 : (double) rs.getLong("pf") / dc,
											lc == 0 ? 0 : (double) rs.getLong("tr") / lc,
											recN == 0 ? null : (double) rs.getInt("rec") / recN));
						}).list();

		List<ScenarioResults> scenarios = new ArrayList<>();
		for (String scenario : SCENARIOS) {
			List<Row> rows = new ArrayList<>();
			List<Difference> diffs = new ArrayList<>();
			for (String model : models) {
				for (String condition : CONDITIONS) {
					find(cells, scenario, model, condition).ifPresent(rows::add);
				}
				diff(cells, scenario, model, "group5-alone", "group5", "alone").ifPresent(diffs::add);
				diff(cells, scenario, model, "owner-group5", "group5_owner", "group5").ifPresent(diffs::add);
			}
			scenarios.add(new ScenarioResults(scenario, rows, diffs,
					scenario.equals("town_square") ? baseline() : null));
		}
		return new ResultsResponse(scenarios, props.traceLinks());
	}

	private static Optional<Row> find(List<Cellrow> cells, String scenario, String model, String condition) {
		return cells.stream().filter(c -> c.scenario().equals(scenario) && c.row().model().equals(model)
				&& c.row().condition().equals(condition)).map(Cellrow::row).findFirst();
	}

	private static Optional<Difference> diff(List<Cellrow> cells, String scenario, String model, String label,
			String higher, String lower) {
		Optional<Row> a = find(cells, scenario, model, higher);
		Optional<Row> b = find(cells, scenario, model, lower);
		if (a.isEmpty() || b.isEmpty()) {
			return Optional.empty();
		}
		double[] d = NewcombeInterval.difference(a.get().helped(), a.get().n(), b.get().helped(), b.get().n());
		return Optional.of(new Difference(model, label, d[0], d[1], d[2]));
	}

	private List<BaselineRow> baseline() {
		AslProperties.Baseline b = props.baseline();
		if (b == null) {
			return null;
		}
		List<BaselineRow> rows = new ArrayList<>();
		addBaseline(rows, "alone", b.alone());
		addBaseline(rows, "group", b.group());
		return rows.isEmpty() ? null : rows;
	}

	private static void addBaseline(List<BaselineRow> rows, String condition, Cell c) {
		if (c == null || c.n() == null || c.n() <= 0 || c.helped() == null) {
			return;
		}
		double[] ci = WilsonInterval.of(c.helped(), c.n());
		Double eventual = c.eventualHelped() == null ? null : (double) c.eventualHelped() / c.n();
		rows.add(new BaselineRow(condition, c.n(), c.helped(), (double) c.helped() / c.n(), ci[0], ci[1],
				c.eventualHelped(), eventual));
	}
}
