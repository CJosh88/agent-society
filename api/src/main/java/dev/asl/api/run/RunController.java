package dev.asl.api.run;

import java.util.List;
import java.util.Set;
import java.util.UUID;

import dev.asl.api.config.AslProperties;
import dev.asl.api.run.RunExceptions.BadRequest;
import dev.asl.api.run.RunExceptions.NotFound;
import dev.asl.api.run.dto.EventView;
import dev.asl.api.run.dto.RunDetail;
import dev.asl.api.run.dto.RunSummary;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/runs")
class RunController {

	private static final Set<String> SCENARIOS = RunScenarios.CONDITIONS.keySet();
	private static final Set<String> CONDITIONS = Set.copyOf(RunScenarios.CONDITIONS.get(RunScenarios.SCENARIO));
	private static final Set<String> POPULATIONS = Set.copyOf(RunScenarios.POPULATIONS);
	private static final int MAX_PAGE_SIZE = 100;

	private final RunRepository runs;
	private final AgentRepository agents;
	private final EventRepository events;
	private final AslProperties props;

	RunController(RunRepository runs, AgentRepository agents, EventRepository events, AslProperties props) {
		this.runs = runs;
		this.agents = agents;
		this.events = events;
		this.props = props;
	}

	@GetMapping
	Page<RunSummary> list(@RequestParam(required = false) String scenario, @RequestParam(required = false) String population,
			@RequestParam(required = false) String condition, @RequestParam(defaultValue = "0") int page,
			@RequestParam(defaultValue = "20") int size) {
		if (scenario != null && !SCENARIOS.contains(scenario)) {
			throw new BadRequest("Unknown scenario: " + scenario);
		}
		if (population != null && !POPULATIONS.contains(population)) {
			throw new BadRequest("Unknown population: " + population);
		}
		if (condition != null && !CONDITIONS.contains(condition)) {
			throw new BadRequest("Unknown condition: " + condition);
		}
		if (page < 0 || size < 1) {
			throw new BadRequest("page must be >= 0 and size >= 1");
		}
		PageRequest pr = PageRequest.of(page, Math.min(size, MAX_PAGE_SIZE),
				Sort.by(Sort.Order.desc("createdAt"), Sort.Order.asc("id")));
		return runs.search(scenario, population, condition, pr).map(RunController::summary);
	}

	@GetMapping("/featured")
	List<RunSummary> featured() {
		return props.featuredRunIds().stream().flatMap(id -> runs.findById(id).stream()).map(RunController::summary)
				.toList();
	}

	@GetMapping("/{id}")
	RunDetail get(@PathVariable UUID id) {
		Run r = runs.findById(id).orElseThrow(() -> new NotFound(id));
		return new RunDetail(
				new RunDetail.RunView(r.id, r.experiment, r.scenario, r.condition, r.model, r.seed, r.promptVersion,
						r.startedAt, r.endedAt, r.accuracy, r.ratedCount, r.probeCount, r.recognisedSample),
				agents.findByRunId(id).stream()
						.map(a -> new RunDetail.AgentView(a.agentId, a.name, a.role, a.persona)).toList());
	}

	@GetMapping("/{id}/events")
	List<EventView> events(@PathVariable UUID id) {
		if (!runs.existsById(id)) {
			throw new NotFound(id);
		}
		return events.findByRunIdOrderBySeq(id).stream()
				.map(e -> new EventView(e.seq, e.tick, e.type, e.agentId, e.payload)).toList();
	}

	private static RunSummary summary(Run r) {
		return new RunSummary(r.id, r.scenario, r.condition, r.model, r.seed, r.pilot, r.createdAt, r.accuracy,
				r.ratedCount, r.parseFailures, r.truncations, r.probeCount, r.recognisedSample);
	}
}
