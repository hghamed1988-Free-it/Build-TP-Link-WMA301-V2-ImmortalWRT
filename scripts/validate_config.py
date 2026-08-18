#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROFILE = "tplink_wma301"
EXPECTED = f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{PROFILE}=y"
SELECTED_RE = re.compile(r"^CONFIG_TARGET_DEVICE_.+_DEVICE_.+=y$")


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed validation of the resolved WMA301 .config.")
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--require-initramfs", action="store_true")
    args = ap.parse_args()

    config = Path(args.source_dir).resolve() / ".config"
    if not config.is_file():
        die(f"resolved config missing: {config}")
    lines = config.read_text(encoding="utf-8", errors="replace").splitlines()
    line_set = set(lines)

    for required in ("CONFIG_TARGET_mediatek=y", "CONFIG_TARGET_mediatek_mt7981=y", EXPECTED):
        if required not in line_set:
            die(f"resolved config missing required identity: {required}")
    if "CONFIG_TARGET_MULTI_PROFILE=y" in line_set:
        die("multi-profile mode is enabled")
    if args.require_initramfs and "CONFIG_TARGET_ROOTFS_INITRAMFS=y" not in line_set:
        die("initramfs was requested but is not enabled after make defconfig")

    selected = [line for line in lines if SELECTED_RE.match(line)]
    if len(selected) != 1:
        die(f"expected exactly one selected device; found {len(selected)}: {selected}")
    if selected[0] != EXPECTED:
        die(f"wrong device selected: {selected[0]}")
    if any("abt_asr3000" in line.lower() and line.endswith("=y") for line in lines):
        die("ABT ASR3000 is selected")
    if any(line.startswith("CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_") and line.endswith("=y") for line in lines):
        die("obsolete mediatek_mt7981 device namespace is selected")

    print("RESOLVED CONFIG PASSED")
    print("vendor=TP-Link")
    print("model=WMA301")
    print("profile=tplink_wma301")
    print("dts=mt7981b-tplink-wma301")
    print("target=mediatek/filogic")
    print(f"selected_symbol={selected[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
