package dev.asl.api;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;

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

	/** Inserts count worlds (seeds 0..count-1) with the same accuracy: 2 parse failures and 1 truncation in 100 calls. */
	private void seed(String experiment, String condition, String population, boolean pilot, String promptVersion,
			int count, double accuracy) {
		for (int i = 0; i < count; i++) {
			jdbc.sql("""
					INSERT INTO runs (id, experiment, scenario, condition, model, seed, prompt_version, engine_version,
					  pilot, started_at, ended_at, accuracy, rated_count, parse_failures, truncations, llm_call_count,
					  probe_count, recognised_sample)
					VALUES (:id, :experiment, 'triage_cascade', :condition, :population, :seed, :pv, '0.1.0',
					  :pilot, :t, :t, :accuracy, 800, 2, 1, 100, 10, 2)
					""").param("id", UUID.randomUUID()).param("experiment", experiment).param("condition", condition)
					.param("population", population).param("seed", i).param("pv", promptVersion)
					.param("pilot", pilot).param("t", java.sql.Timestamp.from(Instant.now()))
					.param("accuracy", accuracy).update();
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
	void meansAndDifferencesCountOnlyStudyRuns() throws Exception {
		seed("cascade_v1", "independent", "llama-3.1-8b", false, "c1", 8, 0.8);
		seed("cascade_v1", "weak", "llama-3.1-8b", false, "c1", 8, 0.6);
		// None of these may be counted:
		seed("cascade_v1", "independent", "llama-3.1-8b", true, "c1", 5, 0.0); // pilot
		seed("cascade_v1", "independent", "fake", false, "c1", 5, 0.0); // not a study population
		seed("cascade_v1", "independent", "llama-3.1-8b", false, "c0", 5, 0.0); // other prompt version
		seed("cascade_rl_v1", "independent", "llama-3.1-8b", false, "c1", 5, 0.0); // other experiment

		mvc.perform(get("/api/results")).andExpect(status().isOk())
				.andExpect(jsonPath("$.traceLinks", hasSize(0)))
				.andExpect(jsonPath("$.populations", hasSize(5)))
				.andExpect(jsonPath("$.populations[0].population").value("llama-3.1-8b"))
				.andExpect(jsonPath("$.populations[1].rows", hasSize(0)))
				.andExpect(jsonPath("$.populations[0].rows", hasSize(2)))
				.andExpect(jsonPath("$.populations[0].rows[0].condition").value("independent"))
				.andExpect(jsonPath("$.populations[0].rows[0].n").value(8))
				.andExpect(jsonPath("$.populations[0].rows[0].meanAccuracy").value(near(0.8, 1e-9)))
				.andExpect(jsonPath("$.populations[0].rows[0].ciLow").value(near(0.8, 1e-9)))
				.andExpect(jsonPath("$.populations[0].rows[0].ciHigh").value(near(0.8, 1e-9)))
				.andExpect(jsonPath("$.populations[0].rows[0].parseFailureRate").value(near(0.02, 1e-9)))
				.andExpect(jsonPath("$.populations[0].rows[0].truncationRate").value(near(0.01, 1e-9)))
				.andExpect(jsonPath("$.populations[0].rows[0].recognitionRate").value(near(0.2, 1e-9)))
				.andExpect(jsonPath("$.populations[0].rows[1].condition").value("weak"))
				.andExpect(jsonPath("$.populations[0].rows[1].meanAccuracy").value(near(0.6, 1e-9)))
				.andExpect(jsonPath("$.populations[0].differences", hasSize(1)))
				.andExpect(jsonPath("$.populations[0].differences[0].comparison").value("weak-independent"))
				.andExpect(jsonPath("$.populations[0].differences[0].diff").value(near(-0.2, 1e-9)))
				.andExpect(jsonPath("$.populations[0].differences[0].ciLow").value(near(-0.2, 1e-9)))
				.andExpect(jsonPath("$.populations[0].differences[0].ciHigh").value(near(-0.2, 1e-9)));
	}

	@Test
	void worldsWithoutAnyRatingAreCountedButNotAveraged() throws Exception {
		seed("cascade_v1", "independent", "gpt-oss-120b", false, "c1", 3, 0.7);
		jdbc.sql("UPDATE runs SET accuracy = NULL, rated_count = 0 WHERE seed = 0").update();
		mvc.perform(get("/api/results")).andExpect(status().isOk())
				.andExpect(jsonPath("$.populations[1].rows[0].n").value(3))
				.andExpect(jsonPath("$.populations[1].rows[0].meanAccuracy").value(near(0.7, 1e-9)));
	}
}
