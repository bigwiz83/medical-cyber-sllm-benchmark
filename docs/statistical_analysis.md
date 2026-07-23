# Statistical analysis

## Endpoint

Evidence-verified detection micro-F1 is calculated as

`2 * TP / (2 * TP + FP + FN)`.

For each condition, the inferential estimate is the arithmetic mean of the five run-specific
micro-F1 values. Pooled TP, FP, FN, precision, recall, and pooled-count F1 are also reported. Precision
is left not estimable when a condition emits no positive prediction.

## Paired inference

Differences use 10,000 synchronized, stratum-preserving two-way bootstrap draws. Within each draw,
families are resampled with replacement inside each of the six allocation strata, and five global
repetition indices are sampled with replacement. The same draw is applied to both members of a
comparison. Percentile 95% confidence intervals use linear quantiles.

The main fixed-team and ablation/backbone comparisons use seed 2026071901. The bounded autonomous
comparisons use seed 2026072201. Two-sided centered-bootstrap p values use the finite-resample
plus-one rule. Evidence-checking and retrieval comparisons form one two-test Holm family; the two
Qwen-versus-other-backbone fixed-team comparisons form a separate two-test Holm family.

The retrieval comparison uses evidence-verified recall on the 12 affected recent-KEV targets and
stratifies over the three recency windows. The clinical-context-agent comparison is descriptive. The minimum
within-backbone fixed-team effect is computed draw by draw across Qwen, Gemma, and gpt-oss.

## Exact implementation

`src/medcyber_benchmark/analysis.py` contains the estimator. It reads only the released cell score
file, checks the complete paired matrix, and deterministically reconstructs `results/`. Tests assert
the primary point estimates, intervals, p values, multiplicity values, and status totals.

## Explanatory mixed-model sensitivity analysis

Supplementary model-sensitivity results use the 25 positive reference targets. The binary model is

`verified_detected ~ C(condition) + C(finding_type) + recent_kev + C(repetition) + C(condition):recent_kev`

with a scenario-family random intercept. The first-line estimator is statsmodels 0.14.6
`BinomialBayesMixedGLM` Laplace MAP with `vcp_p=0.5`, `fe_p=10`, BFGS followed by L-BFGS-B,
`maxiter=1000`, and `scale_fe=False`. The prespecified fallback is a binomial GEE with
scenario-family clusters, exchangeable working correlation, robust covariance, and 200 iterations.
All three released comparisons selected the first-line BFGS fit.

Marginal probability differences use empirical-row counterfactual standardization. The fixed-effect
covariance is symmetrized and negative eigenvalues are clipped to zero before 5,000 multivariate
normal draws with seed 2026071901; interval endpoints are the 2.5th and 97.5th percentiles.
`src/medcyber_benchmark/mixed_effects.py` contains the frozen sequence, and
`scripts/reproduce_mixed_effects.py --check` binds the archived expected reports to the published
table at absolute tolerance 1e-12, then refits all three comparisons and checks the published values
at absolute tolerance 0.002. The wider refit tolerance reflects platform-level optimization and
simulation variation; the archived expected reports preserve the original estimates exactly.
