package dev.asl.api;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import tools.jackson.databind.json.JsonMapper;

/** Loads the shared contract fixtures as mutable maps so tests can break one rule at a time. */
public final class Fixtures {

	public static final String ADMIN_KEY = "dev-admin-key-change-me-00000000";
	private static final JsonMapper MAPPER = JsonMapper.builder().build();

	private Fixtures() {
	}

	@SuppressWarnings("unchecked")
	public static Map<String, Object> load(String name) {
		try {
			return MAPPER.readValue(Files.readString(Path.of("..", "contracts", "fixtures", name)), Map.class);
		}
		catch (IOException e) {
			throw new IllegalStateException(e);
		}
	}

	public static Map<String, Object> weak() {
		return load("bundle-weak-small.json");
	}

	public static Map<String, Object> seededWrong() {
		return load("bundle-seeded-wrong-small.json");
	}

	/** The first event of the given type, so tests do not depend on fixture positions. */
	public static Map<String, Object> event(Map<String, Object> bundle, String type) {
		return events(bundle, type).get(0);
	}

	public static List<Map<String, Object>> events(Map<String, Object> bundle, String type) {
		return list(bundle, "events").stream().filter(e -> type.equals(e.get("type"))).toList();
	}

	public static String json(Object o) {
		return MAPPER.writeValueAsString(o);
	}

	@SuppressWarnings("unchecked")
	public static Map<String, Object> run(Map<String, Object> bundle) {
		return (Map<String, Object>) bundle.get("run");
	}

	@SuppressWarnings("unchecked")
	public static List<Map<String, Object>> list(Map<String, Object> bundle, String key) {
		return (List<Map<String, Object>>) bundle.get(key);
	}

	public static Map<String, Object> withNewId(Map<String, Object> bundle) {
		run(bundle).put("id", UUID.randomUUID().toString());
		return bundle;
	}
}
