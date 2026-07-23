# Medical Cybersecurity sLLM Benchmark

This repository is the reproducibility package for a local-language-model cybersecurity study in a
fully synthetic hospital network. Ten configurations were evaluated on the same 60 scenarios, with
five technical repetitions per configuration: **3,000 evaluation cells** in total.

The primary outcome is evidence-verified detection micro-F1. A positive prediction counts only when
the target and finding are correct and the required evidence supports the assertion. Failed and
refused cells remain in the full analysis set.

## What is included

- model-visible synthetic scenario inputs and the frozen public/synthetic retrieval corpus;
- the rule-, source-, and execution-validated reference standard and validation records;
- all 3,000 terminal prediction records and per-cell retrieved-object sets using public condition
  identifiers;
- the frozen five-call seed schedule for every cell and the deterministic offline scorer;
- all 3,000 structured cell scores using public condition names;
- model and container digests, execution settings, and the complete scored-cell matrix;
- deterministic aggregation, paired bootstrap, p-value, and multiplicity code;
- the numerical source data and vector masters for the three article figures and three tables;
- a content-addressed manifest and release-safety verifier.

Raw generation transcripts, model weights, container layers, credentials, operational targets, and
real-world hospital data are not included.

## Main inventory

| Item | Count |
|---|---:|
| Configurations | 10 |
| Scenarios | 60 |
| Independent matched families | 30 |
| Technical repetitions | 5 |
| Evaluation cells | 3,000 |
| Complete / failed / refused cells | 2,759 / 236 / 5 |

## Reproduce the article analysis

The executed analysis environment used Python 3.12.3. Exact Python package versions are pinned in
`requirements-lock.txt`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python scripts/verify_release.py
python scripts/score_predictions.py --check
python scripts/reproduce_analysis.py --check
python scripts/build_publication_tables.py --check
python scripts/reproduce_mixed_effects.py --check
python -m pytest -p no:cacheprovider
```

To write a fresh set of derived tables:

```bash
python scripts/reproduce_analysis.py --output build/reproduced
```

The `--check` form recomputes results in memory and compares them with the locked CSV files without
changing the repository. See `docs/reproducibility.md` for the complete sequence and expected values.

## Experimental replay boundary

`configs/models.lock.json`, `configs/runtime.lock.json`, and `configs/conditions.json` identify the
executed local models and schedules. The inference environment used a digest-pinned Ollama container,
GPU execution, concurrency 1, temperature 0, and no runtime network access. Model acquisition is a
separate, user-initiated step governed by each upstream license. The included benchmark inputs can be
mounted read-only into an independently implemented runner; this repository never scans a target and
contains no exploit execution path. The released final prediction envelopes and five-call schedules
reproduce the frozen 3,000-cell score matrix exactly against the released reference standard. The
remaining inference materials support environment and contract reconstruction, not byte-for-byte
model-call replay; model weights, generation transcripts, and the original runner are not
distributed.

## Results at a glance

Qwen single-RAG achieved mean-run F1 0.63, the Qwen autonomous team 0.62, and the Qwen fixed team
0.60. The autonomous-minus-fixed difference was 0.01 (95% CI -0.12 to 0.14; two-sided p=0.880).
Withholding retrieval reduced recall on affected recent-KEV targets from 0.75 to 0.00; the
retained-minus-withheld difference was 0.75 (95% CI 0.50 to 0.92; Holm-adjusted p<0.001). See
`results/` for full-precision condition, subgroup, and comparison tables.

## Data and code availability

The versioned public home for this package is
https://github.com/bigwiz83/medical-cyber-sllm-benchmark. Cite the `v1.0.2` release and its resolved
commit identifier with the associated article. No patient, staff, or real-hospital data were used.

## Publication gate

The responsible author approved Apache-2.0 for code and CC BY 4.0 for study-authored synthetic and
derived data and documentation. Source-specific third-party terms remain controlling. Run
`python scripts/verify_release.py --publication` before publishing or archiving a release.
