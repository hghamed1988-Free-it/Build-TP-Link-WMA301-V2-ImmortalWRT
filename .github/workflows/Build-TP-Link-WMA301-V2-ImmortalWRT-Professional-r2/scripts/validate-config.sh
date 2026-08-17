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

[[ -f "$CONFIG" ]] || { echo "ERROR: missing $CONFIG" >&2; exit 3; }
[[ -f "$IMAGE_MK" ]] || { echo "ERROR: missing filogic image definition: $IMAGE_MK" >&2; exit 3; }
[[ -f "$TARGET_MK" ]] || { echo "ERROR: missing MediaTek target Makefile: $TARGET_MK" >&2; exit 3; }

grep -Eq '^SUBTARGETS:=.*(^|[[:space:]])filogic([[:space:]]|$)' "$TARGET_MK" || {
  echo "ERROR: source does not expose the mediatek/filogic subtarget." >&2
  exit 10
}

grep -Fq "define Device/$PROFILE" "$IMAGE_MK" || {
  echo "ERROR: profile '$PROFILE' is not defined in filogic.mk." >&2
  exit 11
}
grep -Fq "TARGET_DEVICES += $PROFILE" "$IMAGE_MK" || {
  echo "ERROR: profile '$PROFILE' is not registered in TARGET_DEVICES." >&2
  exit 12
}

expected="CONFIG_TARGET_mediatek_filogic_DEVICE_${PROFILE}=y"
grep -Fxq 'CONFIG_TARGET_mediatek=y' "$CONFIG" || { echo "ERROR: MediaTek target is not selected." >&2; exit 20; }
grep -Fxq 'CONFIG_TARGET_mediatek_filogic=y' "$CONFIG" || { echo "ERROR: filogic subtarget is not selected." >&2; exit 21; }
grep -Fxq "$expected" "$CONFIG" || { echo "ERROR: expected profile was lost after make defconfig: $expected" >&2; exit 22; }

mapfile -t selected < <(grep -E '^CONFIG_TARGET_mediatek_filogic_DEVICE_.+=y$' "$CONFIG" || true)
if [[ ${#selected[@]} -ne 1 ]]; then
  echo "ERROR: expected exactly one selected filogic image profile; found ${#selected[@]}." >&2
  printf '  %s\n' "${selected[@]:-<none>}" >&2
  exit 23
fi
if [[ "${selected[0]}" != "$expected" ]]; then
  echo "ERROR: wrong profile selected: ${selected[0]}" >&2
  exit 24
fi

if grep -Eq '^CONFIG_TARGET(_DEVICE)?_.*DEVICE_abt_asr3000=y$' "$CONFIG"; then
  echo "ERROR: ABT ASR3000 was selected. Refusing to continue." >&2
  exit 25
fi

if grep -Eq '^CONFIG_TARGET_mediatek_mt7981=y$|^CONFIG_TARGET_mediatek_mt7981_DEVICE_' "$CONFIG"; then
  echo "ERROR: obsolete mediatek/mt7981 target symbols survived configuration." >&2
  exit 26
fi

echo "Target validation passed: mediatek/filogic/$PROFILE"
