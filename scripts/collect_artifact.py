#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

PROFILE = "tplink_wma301"
TARGET_REL = Path("bin/targets/mediatek/filogic")
METADATA_FILES = ("profiles.json", "config.buildinfo", "feeds.buildinfo", "version.buildinfo")


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_sums(path: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line.strip())
        if match:
            sums[match.group(2)] = match.group(1).lower()
    return sums


def exactly_one(target: Path, pattern: str, label: str) -> Path:
    matches = sorted(p for p in target.glob(pattern) if p.is_file() and not p.is_symlink())
    if len(matches) != 1:
        die(f"expected exactly one {label} matching {pattern!r}; found {[p.name for p in matches]}")
    if matches[0].stat().st_size == 0:
        die(f"{label} is empty: {matches[0].name}")
    return matches[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect only exact, checksummed TP-Link WMA301 images.")
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--require-initramfs", action="store_true")
    ap.add_argument("--source-repo", required=True)
    ap.add_argument("--source-ref", required=True)
    ap.add_argument("--source-commit", required=True)
    args = ap.parse_args()

    source = Path(args.source_dir).resolve()
    target = source / TARGET_REL
    output = Path(args.output_dir).resolve()
    if not target.is_dir():
        die(f"target output directory missing: {target}")

    names = [p.name for p in target.iterdir() if p.is_file()]
    forbidden_markers = ("abt_asr3000", "tplink_wma301-stock", "tplink_wma301-ubootmod")
    contaminated = [name for name in names if any(marker in name.lower() for marker in forbidden_markers)]
    if contaminated:
        die(f"wrong-device/layout output detected: {contaminated}")

    factory = exactly_one(target, "*-tplink_wma301-squashfs-factory.bin", "factory image")
    sysupgrade = exactly_one(target, "*-tplink_wma301-squashfs-sysupgrade.bin", "sysupgrade image")
    images = [factory, sysupgrade]
    initramfs_matches = sorted(target.glob("*-tplink_wma301-initramfs-kernel.bin"))
    if args.require_initramfs:
        initramfs = exactly_one(target, "*-tplink_wma301-initramfs-kernel.bin", "initramfs image")
        images.append(initramfs)
    elif len(initramfs_matches) == 1 and initramfs_matches[0].is_file():
        images.append(initramfs_matches[0])
    elif len(initramfs_matches) > 1:
        die(f"multiple initramfs images found: {[p.name for p in initramfs_matches]}")

    sums_path = target / "sha256sums"
    if not sums_path.is_file() or sums_path.stat().st_size == 0:
        die("upstream target sha256sums is missing")
    upstream_sums = read_sums(sums_path)
    for image in images:
        expected = upstream_sums.get(image.name)
        if not expected:
            die(f"{image.name} is not listed in upstream sha256sums")
        actual = sha256(image)
        if actual != expected:
            die(f"upstream SHA-256 mismatch for {image.name}: expected {expected}, got {actual}")

    profiles_path = target / "profiles.json"
    if not profiles_path.is_file():
        die("profiles.json is missing")
    data = json.loads(profiles_path.read_text(encoding="utf-8"))
    profiles = data.get("profiles") or {}
    if PROFILE not in profiles:
        die("profiles.json does not contain tplink_wma301")
    if "abt_asr3000" in profiles:
        die("profiles.json contains abt_asr3000")
    profile_meta = profiles[PROFILE]
    meta_text = json.dumps(profile_meta, ensure_ascii=False).lower()
    if "wma301" not in meta_text:
        die("profiles.json WMA301 entry does not identify WMA301")
    if any(key in profiles for key in ("tplink_wma301-stock", "tplink_wma301-ubootmod")):
        die("profiles.json contains a sibling WMA301 layout in a single-device build")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    copied: list[Path] = []
    for image in images:
        dst = output / image.name
        shutil.copy2(image, dst)
        copied.append(dst)
    for name in METADATA_FILES:
        src = target / name
        if src.is_file():
            shutil.copy2(src, output / name)
    shutil.copy2(sums_path, output / "TARGET-sha256sums.txt")

    verified_sums = output / "SHA256SUMS-VERIFIED-WMA301.txt"
    verified_sums.write_text("".join(f"{sha256(p)}  {p.name}\n" for p in copied), encoding="utf-8")

    identity = {
        "schema": 2,
        "verification_status": "PASSED_FAIL_CLOSED_GATES",
        "requested_hardware": "TP-Link WMA301 V2",
        "source_device_vendor": "TP-Link",
        "source_device_model": "WMA301",
        "profile": PROFILE,
        "dts": "mt7981b-tplink-wma301",
        "target": "mediatek/filogic",
        "source_repo": args.source_repo,
        "source_ref": args.source_ref,
        "source_commit": args.source_commit,
        "images": [
            {"name": p.name, "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in copied
        ],
    }
    (output / "WMA301-BUILD-MANIFEST.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "BUILD-IDENTITY.txt").write_text(
        "\n".join([
            "verification_status=PASSED_FAIL_CLOSED_GATES",
            "requested_hardware=TP-Link WMA301 V2",
            "source_device_vendor=TP-Link",
            "source_device_model=WMA301",
            "profile=tplink_wma301",
            "dts=mt7981b-tplink-wma301",
            "target=mediatek/filogic",
            f"source_repo={args.source_repo}",
            f"source_ref={args.source_ref}",
            f"source_commit={args.source_commit}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(f"Collected {len(copied)} verified WMA301 image(s).")
    for p in copied:
        print(f"  {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
