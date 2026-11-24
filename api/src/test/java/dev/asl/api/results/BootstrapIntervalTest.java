package dev.asl.api.results;

import static org.assertj.core.api.Assertions.assertThat;

import org.assertj.core.data.Offset;
import org.junit.jupiter.api.Test;

class BootstrapIntervalTest {

	@Test
	void constantValuesGiveAPointInterval() {
		double[] ci = BootstrapInterval.mean(new double[] { 0.5, 0.5, 0.5, 0.5 });
		assertThat(ci).containsExactly(0.5, 0.5, 0.5);
	}

	@Test
	void intervalBracketsTheMeanAndStaysInsideTheRange() {
		double[] ci = BootstrapInterval.mean(new double[] { 0.6, 0.7, 0.8, 0.9, 0.65, 0.75, 0.85, 0.7 });
		assertThat(ci[0]).isEqualTo(0.74375, Offset.offset(1e-12));
		assertThat(ci[1]).isLessThan(ci[0]);
		assertThat(ci[2]).isGreaterThan(ci[0]);
		assertThat(ci[1]).isGreaterThan(0.6);
		assertThat(ci[2]).isLessThan(0.9);
	}

	@Test
	void sameInputGivesTheSameInterval() {
		double[] v = { 0.2, 0.4, 0.9, 0.5 };
		assertThat(BootstrapInterval.mean(v)).containsExactly(BootstrapInterval.mean(v));
	}

	@Test
	void differenceOfSeparatedGroupsExcludesZero() {
		double[] ci = BootstrapInterval.difference(new double[] { 0.5, 0.55, 0.6, 0.52 },
				new double[] { 0.8, 0.85, 0.9, 0.82 });
		assertThat(ci[0]).isLessThan(0);
		assertThat(ci[2]).isLessThan(0);
	}
}
