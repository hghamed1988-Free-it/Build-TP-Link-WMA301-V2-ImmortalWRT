# Verification Report — R3

Date: 2026-08-18

## Verified against the current source contract

The R3 validators were exercised against freshly retrieved files from branch `openwrt-24.10-6.6`:

- `target/linux/mediatek/Makefile`
- `target/linux/mediatek/image/filogic.mk`
- `defconfig/mt7981-ax3000.config`

Observed contract:

- MediaTek declares `filogic` in `SUBTARGETS`.
- The canonical MT7981 defconfig uses `CONFIG_TARGET_mediatek_mt7981=y` as a source meta-target.
- Per-device selections use `CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_*`.
- WMA301 definitions present: `tplink_wma301`, `tplink_wma301-stock`, `tplink_wma301-ubootmod`.
- `tplink_wma301-ubootmod` declares `sysupgrade.itb`, `preloader.bin`, `bl31-uboot.fip` and the MT7981 DDR3 preloader contract.

## Local tests passed

- Project self-check.
- Python syntax compilation for all validators/generators.
- Bash syntax for local scripts.
- YAML parse of `.github/workflows/build.yml`.
- Bash syntax validation of every workflow `run:` block.
- Positive source-contract checks for all three WMA301 profiles.
- Source-derived config generation for all three profiles.
- Exact single-device config validation.
- Negative rejection of ABT ASR3000.
- Firmware collector checksum positive test.
- Negative rejection of an ASR3000-contaminated output directory.
- Negative rejection of a changed ubootmod bootloader contract.

## Scope limitation

A complete ImmortalWrt toolchain/firmware compilation was not executed in this local environment. The GitHub Actions workflow performs the full clone, feeds update/install, `make defconfig`, source download, compilation, post-build target validation, upstream checksum verification, artifact generation, and optional release publication.
