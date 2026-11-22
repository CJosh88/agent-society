package dev.asl.api.run;

import java.util.UUID;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "llm_calls")
class LlmCall {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	Long id;
	UUID runId;
	String agentId;
	int tick;
	String kind;
	int attempt;
	String prompt;
	String responseText;
	String reasoningText;
	String finishReason;
	Integer inputTokens;
	Integer outputTokens;
	boolean tokensEstimated;
	boolean parsedOk;
	int latencyMs;
}
