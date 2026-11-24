package dev.asl.api;

import static org.assertj.core.api.Assertions.assertThat;
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

	private static final String WEAK_ID = "0308b50f-23e0-533d-82d4-f66907929be7";
	private static final String SEEDED_ID = "727e1a12-3f57-5394-854b-c77bd7fd2957";

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

	/** Breaks one rule of a fresh copy of the weak fixture and expects a 400. */
	private void expect400(Consumer<Map<String, Object>> breakIt) throws Exception {
		Map<String, Object> b = Fixtures.withNewId(Fixtures.weak());
		breakIt.accept(b);
		submit(b).andExpect(status().isBadRequest()).andExpect(jsonPath("$.status").value(400));
	}

	@SuppressWarnings("unchecked")
	private static Map<String, Object> payload(Map<String, Object> event) {
		return (Map<String, Object>) event.get("payload");
	}

	@Test
	void weakFixtureIsStoredWithDerivedFields() throws Exception {
		submit(Fixtures.weak()).andExpect(status().isCreated()).andExpect(jsonPath("$.id").value(WEAK_ID));

		mvc.perform(get("/api/runs/" + WEAK_ID)).andExpect(status().isOk())
				.andExpect(jsonPath("$.run.population").value("llama-3.1-8b"))
				.andExpect(jsonPath("$.run.worldSeed").value(0))
				.andExpect(jsonPath("$.run.promptVersion").value("c1"))
				.andExpect(jsonPath("$.run.accuracy").value(1.0))
				.andExpect(jsonPath("$.run.ratedCount").value(24))
				.andExpect(jsonPath("$.run.probeCount").value(1))
				.andExpect(jsonPath("$.run.recognisedSample").value(0))
				.andExpect(jsonPath("$.agents", hasSize(6)));

		mvc.perform(get("/api/runs")).andExpect(status().isOk())
				.andExpect(jsonPath("$.page.totalElements").value(1))
				.andExpect(jsonPath("$.content[0].parseFailures").value(1))
				.andExpect(jsonPath("$.content[0].truncations").value(0));

		Integer calls = jdbc.sql("SELECT llm_call_count FROM runs WHERE id = ?").param(UUID.fromString(WEAK_ID))
				.query(Integer.class).single();
		assertThat(calls).isEqualTo(8);
	}

	@Test
	void seededWrongFixtureCountsScriptedRatingsInAccuracy() throws Exception {
		submit(Fixtures.seededWrong()).andExpect(status().isCreated());
		Double accuracy = jdbc.sql("SELECT accuracy FROM runs WHERE id = ?").param(UUID.fromString(SEEDED_ID))
				.query(Double.class).single();
		assertThat(accuracy).isEqualTo(14.0 / 24.0);
		mvc.perform(get("/api/runs/" + SEEDED_ID)).andExpect(jsonPath("$.agents[0].role").value("scripted"));
	}

	@Test
	void independentWorldWithNullCountsIsAccepted() throws Exception {
		Map<String, Object> b = Fixtures.withNewId(Fixtures.weak());
		Fixtures.run(b).put("condition", "independent");
		Fixtures.events(b, "TICKETS_SHOWN").forEach(e -> payload(e).put("counts", null));
		submit(b).andExpect(status().isCreated());
	}

	@Test
	void eventsComeBackOrderedWithPayloadUnchanged() throws Exception {
		submit(Fixtures.weak()).andExpect(status().isCreated());
		mvc.perform(get("/api/runs/" + WEAK_ID + "/events")).andExpect(status().isOk())
				.andExpect(jsonPath("$", hasSize(45))).andExpect(jsonPath("$[0].seq").value(0))
				.andExpect(jsonPath("$[0].type").value("AGENT_SPAWNED"))
				.andExpect(jsonPath("$[0].payload.position").value(1))
				.andExpect(jsonPath("$[1].type").value("TICKETS_SHOWN"))
				.andExpect(jsonPath("$[1].payload.order", hasSize(24)))
				.andExpect(jsonPath("$[2].type").value("AGENT_PICKED"))
				.andExpect(jsonPath("$[2].payload.ticket_ids", hasSize(4)))
				.andExpect(jsonPath("$[44].type").value("RUN_ENDED"))
				.andExpect(jsonPath("$[44].agentId").doesNotExist());
	}

	@Test
	void repeatPostReturns409() throws Exception {
		submit(Fixtures.weak()).andExpect(status().isCreated());
		submit(Fixtures.weak()).andExpect(status().isConflict()).andExpect(jsonPath("$.status").value(409));
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
		mvc.perform(get("/api/runs?population=nope")).andExpect(status().isBadRequest());
	}

	@Test
	void filtersAndPaging() throws Exception {
		submit(Fixtures.weak()).andExpect(status().isCreated());
		submit(Fixtures.seededWrong()).andExpect(status().isCreated());
		mvc.perform(get("/api/runs?condition=seeded_wrong")).andExpect(jsonPath("$.page.totalElements").value(1))
				.andExpect(jsonPath("$.content[0].id").value(SEEDED_ID));
		mvc.perform(get("/api/runs?population=llama-3.1-8b&condition=weak"))
				.andExpect(jsonPath("$.content[0].id").value(WEAK_ID));
		mvc.perform(get("/api/runs?size=1")).andExpect(jsonPath("$.content", hasSize(1)))
				.andExpect(jsonPath("$.page.totalPages").value(2));
	}

	@Test
	void unknownPropertyIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("surprise", 1));
	}

	@Test
	void oldBundleFieldsAreRejected() throws Exception {
		expect400(b -> Fixtures.run(b).put("model", "llama-3.1-8b"));
	}

	@Test
	void shapeViolationIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("scenario", "moon"));
	}

	@Test
	void unknownPopulationIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("population", "granite"));
	}

	@Test
	void tickOutOfRangeIs400() throws Exception {
		expect400(b -> Fixtures.events(b, "AGENT_RATED").get(0).put("tick", 201));
	}

	@Test
	void agentIdOutOfRangeIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "agents").get(5).put("agent_id", "a201"));
	}

	@Test
	void duplicateAgentIdIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "agents").get(1).put("agent_id", "a1"));
	}

	@Test
	void agentGapIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "agents").get(5).put("agent_id", "a7"));
	}

	@Test
	void scriptedAgentInWeakIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "agents").get(0).put("role", "scripted"));
	}

	@Test
	void seededWrongWithoutScriptedAgentsIs400() throws Exception {
		Map<String, Object> b = Fixtures.withNewId(Fixtures.seededWrong());
		Fixtures.list(b, "agents").forEach(a -> a.put("role", "agent"));
		submit(b).andExpect(status().isBadRequest());
	}

	@Test
	void scriptedAgentsNotAtTheStartIs400() throws Exception {
		Map<String, Object> b = Fixtures.withNewId(Fixtures.seededWrong());
		Fixtures.list(b, "agents").get(0).put("role", "agent");
		Fixtures.list(b, "agents").get(4).put("role", "scripted");
		submit(b).andExpect(status().isBadRequest());
	}

	@Test
	void mixedPopulationWithSeededWrongIs400() throws Exception {
		Map<String, Object> b = Fixtures.withNewId(Fixtures.seededWrong());
		Fixtures.run(b).put("population", "mix_early");
		submit(b).andExpect(status().isBadRequest());
	}

	@Test
	void countsInIndependentIs400() throws Exception {
		expect400(b -> Fixtures.run(b).put("condition", "independent"));
	}

	@Test
	void nullCountsInWeakIs400() throws Exception {
		expect400(b -> payload(Fixtures.event(b, "TICKETS_SHOWN")).put("counts", null));
	}

	@Test
	void eventTickNotItsAgentPositionIs400() throws Exception {
		expect400(b -> Fixtures.event(b, "AGENT_PICKED").put("tick", 2));
	}

	@Test
	void spawnedPositionMismatchIs400() throws Exception {
		expect400(b -> payload(Fixtures.event(b, "AGENT_SPAWNED")).put("position", 2));
	}

	@Test
	void ratedTicketThatWasNotPickedIs400() throws Exception {
		expect400(b -> {
			Map<String, Object> picked = payload(Fixtures.event(b, "AGENT_PICKED"));
			@SuppressWarnings("unchecked")
			List<Object> ids = (List<Object>) picked.get("ticket_ids");
			ids.set(0, "T24".equals(ids.get(0)) ? "T23" : "T24");
		});
	}

	@Test
	void ratedWithoutAnyPickIs400() throws Exception {
		expect400(b -> Fixtures.event(b, "AGENT_PICKED").put("type", "ACTION_PARSE_FAILED"));
	}

	@Test
	void seqGapIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(44).put("seq", 45));
	}

	@Test
	void duplicateSeqIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "events").get(44).put("seq", 43));
	}

	@Test
	void eventForUnknownAgentIs400() throws Exception {
		expect400(b -> Fixtures.event(b, "AGENT_RATED").put("agent_id", "a9"));
	}

	@Test
	void llmCallForUnknownAgentIs400() throws Exception {
		expect400(b -> Fixtures.list(b, "llm_calls").get(0).put("agent_id", "a9"));
	}

	@Test
	void missingRunEndedIs400() throws Exception {
		expect400(b -> Fixtures.event(b, "RUN_ENDED").put("type", "PROBE_ANSWERED"));
	}

	@Test
	void runEndedNotLastIs400() throws Exception {
		expect400(b -> {
			List<Map<String, Object>> events = Fixtures.list(b, "events");
			events.get(44).put("seq", 3);
			events.get(3).put("seq", 44);
		});
	}

	@Test
	void twoRunEndedIs400() throws Exception {
		expect400(b -> {
			Map<String, Object> e = Fixtures.list(b, "events").get(43);
			e.put("type", "RUN_ENDED");
			e.put("agent_id", null);
			e.put("payload", Map.of("reason", "all_agents_done"));
		});
	}
}
