#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$ROOT/scripts/self-check.py"
bash -n "$ROOT/scripts/validate-config.sh"
bash -n "$ROOT/scripts/build-local.sh"
python3 -m py_compile \
  "$ROOT/scripts/self-check.py" \
  "$ROOT/scripts/prepare-config.py" \
  "$ROOT/scripts/verify-source.py" \
  "$ROOT/scripts/collect-firmware.py"

for p in tplink_wma301 tplink_wma301-stock tplink_wma301-ubootmod; do
  python3 "$ROOT/scripts/verify-source.py" --profile "$p" --source-dir "$ROOT/tests/fixtures/source"
done

# Generate source-synchronized single-device configs for all three profiles.
for p in tplink_wma301 tplink_wma301-stock tplink_wma301-ubootmod; do
  out="$TMP/$p.config"
  python3 "$ROOT/scripts/prepare-config.py" \
    --profile "$p" \
    --source-dir "$ROOT/tests/fixtures/source" \
    --output "$out" \
    --extra-config "$ROOT/configs/extra.config" \
    --include-initramfs
  grep -Fxq "CONFIG_TARGET_mediatek_mt7981=y" "$out"
  grep -Fxq "CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_${p}=y" "$out"
  test "$(grep -Ec '^CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_.+=y$' "$out")" -eq 1
  ! grep -q 'abt_asr3000' "$out"
  ! grep -q 'CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_' "$out"
done

# validate-config positive test against a generated config.
cp -a "$ROOT/tests/fixtures/source" "$TMP/source"
cp "$TMP/tplink_wma301.config" "$TMP/source/.config"
"$ROOT/scripts/validate-config.sh" tplink_wma301 "$TMP/source"

# validate-config must reject a second/wrong device.
printf '\nCONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_abt_asr3000=y\n' >> "$TMP/source/.config"
if "$ROOT/scripts/validate-config.sh" tplink_wma301 "$TMP/source" >/dev/null 2>&1; then
  echo 'ERROR: validate-config accepted a wrong-device selection' >&2
  exit 1
fi

# Collector positive test with upstream target checksums.
rm -rf "$TMP/source" "$TMP/out"
cp -a "$ROOT/tests/fixtures/source" "$TMP/source"
mkdir -p "$TMP/source/bin/targets/mediatek/filogic" "$TMP/out"
T="$TMP/source/bin/targets/mediatek/filogic"
printf 'factory\n' > "$T/immortalwrt-mediatek-filogic-tplink_wma301-squashfs-factory.bin"
printf 'sysupgrade\n' > "$T/immortalwrt-mediatek-filogic-tplink_wma301-squashfs-sysupgrade.bin"
(
  cd "$T"
  sha256sum immortalwrt-mediatek-filogic-tplink_wma301-squashfs-factory.bin \
            immortalwrt-mediatek-filogic-tplink_wma301-squashfs-sysupgrade.bin > sha256sums
)
python3 "$ROOT/scripts/collect-firmware.py" --profile tplink_wma301 --source-dir "$TMP/source" --output-dir "$TMP/out"
(cd "$TMP/out" && sha256sum -c SHA256SUMS-WMA301.txt)

# Collector must reject ASR3000 even if WMA301 files are otherwise valid.
printf 'wrong-device\n' > "$T/immortalwrt-mediatek-filogic-abt_asr3000-squashfs-factory.bin"
rm -rf "$TMP/out" && mkdir "$TMP/out"
if python3 "$ROOT/scripts/collect-firmware.py" --profile tplink_wma301 --source-dir "$TMP/source" --output-dir "$TMP/out" >/dev/null 2>&1; then
  echo 'ERROR: collector accepted an ASR3000-contaminated output directory' >&2
  exit 1
fi

# A changed upstream source contract must be rejected.
cp -a "$ROOT/tests/fixtures/source" "$TMP/bad-source"
sed -i 's/ARTIFACT\/preloader.bin := mt7981-bl2 spim-nand-ddr3/ARTIFACT\/preloader.bin := mt7981-bl2 unexpected-layout/' \
  "$TMP/bad-source/target/linux/mediatek/image/filogic.mk"
if python3 "$ROOT/scripts/verify-source.py" --profile tplink_wma301-ubootmod --source-dir "$TMP/bad-source" >/dev/null 2>&1; then
  echo 'ERROR: source contract validator accepted an unexpected bootloader layout' >&2
  exit 1
fi

echo 'All R3 static and safety tests passed.'
