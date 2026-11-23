package dev.asl.api;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.forwardedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class StaticPagesIT {

	@Autowired
	MockMvc mvc;

	@Test
	void rootForwardsToTheIndexPage() throws Exception {
		// MockMvc does not follow the welcome-page forward, so check the forward and then the page itself.
		mvc.perform(get("/")).andExpect(status().isOk()).andExpect(forwardedUrl("index.html"));
		mvc.perform(get("/index.html")).andExpect(status().isOk())
				.andExpect(content().string(containsString("Featured worlds")))
				.andExpect(content().string(containsString("js/results.js")));
	}

	@Test
	void replayPageIsServedWithPhaserPinnedExactly() throws Exception {
		mvc.perform(get("/replay.html")).andExpect(status().isOk())
				.andExpect(content().string(containsString("cdn.jsdelivr.net/npm/phaser@3.90.0/dist/phaser.min.js")))
				.andExpect(content().string(containsString("js/replay.js")));
	}

	@Test
	void scriptsStylesAndTicketTextAreServed() throws Exception {
		for (String path : new String[] { "/js/common.js", "/js/results.js", "/js/replay.js", "/css/app.css" }) {
			mvc.perform(get(path)).andExpect(status().isOk());
		}
		mvc.perform(get("/tickets.json")).andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(24))
				.andExpect(jsonPath("$[0].id").value("T01")).andExpect(jsonPath("$[0].truth").doesNotExist());
	}
}
