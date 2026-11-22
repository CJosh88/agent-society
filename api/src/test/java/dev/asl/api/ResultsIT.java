package dev.asl.api;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;

import dev.asl.api.results.NewcombeInterval;
import dev.asl.api.results.WilsonInterval;

import org.hamcrest.BaseMatcher;
import org.hamcrest.Description;
import org.hamcrest.Matcher;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class ResultsIT {

	@Autowired
	MockMvc mvc;
	@Autowired
	JdbcClient jdbc;

	@BeforeEach
	void clean() {
		jdbc.sql("DELETE FROM runs").update();
	}

	/** Inserts count runs, the first {@code helped} of which helped at tick 4 (the rest never helped). */
	private void seed(String scenario, String condition, String model, boolean pilot, String promptVersion, int count,
			int helped) {
		for (int i = 0; i < count; i++) {
			boolean h = i < helped;
			jdbc.sql("""
					INSERT INTO runs (id, experiment, scenario, condition, model, seed, prompt_version, engine_version,
					  pilot, started_at, ended_at, focal_helped, early_help, focal_help_tick, decision_count,
					  parse_failures, truncations, llm_call_count, recognized)
					VALUES (:id, 'agent_society_v1', :scenario, :condition, :model, :seed, :pv, '0.1.0',
					  :pilot, :t, :t, :h, :h, :tick, 10, 1, 0, 11, false)
					""").param("id", UUID.randomUUID()).param("scenario", scenario).param("condition", condition)
					.param("model", model).param("seed", i).param("pv", promptVersion).param("pilot", pilot)
					.param("t", java.sql.Timestamp.from(Instant.now())).param("h", h)
					.param("tick", h ? 4 : null, java.sql.Types.INTEGER).update();
		}
	}

	/** JSON numbers may arrive as Double or BigDecimal, so Hamcrest's closeTo(Double) is not usable here. */
	private static Matcher<Object> near(double expected, double tolerance) {
		return new BaseMatcher<>() {
			@Override
			public boolean matches(Object item) {
				return item instanceof Number n && Math.abs(n.doubleValue() - expected) < tolerance;
			}

			@Override
			public void describeTo(Description d) {
				d.appendText("a number within " + tolerance + " of " + expected);
			}
		};
	}

	@Test
	void ratesAndIntervalsCountOnlyStudyRuns() throws Exception {
		seed("office", "alone", "llama-3.1-8b", false, "v1", 10, 9);
		seed("office", "group5", "llama-3.1-8b", false, "v1", 10, 3);
		// None of these may be counted:
		seed("office", "alone", "llama-3.1-8b", true, "v1", 5, 0); // pilot
		seed("office", "alone", "fake", false, "v1", 5, 0); // not a study model
		seed("office", "alone", "llama-3.1-8b", false, "v0", 5, 0); // other prompt version

		double[] alone = WilsonInterval.of(9, 10);
		double[] diff = NewcombeInterval.difference(3, 10, 9, 10);

		mvc.perform(get("/api/results")).andExpect(status().isOk())
				.andExpect(jsonPath("$.scenarios", hasSize(2)))
				.andExpect(jsonPath("$.scenarios[0].scenario").value("town_square"))
				.andExpect(jsonPath("$.scenarios[0].rows", hasSize(0)))
				.andExpect(jsonPath("$.scenarios[0].baseline").doesNotExist())
				.andExpect(jsonPath("$.scenarios[1].scenario").value("office"))
				.andExpect(jsonPath("$.scenarios[1].rows", hasSize(2)))
				.andExpect(jsonPath("$.scenarios[1].rows[0].condition").value("alone"))
				.andExpect(jsonPath("$.scenarios[1].rows[0].n").value(10))
				.andExpect(jsonPath("$.scenarios[1].rows[0].helped").value(9))
				.andExpect(jsonPath("$.scenarios[1].rows[0].rate").value(0.9))
				.andExpect(jsonPath("$.scenarios[1].rows[0].ciLow").value(near(alone[0], 1e-9)))
				.andExpect(jsonPath("$.scenarios[1].rows[0].ciHigh").value(near(alone[1], 1e-9)))
				.andExpect(jsonPath("$.scenarios[1].rows[0].earlyRate").value(0.9))
				.andExpect(jsonPath("$.scenarios[1].rows[0].medianHelpTick").value(4.0))
				.andExpect(jsonPath("$.scenarios[1].rows[0].parseFailureRate").value(0.1))
				.andExpect(jsonPath("$.scenarios[1].rows[0].truncationRate").value(0.0))
				.andExpect(jsonPath("$.scenarios[1].rows[0].recognitionRate").value(0.0))
				.andExpect(jsonPath("$.scenarios[1].rows[1].condition").value("group5"))
				.andExpect(jsonPath("$.scenarios[1].rows[1].rate").value(0.3))
				.andExpect(jsonPath("$.scenarios[1].differences", hasSize(1)))
				.andExpect(jsonPath("$.scenarios[1].differences[0].comparison").value("group5-alone"))
				.andExpect(jsonPath("$.scenarios[1].differences[0].diff").value(near(-0.6, 1e-9)))
				.andExpect(jsonPath("$.scenarios[1].differences[0].ciLow").value(near(diff[1], 1e-9)))
				.andExpect(jsonPath("$.scenarios[1].differences[0].ciHigh").value(near(diff[2], 1e-9)));
	}

	@Test
	void medianHelpTickIsNullWhenNobodyHelped() throws Exception {
		seed("office", "group5", "gpt-oss-120b", false, "v1", 4, 0);
		mvc.perform(get("/api/results")).andExpect(status().isOk())
				.andExpect(jsonPath("$.scenarios[1].rows[0].rate").value(0.0))
				.andExpect(jsonPath("$.scenarios[1].rows[0].medianHelpTick").doesNotExist());
	}
}
