package dev.asl.api.results;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/results")
class ResultsController {

	private final ResultsService service;

	ResultsController(ResultsService service) {
		this.service = service;
	}

	@GetMapping
	ResultsResponse get() {
		return service.results();
	}
}
