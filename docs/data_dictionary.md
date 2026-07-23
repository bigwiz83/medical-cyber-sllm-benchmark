# Data dictionary

## `data/predictions/final_predictions.jsonl`

Each line is one terminal evaluation-cell record validated by
`schemas/final_prediction.schema.json`.

| Field | Meaning |
|---|---|
| `schema_version` | Public prediction contract version |
| `condition_id` | Stable public identifier from `configs/conditions.json` |
| `blind_case_id` | Opaque model-visible case identifier |
| `run_index` | Technical repetition index, 1 through 5 |
| `run_status` | `complete`, `failed`, or `refusal` |
| `call_seed_schedule` | Ordered, frozen seed values for call slots 1 through 5 |
| `retrieved_object_ids` | Exact corpus-object identifiers exposed to that cell |
| `final_output` | Validated terminal envelope; null only for a failed cell |

The terminal envelope preserves structured findings, applicability statements, and cited opaque
evidence identifiers. It excludes generation transcripts, intermediate outputs, retry histories,
and transport bodies. All model-authored text is inert data and is never executed by the scorer.

## `data/derived/integrated_cell_scores.csv`

| Field | Meaning |
|---|---|
| `condition_id` | Stable public identifier from `configs/conditions.json` |
| `condition` | Reader-facing condition label |
| `backbone` | Local model family/profile |
| `blind_case_id` | Opaque model-visible case identifier |
| `scenario_id` | Stable scenario identifier |
| `family_id` | Matched scenario-family identifier |
| `stratum` | Prespecified allocation stratum |
| `run_index` | Technical repetition index, 1 through 5 |
| `run_status` | `complete`, `failed`, or `refusal` |
| `positive_reference_count` | Number of positive reference items in the scenario |
| `tp_ev` | Evidence-verified true positives |
| `fp` | False positives, including unsupported positive assertions |
| `fn` | Missed positive reference items |
The JSON Lines version contains the same fields and values.

`scripts/score_predictions.py --check` reconstructs these 3,000 score rows from the final
predictions and reference bundle and requires exact equality with the released JSON Lines matrix.

## Result files

- `condition_summary.csv`: terminal counts, pooled counts, precision, recall, mean-run F1, and
  pooled-count F1 by condition.
- `article_comparisons.csv`: point differences, intervals, raw and adjusted p values, and analysis
  status for the article comparisons.
- `subgroup_results.csv`: pooled counts and metrics by condition and scenario stratum.
- `retrieval_window_recall.csv`: affected-target recall by recency window for retained versus withheld
  retrieval.
- `resource_use.csv`: recorded attempts, token counts, latency, transfer, and command-execution totals.

`resource_use.csv` is a frozen aggregate bound by the release manifest; cell-level attempt and token
records are not distributed, so these totals are not independently reconstructed from
`integrated_cell_scores.csv`. `model_attempts` counts backend generation attempts, including
schema/transport repair attempts where recorded, rather than only the 1,500 scheduled calls per
condition. `retries` is the recorded excess-attempt count; `NE` means that this field was not
estimable from that execution harness and must not be read as zero. Tests require Supplementary
Table S3 to match the frozen aggregate byte for byte.

An empty metric field means not estimable; it is not zero. Counts are integers. F1 estimates and
probabilities are represented as decimal floating-point values.
