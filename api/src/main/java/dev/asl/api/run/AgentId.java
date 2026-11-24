package dev.asl.api.run;

import java.io.Serializable;
import java.util.UUID;

record AgentId(UUID runId, String agentId) implements Serializable {
}
