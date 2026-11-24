package dev.asl.api.run;

import java.util.UUID;

/** Namespace for the run-related exceptions mapped to problem details in ApiExceptionHandler. */
public final class RunExceptions {

	private RunExceptions() {
	}

	/** 400: a semantic or parameter rule failed. */
	public static class BadRequest extends RuntimeException {
		public BadRequest(String message) {
			super(message);
		}
	}

	/** 404 */
	public static class NotFound extends RuntimeException {
		public NotFound(UUID id) {
			super("Run not found: " + id);
		}
	}

	/** 409 */
	public static class AlreadyExists extends RuntimeException {
		public AlreadyExists(UUID id) {
			super("Run already exists: " + id);
		}
	}
}
