# Changelog

## R7.0 — Unified Best

- Merged the strongest safeguards from R2, R3, R4, R5 and R6.
- Locked the build to `tplink_wma301` and its exact `mediatek_filogic` device symbol.
- Removed the stale root `.config` design; configuration is regenerated from upstream `mt7981-ax3000.config` on every run.
- Removed project shell-script execution to eliminate executable permission failures from GitHub web uploads.
- Uses workflow artifacts only; no Release job and no `contents: write` permission.
- Adds five fail-closed gates: upstream contract, resolved config, post-build identity, output collection, final checksums/manifest.
- Rejects ASR3000 and sibling WMA301 layouts at config and artifact stages.
- Adds retry handling for feeds and downloads and serial verbose compile fallback.
- Records source repository, branch and exact commit in the artifact.
