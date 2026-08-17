#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-tplink_wma301}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-$ROOT/immortalwrt}"
SOURCE_REPO="${SOURCE_REPO:-https://github.com/zeromake/immortalwrt-mt798x-6.6.git}"
SOURCE_REF="${SOURCE_REF:-openwrt-24.10-6.6}"
INCLUDE_INITRAMFS="${INCLUDE_INITRAMFS:-true}"

case "$PROFILE" in
  tplink_wma301|tplink_wma301-stock|tplink_wma301-ubootmod) ;;
  *) echo "Unsupported profile: $PROFILE" >&2; exit 2 ;;
esac

python3 "$ROOT/scripts/self-check.py"

if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  git clone --depth 1 --single-branch --branch "$SOURCE_REF" "$SOURCE_REPO" "$SOURCE_DIR"
fi

python3 "$ROOT/scripts/verify-source.py" --profile "$PROFILE" --source-dir "$SOURCE_DIR"

prepare_args=(
  --profile "$PROFILE"
  --source-dir "$SOURCE_DIR"
  --output "$SOURCE_DIR/.config"
  --extra-config "$ROOT/configs/extra.config"
)
if [[ "$INCLUDE_INITRAMFS" == "true" ]]; then
  prepare_args+=(--include-initramfs)
fi
python3 "$ROOT/scripts/prepare-config.py" "${prepare_args[@]}"

cd "$SOURCE_DIR"
./scripts/feeds update -a
./scripts/feeds install -a
make defconfig
"$ROOT/scripts/validate-config.sh" "$PROFILE" "$SOURCE_DIR"
make download -j"$(nproc)"
make -j"$(nproc)" || make -j1 V=s
"$ROOT/scripts/validate-config.sh" "$PROFILE" "$SOURCE_DIR"
python3 "$ROOT/scripts/verify-source.py" --profile "$PROFILE" --source-dir "$SOURCE_DIR"

rm -rf "$ROOT/firmware"
mkdir -p "$ROOT/firmware"
python3 "$ROOT/scripts/collect-firmware.py" \
  --profile "$PROFILE" \
  --source-dir "$SOURCE_DIR" \
  --output-dir "$ROOT/firmware"
cp .config "$ROOT/firmware/effective.config"
printf 'source_repo=%s\nsource_ref=%s\nsource_commit=%s\ndevice_profile=%s\ntarget=mediatek/filogic\ninitramfs=%s\n' \
  "$SOURCE_REPO" "$SOURCE_REF" "$(git rev-parse HEAD)" "$PROFILE" "$INCLUDE_INITRAMFS" > "$ROOT/firmware/SOURCE.txt"
(cd "$ROOT/firmware" && sha256sum -c SHA256SUMS-WMA301.txt)

echo "Verified firmware is in: $ROOT/firmware"
