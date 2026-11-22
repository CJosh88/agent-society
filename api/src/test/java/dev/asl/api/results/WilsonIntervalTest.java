package dev.asl.api.results;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class WilsonIntervalTest {

	@Test
	void zeroOfFifty() {
		double[] ci = WilsonInterval.of(0, 50);
		assertThat(ci[0]).isEqualTo(0.0);
		assertThat(ci[1]).isCloseTo(0.0713, within4());
	}

	@Test
	void halfOfFifty() {
		double[] ci = WilsonInterval.of(25, 50);
		assertThat(ci[0]).isCloseTo(0.3664, within4());
		assertThat(ci[1]).isCloseTo(0.6336, within4());
	}

	@Test
	void fiftyOfFifty() {
		double[] ci = WilsonInterval.of(50, 50);
		assertThat(ci[0]).isCloseTo(0.9287, within4());
		assertThat(ci[1]).isEqualTo(1.0);
	}

	@Test
	void rejectsEmptySample() {
		assertThatThrownBy(() -> WilsonInterval.of(0, 0)).isInstanceOf(IllegalArgumentException.class);
	}

	private static org.assertj.core.data.Offset<Double> within4() {
		return org.assertj.core.data.Offset.offset(0.0001);
	}
}
