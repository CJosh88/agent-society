package dev.asl.api;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import dev.asl.api.config.AdminKeyInterceptor;
import dev.asl.api.config.AslProperties;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class AdminKeyIT {

	@Autowired
	MockMvc mvc;

	private String body() {
		return Fixtures.json(Fixtures.withNewId(Fixtures.town()));
	}

	@Test
	void noKeyIs401() throws Exception {
		mvc.perform(post("/api/admin/runs").contentType(MediaType.APPLICATION_JSON).content(body()))
				.andExpect(status().isUnauthorized());
	}

	@Test
	void wrongKeyIs401() throws Exception {
		mvc.perform(post("/api/admin/runs").header("X-Admin-Key", "not-the-key")
				.contentType(MediaType.APPLICATION_JSON).content(body())).andExpect(status().isUnauthorized());
	}

	@Test
	void pathParameterTrickDoesNotBypass() throws Exception {
		mvc.perform(post("/api/admin;x/runs").contentType(MediaType.APPLICATION_JSON).content(body()))
				.andExpect(status().isUnauthorized());
		mvc.perform(post("/api/admin/runs;x=1").contentType(MediaType.APPLICATION_JSON).content(body()))
				.andExpect(status().isUnauthorized());
	}

	@Test
	void shortKeyFailsStartup() {
		AslProperties props = new AslProperties("too-short", null, "v1", null, null, null);
		assertThatThrownBy(() -> new AdminKeyInterceptor(props)).isInstanceOf(IllegalStateException.class);
	}
}
