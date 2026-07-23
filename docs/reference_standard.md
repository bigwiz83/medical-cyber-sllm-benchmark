# Reference standard

The reference standard is deterministic and does not use opinion labels. It combines:

1. explicit applicability rules for product, version, component, configuration, and reachability;
2. frozen public CVE and Known Exploited Vulnerabilities source material;
3. study-authored synthetic policies and asset facts; and
4. execution-validation records for each scenario and candidate universe.

A scored true positive requires the correct asset/finding identity and satisfaction of the required
evidence groups. A positive assertion without supporting evidence is a false positive. A supported
reference item not recovered by the model is a false negative.

The released offline scorer validates every terminal prediction envelope, maps opaque case IDs only
inside the evaluator boundary, re-resolves cited evidence through hash-bound model-visible files,
and verifies the frozen JSON Pointer selections. It then applies deterministic one-to-one matching
between eligible positive assertions and positive reference items. An optional source-schema
`verification_status` field is preserved only when it was explicitly present; no default label is
inserted. Eligibility and evidence verification are determined by the scorer itself. Failed and
refused cells retain their prespecified full-analysis-set contribution without salvaging
intermediate output.

For corpus citations, every cited `obj_*` identifier must occur in that cell's preserved
`retrieved_object_ids`; the without-retrieval condition requires an empty set. Scenario-input
`art_*` identifiers are checked separately against the hash-bound model-visible case bundle.

The public reference bundle is under `data/benchmark/evaluator_only/`. Model-visible inputs are
separated at `data/benchmark/model_visible/`. Provenance paths embedded in the reference JSON retain
the original source-tree prefix. `scripts/verify_release.py` resolves those entries to the released
tree and verifies the recorded object hashes. The public projection omits non-analytic null
annotation fields while preserving labels, evidence, decision rules, validation records, and linked
hashes.

Public vulnerability metadata is time-frozen. The Known Exploited Vulnerabilities snapshot was
retrieved on 18 July 2026; the reference source manifest records the exact retrieval timestamps and
SHA-256 values used by the study.

Run `python scripts/score_predictions.py --check` to verify that the terminal prediction file
reconstructs all 3,000 released TP, FP, FN, and status rows exactly.
