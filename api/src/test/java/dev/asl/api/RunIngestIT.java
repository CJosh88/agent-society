package dev.asl.api;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class RunIngestIT {

	private static final String TRIAGE_ID = "45ea0034-a628-5a11-804d-f627ed12c8c6";
	private static final String FATIGUE_ID = "5c822339-6058-5c73-8f01-be2de253a72f";

	@Autowired
	MockMvc mvc;
	@Autowired
	JdbcClient jdbc;

	@BeforeEach
	void clean() {
		jdbc.sql("DELETE FROM runs").update();
	}

	private ResultActions submit(Map<String, Object> bundle) throws Exception {
		return mvc.perform(post("/api/admin/runs").header("X-Admin-Key", Fixtures.ADMIN_KEY)
				.contentType(MediaType.APPLICATION_JSON).content(Fixtures.json(bundle)));
	}

	private void expect400(Consumer<Map<String, Object>> breakIt) throws Exception {
		Map<String, Object> b = Fixtures.withNewId(Fixtures.triage());
		breakIt.accept(b);
		submit(b).andExpect(status().isBadRequest()).andExpect(jsonPath("$.status").value(400));
	}

	@Test
	void triageFixtureIsStoredWithDerivedFields() throws Exception {
		submit(Fixtures.triage()).andExpect(status().isCreated()).andExpect(jsonPath("$.id").value(TRIAGE_ID));

		mvc.perform(get("/api/runs/" + TRIAGE_ID)).andExpect(status().isOk())
				.andExpect(jsonPath("$.run.focalHelped").value(true))
				.andExpect(jsonPath("$.run.focalHelpTick").value(6))
				.andExpect(jsonPath("$.run.earlyHelp").value(false))
				.andExpect(jsonPath("$.run.recognized").value(false))
				.andExpect(jsonPath("$.run.promptVersion").value("v2"))
				.andExpect(jsonPath("$.agents", hasSize(5)));

		mvc.perform(get("/api/runs")).andExpect(status().isOk())
				.andExpect(jsonPath("$.page.totalElements").value(1))
				.andExpect(jsonPath("$.content[0].parseFailures").value(0))
				.andExpect(jsonPath("$.content[0].truncations").value(0));

		Integer decisions = jdbc.sql("SELECT decision_count FROM runs WHERE id = ?").param(UUID.fromString(TRIAGE_ID))
				.query(Integer.class).single();
		org.assertj.core.api.Assertions.assertThat(decisions).isEqualTo(4);
	}

	@Test
	void fatigueFixtureCountsParseFailureAndTruncation() throws Exception {
		submit(Fixtures.fatigue()).andExpect(status().isCreated());

		mvc.perform(get("/api/runs/" + FATIGUE_ID)).andExpect(status().isOk())
				.andExpect(jsonPath("$.run.focalHelpTick").value(10))
				.andExpect(jsonPath("$.run.earlyHelp").value(true))
				.andExpect(jsonPath("$.agents", hasSize(1)));
		mvc.perform(get("/api/runs")).andExpect(jsonPath("$.content[0].parseFailures").value(1))
				.andExpect(jsonPath("$.content[0].truncations").value(1));

		Map<String, Object> counts = jdbc.sql("SELECT decision_count, llm_call_count FROM runs WHERE id = ?")
				.param(UUID.fromString(FATIGUE_ID)).query().singleRow();
		org.assertj.core.api.Assertions.assertThat(counts.get("decision_count")).isEqualTo(10);
		org.assertj.core.api.Assertions.assertThat(counts.get("llm_call_count")).isEqualTo(13);
	}

	@Test
	void eventsComeBackOrderedWithPayloadUnchanged() throws Exception {
		submit(Fixtures.triage()).andExpect(status().isCreated());
		mvc.perform(get("/api/runs/" + TRIAGE_ID + "/events")).andExpect(status().isOk())
				.andExpect(jsonPath("$", hasSize(16))).andExpect(jsonPath("$[0].seq").value(0))
				.andExpect(jsonPath("$[5].type").value("NOTICE_SHOWN"))
				.andExpect(jsonPath("$[5].agentId").doesNotExist())
				.andExpect(jsonPath("$[5].payload.real").value(true))
				.andExpect(jsonPath("$[13].type").value("AGENT_PRIORITY_SET"))
				.andExpect(jsonPath("$[13].agentId").value("focal"))
				.andExpect(jsonPath("$[13].payload.counts_as_help").value(true))
				.andExpect(jsonPath("$[15].type").value("RUN_ENDED"))
				.andExpect(jsonPath("$[15].agentId").doesNotExist());
	}

	@Test
	void repeatPostReturns409() throws Exception {
		submit(Fixtures.triage()).andExpect(status().isCreated());
		submit(Fixtures.triage()).andExpect(status().isConflict()).andExpect(jsonPath("$.status").value(409));
	}

	@Test
	void unknownRunIs404() throws Exception {
		mvc.perform(get("/api/runs/" + UUID.randomUUID())).andExpect(status().isNotFound());
		mvc.perform(get("/api/runs/" + UUID.randomUUID() + "/events")).andExpect(status().isNotFound());
	}

	@Test
	void unknownFilterValueIs400() throws Exception {
		mvc.perform(get("/api/runs?scenario=nope")).andExpect(status().isBadRequest());
		mvc.perform(get("/api/runs?condition=nope")).andExpect(status().isBadRequest());
	}

	@Test
	void filtersAndPaging() throws Exception {
		submit(Fixtures.triage()).andExpect(status().isCreated());
		submit(Fixtures.fatigue()).andExpect(status().isCreated());
		mvc.perform(get("/api/runs?scenario=alert_fatigue")).andExpect(jsonPath("$.page.totalElements").value(1))
				.andExpect(jsonPath("$.content[0].id").value(FATIGUE_ID));
		mvc.perform(get("/api/runs?model=claude-haiku-5-5&condition=dismiss"))
				.andExpect(jsonPath("$.content[0].id").value(TRIAGE_ID));
		mvc.perform(get("/api/runs?size=1")).andExpect(jsonPath("$.content", hasSize(1)))
				.andExpect(jsonPath("$.page.totalPages").value(2));
	}

	@Test
	void unknownPropertyIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("surprise", 1));
	}

	@Test
	void shapeViolationIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("scenario", "moon"));
	}

	@Test
	void tickOutOfRangeIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(6).put("tick", 13));
	}

	@Test
	void twoFocalAgentsIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "agents").get(1).put("role", "focal"));
	}

	@Test
	void wrongScriptedCountIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("condition", "alone"));
	}

	@Test
	void conditionFromAnotherScenarioIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("scenario", "alert_fatigue"));
	}

	@Test
	void seqGapIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(15).put("seq", 16));
	}

	@Test
	void duplicateSeqIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(15).put("seq", 14));
	}

	@Test
	void eventForUnknownAgentIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(6).put("agent_id", "s9"));
	}

	@Test
	void llmCallForUnknownAgentIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "llm_calls").get(0).put("agent_id", "s9"));
	}

	@Test
	void missingRunEndedIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(15).put("type", "AGENT_WAITED"));
	}

	@Test
	void runEndedNotLastIs400() throws Exception {
		expect400(b -> {
			List<Map<String, Object>> events = Fixtures.list(b, "events");
			events.get(15).put("seq", 3);
			events.get(3).put("seq", 15);
		});
	}

	@Test
	void twoRunEndedIs400() throws Exception {
		expect400(b -> {
			Map<String, Object> e = Fixtures.list(b, "events").get(14);
			e.put("type", "RUN_ENDED");
			e.put("agent_id", null);
			e.put("payload", Map.of("reason", "max_ticks"));
		});
	}
}
