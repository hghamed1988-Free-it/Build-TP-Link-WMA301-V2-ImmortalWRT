#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROFILES = ("tplink_wma301", "tplink_wma301-stock", "tplink_wma301-ubootmod")
REQUIRED_BASE = (
    "CONFIG_TARGET_mediatek=y",
    "CONFIG_TARGET_mediatek_mt7981=y",
    "CONFIG_TARGET_MULTI_PROFILE=y",
    "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
    "CONFIG_HAS_SUBTARGETS=y",
)
DEVICE_RE = re.compile(r"^CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_.+=y$")
DEVICE_PACKAGES_RE = re.compile(r"^CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_.*=")
FORBIDDEN_OVERRIDE_PREFIXES = (
    "CONFIG_TARGET_mediatek=",
    "CONFIG_TARGET_mediatek_mt7981=",
    "CONFIG_TARGET_MULTI_PROFILE=",
    "CONFIG_TARGET_PER_DEVICE_ROOTFS=",
    "CONFIG_HAS_SUBTARGETS=",
    "CONFIG_TARGET_DEVICE_",
    "CONFIG_TARGET_DEVICE_PACKAGES_",
)


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a single-device WMA301 config from the source's canonical MT7981 defconfig.")
    ap.add_argument("--profile", required=True, choices=PROFILES)
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--extra-config")
    ap.add_argument("--include-initramfs", action="store_true")
    args = ap.parse_args()

    source = Path(args.source_dir).resolve()
    base_path = source / "defconfig/mt7981-ax3000.config"
    if not base_path.is_file():
        die(f"canonical source defconfig is missing: {base_path}")

    raw_lines = base_path.read_text(encoding="utf-8", errors="replace").splitlines()
    raw_text = "\n".join(raw_lines)
    for required in REQUIRED_BASE:
        if required not in raw_text:
            die(f"source MT7981 defconfig contract changed; missing: {required}")

    # Remove every preselected filogic device from the source's multi-profile defconfig.
    # Keep the source-maintained package/kernel policy, then add exactly one WMA301 device.
    lines: list[str] = []
    for line in raw_lines:
        if DEVICE_RE.match(line) or DEVICE_PACKAGES_RE.match(line):
            continue
        if line == "CONFIG_TARGET_ROOTFS_INITRAMFS=y" or line == "# CONFIG_TARGET_ROOTFS_INITRAMFS is not set":
            continue
        lines.append(line)

    if args.extra_config:
        extra_path = Path(args.extra_config).resolve()
        if extra_path.is_file():
            for line in extra_path.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.startswith(FORBIDDEN_OVERRIDE_PREFIXES):
                    die(f"extra.config may not override target/device selection: {stripped}")
                lines.append(stripped)

    lines.extend([
        f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{args.profile}=y",
        f"CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_{args.profile}=\"\"",
    ])
    if args.include_initramfs:
        lines.append("CONFIG_TARGET_ROOTFS_INITRAMFS=y")

    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    selected = [line for line in lines if DEVICE_RE.match(line)]
    expected = f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{args.profile}=y"
    if selected != [expected]:
        die(f"generated config is not single-device: {selected}")
    if any("abt_asr3000" in line.lower() for line in lines):
        die("generated config still contains ABT ASR3000")

    print(f"Generated source-synchronized config for {args.profile}")
    print(f"Base: {base_path}")
    print(f"Initramfs: {'enabled' if args.include_initramfs else 'disabled'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
