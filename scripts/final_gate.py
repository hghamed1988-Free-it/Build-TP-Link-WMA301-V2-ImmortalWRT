#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Final fail-closed gate before GitHub artifact upload.")
    ap.add_argument("--artifact-dir", required=True)
    ap.add_argument("--require-initramfs", action="store_true")
    args = ap.parse_args()
    root = Path(args.artifact_dir).resolve()
    manifest_path = root / "WMA301-BUILD-MANIFEST.json"
    sums_path = root / "SHA256SUMS-VERIFIED-WMA301.txt"
    identity_path = root / "BUILD-IDENTITY.txt"
    for p in (manifest_path, sums_path, identity_path):
        if not p.is_file() or p.stat().st_size == 0:
            die(f"required verification file missing: {p.name}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "verification_status": "PASSED_FAIL_CLOSED_GATES",
        "source_device_vendor": "TP-Link",
        "source_device_model": "WMA301",
        "profile": "tplink_wma301",
        "dts": "mt7981b-tplink-wma301",
        "target": "mediatek/filogic",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            die(f"manifest identity mismatch: {key}={manifest.get(key)!r}, expected {value!r}")

    files = [Path(item["name"]).name for item in manifest.get("images", [])]
    required_suffixes = ["-tplink_wma301-squashfs-factory.bin", "-tplink_wma301-squashfs-sysupgrade.bin"]
    if args.require_initramfs:
        required_suffixes.append("-tplink_wma301-initramfs-kernel.bin")
    for suffix in required_suffixes:
        if sum(name.endswith(suffix) for name in files) != 1:
            die(f"manifest does not contain exactly one image ending with {suffix}")
    if any(any(marker in name.lower() for marker in ("asr3000", "wma301-stock", "wma301-ubootmod")) for name in files):
        die("manifest contains wrong-device/layout image")

    expected_sums: dict[str, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([0-9a-f]{64})\s+(.+)$", line.strip())
        if match:
            expected_sums[match.group(2)] = match.group(1)
    for item in manifest["images"]:
        path = root / item["name"]
        if not path.is_file() or path.stat().st_size == 0:
            die(f"manifest image missing or empty: {item['name']}")
        digest = sha256(path)
        if digest != item["sha256"] or expected_sums.get(path.name) != digest:
            die(f"final SHA-256 mismatch: {path.name}")

    print("FINAL GATE PASSED: exact TP-Link WMA301 artifact is internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
