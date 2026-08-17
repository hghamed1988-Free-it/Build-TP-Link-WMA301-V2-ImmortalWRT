#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ALLOWED = {
    "tplink_wma301": {
        "required_suffixes": ("factory.bin", "sysupgrade.bin"),
        "forbidden_markers": ("tplink_wma301-stock", "tplink_wma301-ubootmod"),
    },
    "tplink_wma301-stock": {
        "required_suffixes": ("factory.bin", "sysupgrade.bin"),
        "forbidden_markers": (),
    },
    "tplink_wma301-ubootmod": {
        "required_suffixes": ("sysupgrade.itb", "preloader.bin", "bl31-uboot.fip"),
        "forbidden_markers": (),
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=sorted(ALLOWED))
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    source = Path(args.source_dir).resolve()
    target = source / "bin" / "targets" / "mediatek" / "filogic"
    output = Path(args.output_dir).resolve()
    profile = args.profile
    rules = ALLOWED[profile]

    if not target.is_dir():
        raise SystemExit(f"ERROR: target output directory not found: {target}")

    output.mkdir(parents=True, exist_ok=True)

    # Only WMA301 files belonging to the selected source profile are eligible.
    candidates: list[Path] = []
    for p in sorted(target.iterdir()):
        if not p.is_file():
            continue
        name = p.name
        if profile not in name:
            continue
        if any(marker in name for marker in rules["forbidden_markers"]):
            continue
        if not name.endswith((".bin", ".itb", ".img.gz", ".ubi", ".fip")):
            continue
        candidates.append(p)

    if not candidates:
        raise SystemExit(f"ERROR: no firmware images found for {profile}")

    names = [p.name for p in candidates]
    for suffix in rules["required_suffixes"]:
        if not any(name.endswith(suffix) for name in names):
            raise SystemExit(f"ERROR: required {profile} output '*{suffix}' is missing. Found: {names}")

    # A wrong-device build must never be publishable.
    all_image_names = [p.name for p in target.iterdir() if p.is_file()]
    if any("abt_asr3000" in n for n in all_image_names):
        raise SystemExit("ERROR: ABT ASR3000 output detected in target directory; refusing publication.")

    # Validate profile metadata when available.
    profiles_path = target / "profiles.json"
    if profiles_path.exists():
        data = json.loads(profiles_path.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
        if profile not in profiles:
            raise SystemExit(f"ERROR: profiles.json does not contain selected profile '{profile}'.")
        display = json.dumps(profiles[profile], ensure_ascii=False).lower()
        if "wma301" not in display and "wma301" not in profile.lower():
            raise SystemExit("ERROR: selected profile metadata does not identify WMA301.")
        shutil.copy2(profiles_path, output / profiles_path.name)

    metadata_names = ("config.buildinfo", "feeds.buildinfo", "version.buildinfo")
    for name in metadata_names:
        p = target / name
        if p.exists():
            shutil.copy2(p, output / name)

    copied: list[Path] = []
    for src in candidates:
        dst = output / src.name
        shutil.copy2(src, dst)
        copied.append(dst)

    sums = output / "SHA256SUMS-WMA301.txt"
    sums.write_text("".join(f"{sha256(p)}  {p.name}\n" for p in copied), encoding="utf-8")

    manifest = {
        "profile": profile,
        "target": "mediatek/filogic",
        "images": [{"name": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in copied],
    }
    (output / "WMA301-BUILD-MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Collected {len(copied)} verified WMA301 image(s) for {profile}:")
    for p in copied:
        print(f"  {p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
