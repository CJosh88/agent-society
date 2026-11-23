package dev.asl.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class OpenApiExportIT {

	@Autowired
	MockMvc mvc;

	@Test
	void writesOpenApiYaml() throws Exception {
		String yaml = mvc.perform(get("/v3/api-docs.yaml")).andExpect(status().isOk()).andReturn().getResponse()
				.getContentAsString();
		assertThat(yaml).contains("/api/runs").contains("/api/results").contains("/api/admin/runs");
		Files.writeString(Path.of("..", "contracts", "openapi.yaml"), yaml);
	}
}
