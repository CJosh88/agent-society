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

	private static final String TOWN_ID = "fc647cdf-8de8-5e3f-a1cf-1a3858866d62";
	private static final String OFFICE_ID = "43bb03b3-4f79-55ab-a4ad-43b8a2a78150";

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
		Map<String, Object> b = Fixtures.withNewId(Fixtures.town());
		breakIt.accept(b);
		submit(b).andExpect(status().isBadRequest()).andExpect(jsonPath("$.status").value(400));
	}

	@Test
	void townFixtureIsStoredWithDerivedFields() throws Exception {
		submit(Fixtures.town()).andExpect(status().isCreated()).andExpect(jsonPath("$.id").value(TOWN_ID));

		mvc.perform(get("/api/runs/" + TOWN_ID)).andExpect(status().isOk())
				.andExpect(jsonPath("$.run.focalHelped").value(true))
				.andExpect(jsonPath("$.run.focalHelpTick").value(8))
				.andExpect(jsonPath("$.run.earlyHelp").value(false))
				.andExpect(jsonPath("$.run.recognized").value(false))
				.andExpect(jsonPath("$.run.promptVersion").value("v1"))
				.andExpect(jsonPath("$.agents", hasSize(6)));

		mvc.perform(get("/api/runs")).andExpect(status().isOk())
				.andExpect(jsonPath("$.page.totalElements").value(1))
				.andExpect(jsonPath("$.content[0].parseFailures").value(0))
				.andExpect(jsonPath("$.content[0].truncations").value(0));

		Integer decisions = jdbc.sql("SELECT decision_count FROM runs WHERE id = ?").param(UUID.fromString(TOWN_ID))
				.query(Integer.class).single();
		org.assertj.core.api.Assertions.assertThat(decisions).isEqualTo(8);
	}

	@Test
	void officeFixtureCountsParseFailureAndTruncation() throws Exception {
		submit(Fixtures.office()).andExpect(status().isCreated());

		mvc.perform(get("/api/runs/" + OFFICE_ID)).andExpect(status().isOk())
				.andExpect(jsonPath("$.run.focalHelpTick").value(4))
				.andExpect(jsonPath("$.run.earlyHelp").value(true))
				.andExpect(jsonPath("$.agents", hasSize(1)));
		mvc.perform(get("/api/runs")).andExpect(jsonPath("$.content[0].parseFailures").value(1))
				.andExpect(jsonPath("$.content[0].truncations").value(1));

		Map<String, Object> counts = jdbc.sql("SELECT decision_count, llm_call_count FROM runs WHERE id = ?")
				.param(UUID.fromString(OFFICE_ID)).query().singleRow();
		org.assertj.core.api.Assertions.assertThat(counts.get("decision_count")).isEqualTo(4);
		org.assertj.core.api.Assertions.assertThat(counts.get("llm_call_count")).isEqualTo(6);
	}

	@Test
	void eventsComeBackOrderedWithPayloadUnchanged() throws Exception {
		submit(Fixtures.town()).andExpect(status().isCreated());
		mvc.perform(get("/api/runs/" + TOWN_ID + "/events")).andExpect(status().isOk())
				.andExpect(jsonPath("$", hasSize(23))).andExpect(jsonPath("$[0].seq").value(0))
				.andExpect(jsonPath("$[16].type").value("AGENT_APPROACHED"))
				.andExpect(jsonPath("$[16].agentId").value("focal"))
				.andExpect(jsonPath("$[16].payload.counts_as_help").value(false))
				.andExpect(jsonPath("$[18].type").value("AGENT_SAID"))
				.andExpect(jsonPath("$[18].agentId").value("focal"))
				.andExpect(jsonPath("$[18].payload.counts_as_help").value(true))
				.andExpect(jsonPath("$[22].type").value("RUN_ENDED"))
				.andExpect(jsonPath("$[22].agentId").doesNotExist());
	}

	@Test
	void repeatPostReturns409() throws Exception {
		submit(Fixtures.town()).andExpect(status().isCreated());
		submit(Fixtures.town()).andExpect(status().isConflict()).andExpect(jsonPath("$.status").value(409));
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
		submit(Fixtures.town()).andExpect(status().isCreated());
		submit(Fixtures.office()).andExpect(status().isCreated());
		mvc.perform(get("/api/runs?scenario=office")).andExpect(jsonPath("$.page.totalElements").value(1))
				.andExpect(jsonPath("$.content[0].id").value(OFFICE_ID));
		mvc.perform(get("/api/runs?model=claude-haiku-5-5&condition=group5"))
				.andExpect(jsonPath("$.content[0].id").value(TOWN_ID));
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
	void wrongVictimCountIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("scenario", "office"));
	}

	@Test
	void seqGapIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(22).put("seq", 23));
	}

	@Test
	void duplicateSeqIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(22).put("seq", 21));
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
		expect400(b -> Fixtures.list(b, "events").get(22).put("type", "AGENT_WAITED"));
	}

	@Test
	void runEndedNotLastIs400() throws Exception {
		expect400(b -> {
			List<Map<String, Object>> events = Fixtures.list(b, "events");
			events.get(22).put("seq", 3);
			events.get(3).put("seq", 22);
		});
	}

	@Test
	void twoRunEndedIs400() throws Exception {
		expect400(b -> {
			Map<String, Object> e = Fixtures.list(b, "events").get(21);
			e.put("type", "RUN_ENDED");
			e.put("agent_id", null);
			e.put("payload", Map.of("reason", "max_ticks"));
		});
	}
}
