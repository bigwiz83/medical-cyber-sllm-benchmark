# Supplementary tables

- `table_s1_stratum_metrics.csv` reports condition performance by scenario stratum.
- `table_s2_model_sensitivity.csv` reports the three Qwen explanatory mixed-model comparisons.
- `table_s3_resource_use.csv` reports observed call, token, latency, and failure totals.

The first and third tables are bound to the released score/resource files. The second is bound to
the archived expected reports under `data/mixed_effects/` and can be refitted with
`scripts/reproduce_mixed_effects.py --check` using the tolerance specified in
`docs/statistical_analysis.md`.
