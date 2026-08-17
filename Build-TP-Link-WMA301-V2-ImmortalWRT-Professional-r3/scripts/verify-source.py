#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROFILES = {
    "tplink_wma301": {
        "required": [
            "DEVICE_VENDOR := TP-Link",
            "DEVICE_MODEL := WMA301",
            "DEVICE_DTS := mt7981b-tplink-wma301",
            "IMAGES += factory.bin",
            "IMAGE/factory.bin := append-ubi",
            "IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata",
        ],
        "forbidden": ["DEVICE_VARIANT := (stock layout)", "DEVICE_VARIANT := (OpenWrt layout)"],
    },
    "tplink_wma301-stock": {
        "required": [
            "DEVICE_VENDOR := TP-Link",
            "DEVICE_MODEL := WMA301",
            "DEVICE_VARIANT := (stock layout)",
            "DEVICE_DTS := mt7981b-tplink-wma301-stock",
            "IMAGES += factory.bin",
            "IMAGE/factory.bin := append-ubi",
            "IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata",
        ],
        "forbidden": ["DEVICE_VARIANT := (OpenWrt layout)"],
    },
    "tplink_wma301-ubootmod": {
        "required": [
            "DEVICE_VENDOR := TP-Link",
            "DEVICE_MODEL := WMA301",
            "DEVICE_VARIANT := (OpenWrt layout)",
            "DEVICE_DTS := mt7981b-tplink-wma301-ubootmod",
            "IMAGES := sysupgrade.itb",
            "IMAGE/sysupgrade.itb := append-kernel",
            "ARTIFACTS := preloader.bin bl31-uboot.fip",
            "ARTIFACT/preloader.bin := mt7981-bl2 spim-nand-ddr3",
            "ARTIFACT/bl31-uboot.fip := mt7981-bl31-uboot tplink_wma301",
        ],
        "forbidden": ["DEVICE_VARIANT := (stock layout)"],
    },
}


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def device_block(text: str, profile: str) -> str:
    pattern = re.compile(
        rf"(?ms)^define Device/{re.escape(profile)}\s*$\n(?P<body>.*?)^endef\s*$"
    )
    match = pattern.search(text)
    if not match:
        die(f"cannot find complete device block for {profile}")
    return match.group(0)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the upstream WMA301 source contract before building.")
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--source-dir", required=True)
    args = ap.parse_args()

    source = Path(args.source_dir).resolve()
    target_mk = source / "target/linux/mediatek/Makefile"
    image_mk = source / "target/linux/mediatek/image/filogic.mk"
    canonical_defconfig = source / "defconfig/mt7981-ax3000.config"
    if not target_mk.is_file() or not image_mk.is_file() or not canonical_defconfig.is_file():
        die("required MediaTek target/defconfig files are missing from the cloned source")

    target_text = target_mk.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?m)^SUBTARGETS:=(.*)$", target_text)
    if not m or "filogic" not in m.group(1).split():
        die("the source no longer declares filogic as a MediaTek subtarget")

    canonical_text = canonical_defconfig.read_text(encoding="utf-8", errors="replace")
    for required in (
        "CONFIG_TARGET_mediatek=y",
        "CONFIG_TARGET_mediatek_mt7981=y",
        "CONFIG_TARGET_MULTI_PROFILE=y",
        "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
        "CONFIG_HAS_SUBTARGETS=y",
    ):
        if required not in canonical_text:
            die(f"canonical MT7981 defconfig contract changed; missing: {required}")
    if "CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_" not in canonical_text:
        die("canonical MT7981 defconfig no longer uses mediatek/filogic per-device symbols")

    image_text = image_mk.read_text(encoding="utf-8", errors="replace")
    profile = args.profile
    block = device_block(image_text, profile)

    registration = f"TARGET_DEVICES += {profile}"
    if registration not in image_text:
        die(f"{profile} is defined but not registered in TARGET_DEVICES")

    for fragment in PROFILES[profile]["required"]:
        if fragment not in block:
            die(f"source contract changed for {profile}; missing: {fragment}")
    for fragment in PROFILES[profile]["forbidden"]:
        if fragment in block:
            die(f"source contract changed for {profile}; unexpected: {fragment}")

    # Cross-profile safety: all three known WMA301 definitions must still be present.
    for known in PROFILES:
        device_block(image_text, known)
        if f"TARGET_DEVICES += {known}" not in image_text:
            die(f"known WMA301 profile is no longer registered: {known}")

    print(f"Source contract verified for mediatek/filogic/{profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
