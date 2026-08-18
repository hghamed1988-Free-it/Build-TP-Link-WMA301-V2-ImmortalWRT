#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROFILE = "tplink_wma301"
EXPECTED_DEVICE = f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{PROFILE}=y"
EXPECTED_PACKAGES = f'CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_{PROFILE}=""'
DEVICE_LINE = re.compile(r"^CONFIG_TARGET_DEVICE_.+_DEVICE_.+=")
DEVICE_PACKAGE_LINE = re.compile(r"^CONFIG_TARGET_DEVICE_PACKAGES_.+=")


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a source-synchronized single-device WMA301 .config.")
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--include-initramfs", action="store_true")
    args = ap.parse_args()

    source = Path(args.source_dir).resolve()
    base = source / "defconfig/mt7981-ax3000.config"
    if not base.is_file():
        die(f"canonical MT7981 config is missing: {base}")
    raw = base.read_text(encoding="utf-8", errors="replace").splitlines()
    text = "\n".join(raw)
    for required in (
        "CONFIG_TARGET_mediatek=y",
        "CONFIG_TARGET_mediatek_mt7981=y",
        "CONFIG_TARGET_MULTI_PROFILE=y",
        "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
        "CONFIG_HAS_SUBTARGETS=y",
    ):
        if required not in text:
            die(f"source defconfig changed; missing: {required}")

    out_lines: list[str] = []
    for line in raw:
        if DEVICE_LINE.match(line) or DEVICE_PACKAGE_LINE.match(line):
            continue
        if line in {
            "CONFIG_TARGET_MULTI_PROFILE=y",
            "# CONFIG_TARGET_MULTI_PROFILE is not set",
            "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
            "# CONFIG_TARGET_PER_DEVICE_ROOTFS is not set",
            "CONFIG_TARGET_ROOTFS_INITRAMFS=y",
            "# CONFIG_TARGET_ROOTFS_INITRAMFS is not set",
        }:
            continue
        out_lines.append(line)

    out_lines.extend([
        "# CONFIG_TARGET_MULTI_PROFILE is not set",
        "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
        EXPECTED_DEVICE,
        EXPECTED_PACKAGES,
    ])
    if args.include_initramfs:
        out_lines.append("CONFIG_TARGET_ROOTFS_INITRAMFS=y")

    # Defensive final checks before writing.
    selected = [line for line in out_lines if re.match(r"^CONFIG_TARGET_DEVICE_.+_DEVICE_.+=y$", line)]
    if selected != [EXPECTED_DEVICE]:
        die(f"generated config is not single-device WMA301: {selected}")
    if any("abt_asr3000" in line.lower() for line in out_lines):
        die("ASR3000 survived config generation")
    if any("CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_" in line for line in out_lines):
        die("obsolete mediatek_mt7981 device namespace survived config generation")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Generated exact config: {output}")
    print(f"device_symbol={EXPECTED_DEVICE}")
    print(f"initramfs={'true' if args.include_initramfs else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
