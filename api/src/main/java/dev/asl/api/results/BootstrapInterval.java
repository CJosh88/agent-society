package dev.asl.api.results;

import java.util.Arrays;
import java.util.Random;

/** Percentile bootstrap over worlds. A fixed seed keeps the published numbers stable between requests. */
final class BootstrapInterval {

	static final int RESAMPLES = 4000;
	private static final long SEED = 20261123L;

	private BootstrapInterval() {
	}

	/** Returns {mean, low, high} of the 95% interval for the mean of the values. */
	static double[] mean(double[] values) {
		Random rnd = new Random(SEED);
		double[] means = new double[RESAMPLES];
		for (int i = 0; i < RESAMPLES; i++) {
			means[i] = resampleMean(values, rnd);
		}
		return summary(average(values), means);
	}

	/** Returns {difference, low, high} for mean(a) - mean(b), resampling each group on its own. */
	static double[] difference(double[] a, double[] b) {
		Random rnd = new Random(SEED);
		double[] diffs = new double[RESAMPLES];
		for (int i = 0; i < RESAMPLES; i++) {
			diffs[i] = resampleMean(a, rnd) - resampleMean(b, rnd);
		}
		return summary(average(a) - average(b), diffs);
	}

	private static double resampleMean(double[] values, Random rnd) {
		double sum = 0;
		for (int i = 0; i < values.length; i++) {
			sum += values[rnd.nextInt(values.length)];
		}
		return sum / values.length;
	}

	private static double average(double[] values) {
		return Arrays.stream(values).average().orElseThrow();
	}

	private static double[] summary(double point, double[] samples) {
		Arrays.sort(samples);
		return new double[] { point, samples[(int) Math.floor(0.025 * (samples.length - 1))],
				samples[Math.min(samples.length - 1, (int) Math.ceil(0.975 * (samples.length - 1)))] };
	}
}
