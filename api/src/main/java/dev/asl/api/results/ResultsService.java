package dev.asl.api.results;

import java.util.ArrayList;
import java.util.List;

import dev.asl.api.config.AslProperties;
import dev.asl.api.results.ResultsResponse.Difference;
import dev.asl.api.results.ResultsResponse.PopulationResults;
import dev.asl.api.results.ResultsResponse.Row;
import dev.asl.api.run.RunScenarios;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

@Service
class ResultsService {

	/** One row per world. Worlds with no valid rating have no accuracy and are left out of the means. */
	private static final String SQL = """
			SELECT model, condition, accuracy, parse_failures, truncations, llm_call_count, probe_count,
			       recognised_sample
			FROM runs
			WHERE pilot = false AND experiment = 'cascade_v1' AND scenario = 'triage_cascade'
			  AND prompt_version = :promptVersion AND model IN (:populations)
			ORDER BY model, condition, seed
			""";

	private record World(String population, String condition, Double accuracy, int parseFailures, int truncations,
			int calls, int probes, int recognised) {
	}

	private final JdbcClient jdbc;
	private final AslProperties props;

	ResultsService(JdbcClient jdbc, AslProperties props) {
		this.jdbc = jdbc;
		this.props = props;
	}

	ResultsResponse results() {
		List<String> populations = props.studyPopulations();
		List<World> worlds = populations.isEmpty() ? List.of()
				: jdbc.sql(SQL).param("promptVersion", props.promptVersion()).param("populations", populations)
						.query((rs, i) -> new World(rs.getString("model"), rs.getString("condition"),
								(Double) rs.getObject("accuracy"), rs.getInt("parse_failures"),
								rs.getInt("truncations"), rs.getInt("llm_call_count"), rs.getInt("probe_count"),
								rs.getInt("recognised_sample")))
						.list();

		List<String> conditions = RunScenarios.CONDITIONS.get(RunScenarios.SCENARIO);
		List<PopulationResults> out = new ArrayList<>();
		for (String population : populations) {
			List<Row> rows = new ArrayList<>();
			List<Difference> diffs = new ArrayList<>();
			double[] baseline = accuracies(worlds, population, conditions.get(0));
			for (String condition : conditions) {
				List<World> cell = worlds.stream()
						.filter(w -> w.population().equals(population) && w.condition().equals(condition)).toList();
				double[] acc = accuracies(worlds, population, condition);
				if (cell.isEmpty() || acc.length == 0) {
					continue;
				}
				double[] ci = BootstrapInterval.mean(acc);
				long calls = cell.stream().mapToLong(World::calls).sum();
				long probes = cell.stream().mapToLong(World::probes).sum();
				rows.add(new Row(condition, cell.size(), ci[0], ci[1], ci[2],
						calls == 0 ? 0 : (double) cell.stream().mapToLong(World::parseFailures).sum() / calls,
						calls == 0 ? 0 : (double) cell.stream().mapToLong(World::truncations).sum() / calls,
						probes == 0 ? null : (double) cell.stream().mapToLong(World::recognised).sum() / probes));
				if (!condition.equals(conditions.get(0)) && baseline.length > 0) {
					double[] d = BootstrapInterval.difference(acc, baseline);
					diffs.add(new Difference(condition + "-" + conditions.get(0), d[0], d[1], d[2]));
				}
			}
			out.add(new PopulationResults(population, rows, diffs));
		}
		return new ResultsResponse(out, props.traceLinks());
	}

	private static double[] accuracies(List<World> worlds, String population, String condition) {
		return worlds.stream().filter(w -> w.population().equals(population) && w.condition().equals(condition)
				&& w.accuracy() != null).mapToDouble(World::accuracy).toArray();
	}
}
