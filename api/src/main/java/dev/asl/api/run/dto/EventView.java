package dev.asl.api.run.dto;

import java.util.Map;

public record EventView(int seq, int tick, String type, String agentId, Map<String, Object> payload) {
}
