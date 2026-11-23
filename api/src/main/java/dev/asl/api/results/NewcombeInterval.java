package dev.asl.api.results;

/** 95% Newcombe hybrid-score interval for a difference of two independent proportions (method 10). */
public final class NewcombeInterval {

	private NewcombeInterval() {
	}

	/** Difference p1 - p2 as {diff, low, high}. */
	public static double[] difference(int x1, int n1, int x2, int n2) {
		double p1 = (double) x1 / n1;
		double p2 = (double) x2 / n2;
		double[] w1 = WilsonInterval.of(x1, n1);
		double[] w2 = WilsonInterval.of(x2, n2);
		double d = p1 - p2;
		double low = d - Math.sqrt(Math.pow(p1 - w1[0], 2) + Math.pow(w2[1] - p2, 2));
		double high = d + Math.sqrt(Math.pow(w1[1] - p1, 2) + Math.pow(p2 - w2[0], 2));
		return new double[] { d, Math.max(-1, low), Math.min(1, high) };
	}
}
