# Study design

## Objective

The study tests whether local language-model organization changes evidence-verified cybersecurity
detection on a fixed synthetic hospital-network benchmark. The comparison isolates single-model
self-consistency, a fixed specialist team, bounded model-planned roles, functional ablations, and
matched team structures across three backbones.

## Evaluation matrix

Each of 10 executed configurations was applied to every one of 60 scenarios at five technical
repetition indices. This produces 300 cells per configuration and 3,000 cells overall. Thirty matched
families are the independent inferential units; repetition indices are technical repeats and are not
treated as independent scenarios.

The scenario allocation is:

| Stratum | Families | Scenarios |
|---|---:|---:|
| Recent KEV, 0-30 days | 4 | 8 |
| Recent KEV, 31-60 days | 4 | 8 |
| Recent KEV, 61-90 days | 4 | 8 |
| Other CVE | 6 | 12 |
| Synthetic misconfiguration | 7 | 14 |
| Clean control | 5 | 10 |

Vulnerability and configuration families use a positive case paired with a single-fact near-miss.
Clean families contain two negative controls. Several families include study-authored private
synthetic paths to reduce the usefulness of simple training-data recall.

## Full analysis set

Every scheduled cell is retained. A failed or refused cell contributes no true positives, preserves
its false-negative burden, and retains any scoreable false positive. The endpoint is therefore not
conditioned on successful model completion.

## Executed configurations

The public condition registry is `configs/conditions.json`. It contains exactly the ten conditions
present in `data/derived/integrated_cell_scores.csv`; no unevaluated configuration is represented.

