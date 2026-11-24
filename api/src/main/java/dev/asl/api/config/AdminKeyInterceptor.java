package dev.asl.api.config;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AdminKeyInterceptor implements HandlerInterceptor {

	private static final int MAX_HEADER_CHARS = 256;

	private final byte[] key;

	public AdminKeyInterceptor(AslProperties props) {
		if (props.adminKey() == null || props.adminKey().length() < 32) {
			throw new IllegalStateException("asl.admin-key must be at least 32 characters");
		}
		this.key = props.adminKey().getBytes(StandardCharsets.UTF_8);
	}

	@Override
	public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
		String given = request.getHeader("X-Admin-Key");
		if (given != null && given.length() <= MAX_HEADER_CHARS && MessageDigest.isEqual(key, given.getBytes(StandardCharsets.UTF_8))) {
			return true;
		}
		response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
		return false;
	}
}
