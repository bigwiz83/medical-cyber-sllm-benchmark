# Reproducibility guide

## Level 1: integrity and analysis

This level requires Python 3.12.3 and the pinned dependencies in `requirements-lock.txt`.

```bash
python scripts/verify_release.py
python scripts/score_predictions.py --check
python scripts/reproduce_analysis.py --check
python scripts/build_publication_tables.py --check
python scripts/reproduce_mixed_effects.py --check
python -m pytest -p no:cacheprovider
```

Expected inventory assertions are 3,000 unique cells, 10 conditions, 60 scenarios, 30 families,
five repetition indices, and exactly 300 cells per condition. Expected terminal totals are 2,759
complete, 236 failed, and 5 refused.

## Level 2: output-to-score and table reconstruction

`score_predictions.py` validates the 3,000 public prediction records, resolves only allowlisted
paths in the public benchmark projection, verifies cited evidence hashes and JSON Pointers, and
requires exact field and byte equality with the released scored-cell matrix.

```bash
python scripts/score_predictions.py --output build/rescored_cells.jsonl
```

Then reconstruct the article analysis:

```bash
python scripts/reproduce_analysis.py --output build/reproduced
```

Compare the generated CSV files with `results/`. Floating-point comparisons in the verifier use a
strict absolute tolerance of 1e-12 for full-precision outputs and the published precision for rounded
article rows.

## Level 3: local inference-environment reconstruction

Model weights are not distributed. Acquire the exact upstream models only after accepting their
terms, verify every manifest digest in `configs/models.lock.json`, and use the digest-pinned container
in `configs/runtime.lock.json`. Mount `data/benchmark/model_visible/` read-only, disable runtime
network access, set concurrency to 1, and preserve the five-call schedule and failure policy in
`configs/conditions.json`.

An independent implementation should write structured outputs first and run its scorer offline
against the separate evaluator-only bundle. Never mount evaluator-only files into an inference
container. The repository provides the frozen five-call schedule, terminal structured predictions,
the exact offline scorer, the scored-cell matrix, and analysis code. Generation transcripts, model
weights, and the original runner are not distributed, so this level does not claim byte-identical
inference replay. The release intentionally does not include a network or target-scanning interface.

## Versioning

Use a repository tag and commit identifier when citing results. `metadata/release_manifest.json`
hashes every distributed file other than itself. Any content change requires a new manifest and a new
release version; published artifacts should not be overwritten.
