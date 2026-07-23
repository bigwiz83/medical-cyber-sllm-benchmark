# Machine-readable results

`statistical_results.json` and `article_comparisons.csv` retain the deterministic floating-point
values emitted by the analysis implementation. They are the canonical numerical outputs used for
machine comparison and are not publication-rounded.

The corresponding article display is `tables/table3_comparisons.csv`. It is rebuilt by
`scripts/build_publication_tables.py`: effects and confidence limits use six decimal places, while
p-values use six significant digits to avoid rounding small values to zero. Both layers are tested
independently so display formatting cannot silently replace the full-precision result.
