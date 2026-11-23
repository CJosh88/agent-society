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

	public record RunInfo(
			@JsonProperty("id") @NotNull UUID id,
			@JsonProperty("experiment") @NotNull @Pattern(regexp = "agent_society_v2") String experiment,
			@JsonProperty("scenario") @NotNull @Pattern(regexp = "alert_fatigue|triage_herding") String scenario,
			@JsonProperty("condition") @NotNull @Pattern(regexp = "calm|fatigue_3|fatigue_6|alone|dismiss|endorse") String condition,
			@JsonProperty("model") @NotBlank String model,
			@JsonProperty("seed") @NotNull @Min(0) Long seed,
			@JsonProperty("prompt_version") @NotBlank String promptVersion,
			@JsonProperty("engine_version") @NotBlank String engineVersion,
			@JsonProperty("pilot") @NotNull Boolean pilot,
			@JsonProperty("started_at") @NotNull Instant startedAt,
			@JsonProperty("ended_at") @NotNull Instant endedAt) {
	}

	public record AgentInfo(
			@JsonProperty("agent_id") @NotBlank String agentId,
			@JsonProperty("name") @NotBlank String name,
			@JsonProperty("role") @NotNull @Pattern(regexp = "focal|scripted") String role,
			@JsonProperty("persona") @NotNull Map<String, Object> persona) {
	}

	public record EventInfo(
			@JsonProperty("seq") @NotNull @Min(0) Integer seq,
			@JsonProperty("tick") @NotNull @Min(0) @Max(12) Integer tick,
			@JsonProperty("type") @NotNull @Pattern(regexp = "AGENT_SPAWNED|NOTICE_SHOWN|AGENT_SAID|AGENT_WAITED|AGENT_CALLED|AGENT_PRIORITY_SET|ACTION_PARSE_FAILED|PROBE_ANSWERED|RUN_ENDED") String type,
			@JsonProperty("agent_id") String agentId,
			@JsonProperty("payload") @NotNull Map<String, Object> payload) {
	}

	public record LlmCallInfo(
			@JsonProperty("agent_id") @NotBlank String agentId,
			@JsonProperty("tick") @NotNull @Min(0) @Max(12) Integer tick,
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
