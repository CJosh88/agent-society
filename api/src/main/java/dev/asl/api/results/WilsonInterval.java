package dev.asl.api.results;

/** 95% Wilson score interval for a proportion. */
public final class WilsonInterval {

	static final double Z = 1.959963984540054;

	private WilsonInterval() {
	}

	/** Returns {low, high}. */
	public static double[] of(int successes, int n) {
		if (n <= 0) {
			throw new IllegalArgumentException("n must be positive");
		}
		double p = (double) successes / n;
		double z2 = Z * Z;
		double denom = 1 + z2 / n;
		double centre = (p + z2 / (2.0 * n)) / denom;
		double half = Z * Math.sqrt(p * (1 - p) / n + z2 / (4.0 * n * n)) / denom;
		// The bounds are exactly 0 (no successes) and 1 (all successes); avoid floating-point residue.
		double low = successes == 0 ? 0 : Math.max(0, centre - half);
		double high = successes == n ? 1 : Math.min(1, centre + half);
		return new double[] { low, high };
	}
}
