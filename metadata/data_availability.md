# Data availability statement

The synthetic scenarios, model-visible public/synthetic corpus, rule- and source-validated reference
standard, all 3,000 terminal structured predictions, per-cell five-slot call-seed schedules,
retrieved-object identifiers, the exact offline scorer, all 3,000 structured cell scores, analysis
code, statistical sensitivity inputs, tables, figure source data, and environment/model/container
digests are available in the versioned `v1.0.2` release at
`https://github.com/bigwiz83/medical-cyber-sllm-benchmark`. The article should cite that release tag
and its resolved commit identifier.

No patient, staff, or operational hospital data are included. Upstream model weights and container
layers are not redistributed; their identifiers and digests are supplied for independent
acquisition under upstream terms. Raw transport response bodies, retry histories, intermediate
planner or specialist outputs, and the original inference runner are not distributed. The package
therefore reproduces output-to-score and reported analyses exactly and supports independent
inference-environment reconstruction, but does not claim byte-identical model-call replay.
