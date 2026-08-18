# R7 verification report

R7 was assembled from the strongest parts of R2–R6 and then re-tested as a standalone project.

Local verification performed before packaging:

- project self-check: PASS
- Python syntax compilation for all validators: PASS
- upstream-contract fixture test: PASS
- exact single-device config generation: PASS
- positive resolved-config validation: PASS
- negative ASR3000 config rejection: PASS
- positive artifact checksum/metadata collection: PASS
- negative ASR3000 artifact rejection: PASS
- final artifact identity/SHA-256 gate: PASS
- GitHub workflow YAML parse: PASS
- forbidden legacy workflow-pattern scan: PASS

The local tests validate project logic and fail-closed behavior. They are not a substitute for a full ImmortalWrt compilation on GitHub Actions; the workflow performs that compilation and re-runs the identity gates around it.
