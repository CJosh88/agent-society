package dev.asl.api.results;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

class NewcombeIntervalTest {

	/** Newcombe (1998), method 10: 56/70 vs 48/80 gives 0.2000 (0.0524, 0.3339). */
	@Test
	void publishedExample() {
		double[] r = NewcombeInterval.difference(56, 70, 48, 80);
		assertThat(r[0]).isCloseTo(0.2, within(1e-9));
		assertThat(r[1]).isCloseTo(0.0524, within(0.001));
		assertThat(r[2]).isCloseTo(0.3339, within(0.001));
	}

	@Test
	void identicalProportionsAreCentredOnZero() {
		double[] r = NewcombeInterval.difference(25, 50, 25, 50);
		assertThat(r[0]).isEqualTo(0.0);
		assertThat(r[1]).isNegative();
		assertThat(r[2]).isPositive();
		assertThat(r[1]).isCloseTo(-r[2], within(1e-9));
	}

	@Test
	void staysWithinMinusOneAndOne() {
		double[] r = NewcombeInterval.difference(50, 50, 0, 50);
		assertThat(r[2]).isLessThanOrEqualTo(1.0);
		assertThat(r[1]).isGreaterThan(0.8);
	}
}
