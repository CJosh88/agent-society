package dev.asl.api.run;

import java.util.Map;
import java.util.UUID;

import dev.asl.api.run.dto.RunBundle;

import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin")
class AdminIngestController {

	private final RunIngestService ingest;

	AdminIngestController(RunIngestService ingest) {
		this.ingest = ingest;
	}

	@PostMapping("/runs")
	@ResponseStatus(HttpStatus.CREATED)
	Map<String, UUID> post(@Valid @RequestBody RunBundle bundle) {
		return Map.of("id", ingest.ingest(bundle));
	}
}
