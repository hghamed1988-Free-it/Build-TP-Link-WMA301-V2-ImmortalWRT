#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROFILE = "tplink_wma301"
EXPECTED_DTS = "mt7981b-tplink-wma301"
KNOWN_WMA301_PROFILES = (
    "tplink_wma301",
    "tplink_wma301-stock",
    "tplink_wma301-ubootmod",
)


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def device_block(text: str, profile: str) -> str:
    pattern = re.compile(rf"(?ms)^define Device/{re.escape(profile)}\s*$\n(?P<body>.*?)^endef\s*$")
    match = pattern.search(text)
    if not match:
        die(f"cannot find complete Device/{profile} block")
    return match.group(0)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the exact upstream TP-Link WMA301 build contract.")
    ap.add_argument("--source-dir", required=True)
    args = ap.parse_args()

    source = Path(args.source_dir).resolve()
    target_mk = source / "target/linux/mediatek/Makefile"
    image_mk = source / "target/linux/mediatek/image/filogic.mk"
    base_config = source / "defconfig/mt7981-ax3000.config"
    for path in (target_mk, image_mk, base_config):
        if not path.is_file() or path.stat().st_size == 0:
            die(f"required upstream file is missing or empty: {path}")

    target_text = target_mk.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?m)^SUBTARGETS:=(.*)$", target_text)
    if not match or "filogic" not in match.group(1).split():
        die("MediaTek no longer declares filogic as a subtarget")

    config_text = base_config.read_text(encoding="utf-8", errors="replace")
    for required in (
        "CONFIG_TARGET_mediatek=y",
        "CONFIG_TARGET_mediatek_mt7981=y",
        "CONFIG_TARGET_MULTI_PROFILE=y",
        "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
        "CONFIG_HAS_SUBTARGETS=y",
    ):
        if required not in config_text:
            die(f"canonical MT7981 defconfig contract changed; missing: {required}")
    if "CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_" not in config_text:
        die("canonical MT7981 config no longer uses mediatek_filogic per-device symbols")

    image_text = image_mk.read_text(encoding="utf-8", errors="replace")
    block = device_block(image_text, PROFILE)
    required_fragments = (
        "DEVICE_VENDOR := TP-Link",
        "DEVICE_MODEL := WMA301",
        f"DEVICE_DTS := {EXPECTED_DTS}",
        "SUPPORTED_DEVICES += mediatek,mt7981-spim-snand-rfb",
        "IMAGE_SIZE := 116736k",
        "KERNEL_IN_UBI := 1",
        "IMAGES += factory.bin",
        "IMAGE/factory.bin := append-ubi",
        "IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata",
        "KERNEL_INITRAMFS = kernel-bin",
    )
    for fragment in required_fragments:
        if fragment not in block:
            die(f"upstream WMA301 contract changed; missing: {fragment}")
    for forbidden in (
        "DEVICE_VARIANT := (stock layout)",
        "DEVICE_VARIANT := (OpenWrt layout)",
    ):
        if forbidden in block:
            die(f"base WMA301 profile unexpectedly became a layout variant: {forbidden}")
    if f"TARGET_DEVICES += {PROFILE}" not in image_text:
        die("tplink_wma301 is not registered in TARGET_DEVICES")

    # Keep awareness of sibling layouts so a future upstream rename/layout change fails visibly.
    for sibling in KNOWN_WMA301_PROFILES:
        device_block(image_text, sibling)
        if f"TARGET_DEVICES += {sibling}" not in image_text:
            die(f"known WMA301 profile is not registered: {sibling}")

    print("UPSTREAM CONTRACT PASSED")
    print("vendor=TP-Link")
    print("model=WMA301")
    print(f"profile={PROFILE}")
    print(f"dts={EXPECTED_DTS}")
    print("target=mediatek/filogic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
