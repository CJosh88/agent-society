package dev.asl.api.run;

import java.time.Instant;
import java.util.UUID;

import dev.asl.api.run.RunExceptions.AlreadyExists;
import dev.asl.api.run.dto.RunBundle;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RunIngestService {

	private final BundleValidator validator;
	private final RunRepository runs;
	private final AgentRepository agents;
	private final EventRepository events;
	private final LlmCallRepository llmCalls;

	RunIngestService(BundleValidator validator, RunRepository runs, AgentRepository agents, EventRepository events,
			LlmCallRepository llmCalls) {
		this.validator = validator;
		this.runs = runs;
		this.agents = agents;
		this.events = events;
		this.llmCalls = llmCalls;
	}

	@Transactional
	public UUID ingest(RunBundle b) {
		validator.validate(b);
		UUID id = b.run().id();
		if (runs.existsById(id)) {
			throw new AlreadyExists(id);
		}
		// A concurrent duplicate fails here with DataIntegrityViolationException, which maps to 409.
		runs.saveAndFlush(toRun(b));
		agents.saveAll(b.agents().stream().map(a -> {
			Agent e = new Agent();
			e.runId = id;
			e.agentId = a.agentId();
			e.name = a.name();
			e.role = a.role();
			e.persona = a.persona();
			return e;
		}).toList());
		events.saveAll(b.events().stream().map(x -> {
			Event e = new Event();
			e.runId = id;
			e.seq = x.seq();
			e.tick = x.tick();
			e.type = x.type();
			e.agentId = x.agentId();
			e.payload = x.payload();
			return e;
		}).toList());
		llmCalls.saveAll(b.llmCalls().stream().map(c -> {
			LlmCall e = new LlmCall();
			e.runId = id;
			e.agentId = c.agentId();
			e.tick = c.tick();
			e.kind = c.kind();
			e.attempt = c.attempt();
			e.prompt = c.prompt();
			e.responseText = c.responseText();
			e.reasoningText = c.reasoningText();
			e.finishReason = c.finishReason();
			e.inputTokens = c.inputTokens();
			e.outputTokens = c.outputTokens();
			e.tokensEstimated = c.tokensEstimated();
			e.parsedOk = c.parsedOk();
			e.latencyMs = c.latencyMs();
			return e;
		}).toList());
		events.flush();
		llmCalls.flush();

		return id;
	}

	private Run toRun(RunBundle b) {
		RunBundle.RunInfo info = b.run();
		Run r = new Run();
		r.id = info.id();
		r.experiment = info.experiment();
		r.scenario = info.scenario();
		r.condition = info.condition();
		r.model = info.population();
		r.seed = info.worldSeed();
		r.promptVersion = info.promptVersion();
		r.engineVersion = info.engineVersion();
		r.pilot = info.pilot();
		r.startedAt = info.startedAt();
		r.endedAt = info.endedAt();
		r.createdAt = Instant.now();

		// Accuracy is over every rating in the world, scripted agents included: correct ratings / all ratings.
		var ratings = b.events().stream().filter(e -> e.type().equals("AGENT_RATED")).toList();
		r.ratedCount = ratings.size();
		long correct = ratings.stream().filter(e -> e.payload().get("correct") == Boolean.TRUE).count();
		r.accuracy = ratings.isEmpty() ? null : (double) correct / ratings.size();
		r.parseFailures = (int) b.events().stream().filter(e -> e.type().equals("ACTION_PARSE_FAILED")).count();
		r.truncations = (int) b.llmCalls().stream()
				.filter(c -> "length".equals(c.finishReason()) || "max_tokens".equals(c.finishReason())).count();
		r.llmCallCount = b.llmCalls().size();
		var probes = b.events().stream().filter(e -> e.type().equals("PROBE_ANSWERED")).toList();
		r.probeCount = probes.size();
		r.recognisedSample = (int) probes.stream().filter(e -> e.payload().get("recognized") == Boolean.TRUE).count();
		return r;
	}
}
