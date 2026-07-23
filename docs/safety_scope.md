# Safety scope

All study data are public or synthetic. No patient, staff, or real-hospital information is present.
The evaluation environment enforced these boundaries:

- local digest-pinned models only;
- zero runtime external transfer;
- no host networking, privileged container, or Docker socket mount;
- read-only model and benchmark mounts where applicable;
- no evaluator-only file mounted into inference;
- no execution of model-authored commands;
- no active scanning, exploit execution, persistence, or privilege escalation.

The release verifier scans for high-confidence credential patterns, machine-specific absolute paths,
excluded operational-history path names, oversized files, symlinks, and reader-facing nomenclature
that is outside the public article vocabulary.

