package dev.asl.api.web;

import dev.asl.api.run.RunExceptions.AlreadyExists;
import dev.asl.api.run.RunExceptions.BadRequest;
import dev.asl.api.run.RunExceptions.NotFound;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

/** RFC 9457 problem details for 400, 404 and 409. */
@RestControllerAdvice
class ApiExceptionHandler {

	@ExceptionHandler(BadRequest.class)
	ProblemDetail badRequest(BadRequest e) {
		return problem(HttpStatus.BAD_REQUEST, e.getMessage());
	}

	@ExceptionHandler(MethodArgumentNotValidException.class)
	ProblemDetail invalid(MethodArgumentNotValidException e) {
		String detail = e.getBindingResult().getFieldErrors().stream()
				.map(f -> f.getField() + " " + f.getDefaultMessage()).limit(5).reduce((a, b) -> a + "; " + b)
				.orElse("Validation failed");
		return problem(HttpStatus.BAD_REQUEST, detail);
	}

	@ExceptionHandler(HttpMessageNotReadableException.class)
	ProblemDetail unreadable(HttpMessageNotReadableException e) {
		return problem(HttpStatus.BAD_REQUEST, "Request body is not a valid RunBundle");
	}

	@ExceptionHandler(MethodArgumentTypeMismatchException.class)
	ProblemDetail typeMismatch(MethodArgumentTypeMismatchException e) {
		return problem(HttpStatus.BAD_REQUEST, "Invalid value for parameter " + e.getName());
	}

	@ExceptionHandler(NotFound.class)
	ProblemDetail notFound(NotFound e) {
		return problem(HttpStatus.NOT_FOUND, e.getMessage());
	}

	@ExceptionHandler({ AlreadyExists.class, DataIntegrityViolationException.class })
	ProblemDetail conflict(Exception e) {
		return problem(HttpStatus.CONFLICT, e instanceof AlreadyExists ? e.getMessage() : "Conflicting data");
	}

	private static ProblemDetail problem(HttpStatus status, String detail) {
		return ProblemDetail.forStatusAndDetail(status, detail);
	}
}
