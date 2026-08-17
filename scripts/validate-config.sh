#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:?usage: validate-config.sh <device-profile> [source-dir]}"
SOURCE_DIR="${2:-.}"
CONFIG="$SOURCE_DIR/.config"
IMAGE_MK="$SOURCE_DIR/target/linux/mediatek/image/filogic.mk"
TARGET_MK="$SOURCE_DIR/target/linux/mediatek/Makefile"

case "$PROFILE" in
  tplink_wma301|tplink_wma301-stock|tplink_wma301-ubootmod) ;;
  *) echo "ERROR: unsupported WMA301 profile: $PROFILE" >&2; exit 2 ;;
esac

for f in "$CONFIG" "$IMAGE_MK" "$TARGET_MK"; do
  [[ -f "$f" ]] || { echo "ERROR: required file is missing: $f" >&2; exit 3; }
done

subtargets="$(sed -n 's/^SUBTARGETS:=//p' "$TARGET_MK" | head -n1)"
case " $subtargets " in
  *" filogic "*) ;;
  *) echo "ERROR: source does not expose mediatek/filogic. SUBTARGETS='$subtargets'" >&2; exit 10 ;;
esac

grep -Fqx "define Device/$PROFILE" "$IMAGE_MK" || {
  echo "ERROR: profile '$PROFILE' is not defined in filogic.mk." >&2; exit 11;
}
grep -Fqx "TARGET_DEVICES += $PROFILE" "$IMAGE_MK" || {
  echo "ERROR: profile '$PROFILE' is not registered in TARGET_DEVICES." >&2; exit 12;
}

# The current source's canonical MT7981 defconfig deliberately uses this meta-target
# while per-device symbols point to mediatek/filogic.
for required in \
  'CONFIG_TARGET_mediatek=y' \
  'CONFIG_TARGET_mediatek_mt7981=y' \
  'CONFIG_TARGET_MULTI_PROFILE=y' \
  'CONFIG_TARGET_PER_DEVICE_ROOTFS=y' \
  'CONFIG_HAS_SUBTARGETS=y'; do
  grep -Fxq "$required" "$CONFIG" || {
    echo "ERROR: resolved config lost required source meta-target option: $required" >&2
    exit 20
  }
done

expected="CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_${PROFILE}=y"
grep -Fxq "$expected" "$CONFIG" || {
  echo "ERROR: expected WMA301 device was lost after make defconfig: $expected" >&2; exit 21;
}

mapfile -t selected < <(grep -E '^CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_.+=y$' "$CONFIG" || true)
if [[ ${#selected[@]} -ne 1 ]]; then
  echo "ERROR: expected exactly one selected mediatek/filogic device; found ${#selected[@]}." >&2
  printf '  %s\n' "${selected[@]:-<none>}" >&2
  exit 22
fi
if [[ "${selected[0]}" != "$expected" ]]; then
  echo "ERROR: wrong device selected: ${selected[0]}" >&2
  exit 23
fi

if grep -Eq '^CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_' "$CONFIG"; then
  echo "ERROR: obsolete/wrong per-device symbol namespace mediatek_mt7981 survived configuration." >&2
  exit 24
fi
if grep -Eiq 'CONFIG_TARGET_DEVICE_.*abt_asr3000=y' "$CONFIG"; then
  echo "ERROR: ABT ASR3000 is selected. Refusing to continue." >&2
  exit 25
fi

echo "Target validation passed: MT7981 meta-target -> mediatek/filogic/$PROFILE"
