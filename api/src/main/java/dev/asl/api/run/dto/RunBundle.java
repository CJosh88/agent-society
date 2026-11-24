package dev.asl.api.run.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

/** The bundle the engine POSTs. Snake_case on the wire, per contracts/run-bundle.schema.json. */
public record RunBundle(
		@JsonProperty("run") @NotNull @Valid RunInfo run,
		@JsonProperty("agents") @NotEmpty List<@NotNull @Valid AgentInfo> agents,
		@JsonProperty("events") @NotEmpty List<@NotNull @Valid EventInfo> events,
		@JsonProperty("llm_calls") @NotNull List<@NotNull @Valid LlmCallInfo> llmCalls) {

	/** a1 to a200: the number is the agent's position in the line. */
	static final String AGENT_ID = "a([1-9][0-9]?|1[0-9]{2}|200)";

	public record RunInfo(
			@JsonProperty("id") @NotNull UUID id,
			@JsonProperty("experiment") @NotNull @Pattern(regexp = "cascade_v1") String experiment,
			@JsonProperty("scenario") @NotNull @Pattern(regexp = "triage_cascade") String scenario,
			@JsonProperty("condition") @NotNull @Pattern(regexp = "independent|weak|strong|seeded_wrong") String condition,
			@JsonProperty("population") @NotNull @Pattern(regexp = "llama-3[.]1-8b|gpt-oss-120b|claude-haiku-5-5|mix_early|mix_late|fake") String population,
			@JsonProperty("world_seed") @NotNull @Min(0) Long worldSeed,
			@JsonProperty("prompt_version") @NotBlank String promptVersion,
			@JsonProperty("engine_version") @NotBlank String engineVersion,
			@JsonProperty("pilot") @NotNull Boolean pilot,
			@JsonProperty("started_at") @NotNull Instant startedAt,
			@JsonProperty("ended_at") @NotNull Instant endedAt) {
	}

	public record AgentInfo(
			@JsonProperty("agent_id") @NotNull @Pattern(regexp = AGENT_ID) String agentId,
			@JsonProperty("name") @NotBlank String name,
			@JsonProperty("role") @NotNull @Pattern(regexp = "agent|scripted") String role,
			@JsonProperty("persona") @NotNull Map<String, Object> persona) {
	}

	public record EventInfo(
			@JsonProperty("seq") @NotNull @Min(0) Integer seq,
			@JsonProperty("tick") @NotNull @Min(1) @Max(200) Integer tick,
			@JsonProperty("type") @NotNull @Pattern(regexp = "AGENT_SPAWNED|TICKETS_SHOWN|AGENT_PICKED|AGENT_RATED|ACTION_PARSE_FAILED|PROBE_ANSWERED|RUN_ENDED") String type,
			@JsonProperty("agent_id") @Pattern(regexp = AGENT_ID) String agentId,
			@JsonProperty("payload") @NotNull Map<String, Object> payload) {
	}

	public record LlmCallInfo(
			@JsonProperty("agent_id") @NotNull @Pattern(regexp = AGENT_ID) String agentId,
			@JsonProperty("tick") @NotNull @Min(1) @Max(200) Integer tick,
			@JsonProperty("kind") @NotNull @Pattern(regexp = "decision|probe") String kind,
			@JsonProperty("attempt") @NotNull @Min(1) @Max(2) Integer attempt,
			@JsonProperty("prompt") @NotNull String prompt,
			@JsonProperty("response_text") @NotNull String responseText,
			@JsonProperty("reasoning_text") String reasoningText,
			@JsonProperty("finish_reason") String finishReason,
			@JsonProperty("input_tokens") @Min(0) Integer inputTokens,
			@JsonProperty("output_tokens") @Min(0) Integer outputTokens,
			@JsonProperty("tokens_estimated") @NotNull Boolean tokensEstimated,
			@JsonProperty("parsed_ok") @NotNull Boolean parsedOk,
			@JsonProperty("latency_ms") @NotNull @Min(0) Integer latencyMs) {
	}
}
