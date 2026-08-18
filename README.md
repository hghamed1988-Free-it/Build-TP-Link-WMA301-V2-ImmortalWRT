# TP-Link WMA301 V2 ImmortalWrt — Unified Verified R7

This package consolidates the strongest parts of the earlier R2–R6 iterations into one fail-closed GitHub Actions build project.

## What R7 keeps from the previous revisions

- R3: source-derived configuration, modular validators, checksum-aware collection, tests and documentation.
- R4: workflow-only publication and no GitHub Release permission requirement.
- R5: exact per-device symbol `CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_tplink_wma301=y`.
- R6: fail-closed gates, source contract validation, retries, strict artifact identity, upstream checksum verification and build provenance.
- R7 improvement: no external project `.sh` script is executed, eliminating the executable-bit/`Permission denied` problem seen after web uploads.

## Exact target

R7 is intentionally locked to the base upstream profile only:

- Vendor: `TP-Link`
- Model: `WMA301`
- Profile: `tplink_wma301`
- DTS: `mt7981b-tplink-wma301`
- Target: `mediatek/filogic`
- Device Kconfig symbol: `CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_tplink_wma301=y`

It does **not** build `abt_asr3000`, `tplink_wma301-stock`, or `tplink_wma301-ubootmod`.

## Source

- Repository: `https://github.com/padavanonly/immortalwrt-mt798x-6.6.git`
- Branch: `openwrt-24.10-6.6`
- Canonical MT7981 base config: `defconfig/mt7981-ax3000.config`

The workflow records the resolved source commit in the artifact.

## Run

1. Put `.github/workflows/build.yml` in the repository root hierarchy.
2. Open **Actions** → **Build TP-Link WMA301 V2 ImmortalWrt - Unified Verified R7**.
3. Click **Run workflow**.
4. Keep `include_initramfs=true` for the first verification build.
5. Download the artifact after every gate is green.

## Important flashing note

The upstream source identifies the profile as **WMA301**; it does not encode the physical hardware label `V2` in the profile name. R7 can prove that the generated firmware is for the upstream `tplink_wma301` profile, but it cannot prove the flash layout of a physical router without checking that router. Review `FLASH-SAFETY.md` before flashing.
