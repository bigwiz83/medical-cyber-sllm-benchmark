# Article tables

- `table1a_scenario_composition.csv` summarizes scenario strata and pair structure.
- `table1b_model_configurations.csv` summarizes the ten evaluated model configurations.
- `table2_performance.csv` reports condition-level detection and terminal-status results.
- `table3_comparisons.csv` reports the prespecified comparison estimates.

The canonical full-precision values are retained under `results/`. Table 3 is a deterministic
publication projection with effects and confidence limits rounded to six decimal places and
p-values to six significant digits. Run `python scripts/build_publication_tables.py --check` to
verify that the presentation layer has not diverged from the machine result.
