# Figure assets

`masters/` contains the three reviewed SVG masters. `submission/` contains the corresponding PDF
and 600-dpi PNG derivatives, and `source_data/` contains the numerical CSV inputs used for article
checking. All release masters declare `Arial, Helvetica, sans-serif` and use one consistent visual
system.

`scripts/build_vector_art.mjs` is retained as design provenance for Figures 2 and 3. It uses only
Node.js built-ins and writes to `masters/`, but its rounded display values are embedded in the
script; it is not the statistical source of truth. Figure 1 is the reviewed vector master and has no
code generator in this package. The authoritative numerical outputs are the CSV files in
`source_data/` and `results/`.

Run `python scripts/build_figure_manifest.py` from the repository root after an approved figure
revision. The release-wide manifest independently hashes every master and derivative.

Figure source CSVs are presentation-layer inputs. Figure 3A intentionally omits the retrieval
contrast shown in Figure 3B; its remaining ten contrasts are tested to round-trip through the same
six-decimal/six-significant-digit policy used for article Table 3.
