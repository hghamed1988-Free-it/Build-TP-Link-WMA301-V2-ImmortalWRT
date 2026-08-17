#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

RULES = {
    "tplink_wma301": {
        "required_suffixes": ("factory.bin", "sysupgrade.bin"),
        "forbidden_profile_markers": ("tplink_wma301-stock", "tplink_wma301-ubootmod"),
    },
    "tplink_wma301-stock": {
        "required_suffixes": ("factory.bin", "sysupgrade.bin"),
        "forbidden_profile_markers": ("tplink_wma301-ubootmod",),
    },
    "tplink_wma301-ubootmod": {
        "required_suffixes": ("sysupgrade.itb", "preloader.bin", "bl31-uboot.fip"),
        "forbidden_profile_markers": ("tplink_wma301-stock",),
    },
}

IMAGE_EXTENSIONS = (".bin", ".itb", ".img.gz", ".ubi", ".fip")
METADATA = ("config.buildinfo", "feeds.buildinfo", "version.buildinfo", "profiles.json")


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_upstream_sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", raw)
        if m:
            result[m.group(2)] = m.group(1).lower()
    return result


def is_profile_file(name: str, profile: str, forbidden: tuple[str, ...]) -> bool:
    if profile not in name:
        return False
    if any(marker in name for marker in forbidden):
        return False
    return name.endswith(IMAGE_EXTENSIONS)


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect only verified TP-Link WMA301 firmware outputs.")
    ap.add_argument("--profile", required=True, choices=sorted(RULES))
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    source = Path(args.source_dir).resolve()
    target = source / "bin/targets/mediatek/filogic"
    output = Path(args.output_dir).resolve()
    profile = args.profile
    rules = RULES[profile]

    if not target.is_dir():
        die(f"target output directory not found: {target}")

    all_files = [p for p in sorted(target.iterdir()) if p.is_file() and not p.is_symlink()]
    all_names = [p.name for p in all_files]

    if any("abt_asr3000" in n.lower() for n in all_names):
        die("ABT ASR3000 output detected in mediatek/filogic; publication is blocked")

    # Reject outputs of a different WMA301 layout. A single-device build should not emit siblings.
    sibling_profiles = set(RULES) - {profile}
    for sibling in sibling_profiles:
        sibling_names = [n for n in all_names if sibling in n]
        # Base name is a prefix of the two variants, so don't treat the base as a sibling marker.
        if sibling == "tplink_wma301" and profile.startswith("tplink_wma301-"):
            continue
        if sibling_names:
            die(f"unexpected WMA301 sibling-layout output detected ({sibling}): {sibling_names}")

    candidates = [
        p for p in all_files
        if is_profile_file(p.name, profile, rules["forbidden_profile_markers"])
    ]
    if not candidates:
        die(f"no firmware images found for {profile}")

    names = [p.name for p in candidates]
    for suffix in rules["required_suffixes"]:
        if not any(name.endswith(suffix) for name in names):
            die(f"required {profile} output '*{suffix}' is missing; found: {names}")

    upstream_sums_file = target / "sha256sums"
    if not upstream_sums_file.is_file():
        die("target sha256sums is missing; refusing to publish unverifiable images")
    upstream_sums = read_upstream_sums(upstream_sums_file)
    for p in candidates:
        expected = upstream_sums.get(p.name)
        if not expected:
            die(f"{p.name} is absent from target sha256sums")
        actual = sha256(p)
        if actual != expected:
            die(f"upstream SHA-256 mismatch for {p.name}: expected {expected}, got {actual}")

    profiles_path = target / "profiles.json"
    if profiles_path.is_file():
        data = json.loads(profiles_path.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
        if profile not in profiles:
            die(f"profiles.json does not contain selected profile '{profile}'")
        metadata_text = json.dumps(profiles[profile], ensure_ascii=False).lower()
        if "wma301" not in metadata_text:
            die("selected profiles.json entry does not identify WMA301")

    if output.exists():
        if any(output.iterdir()):
            die(f"output directory must be empty: {output}")
    else:
        output.mkdir(parents=True)

    copied: list[Path] = []
    for src in candidates:
        dst = output / src.name
        shutil.copy2(src, dst)
        copied.append(dst)

    for name in METADATA:
        src = target / name
        if src.is_file():
            shutil.copy2(src, output / name)
    shutil.copy2(upstream_sums_file, output / "TARGET-sha256sums.txt")

    own_sums = output / "SHA256SUMS-WMA301.txt"
    own_sums.write_text(
        "".join(f"{sha256(p)}  {p.name}\n" for p in copied),
        encoding="utf-8",
    )

    manifest = {
        "schema": 1,
        "device": "TP-Link WMA301 V2",
        "target": "mediatek/filogic",
        "profile": profile,
        "images": [
            {"name": p.name, "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in copied
        ],
    }
    (output / "WMA301-BUILD-MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Collected {len(copied)} verified WMA301 image(s) for {profile}:")
    for p in copied:
        print(f"  {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
