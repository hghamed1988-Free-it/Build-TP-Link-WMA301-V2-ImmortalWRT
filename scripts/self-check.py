#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def main() -> int:
    required_files = [
        ".github/workflows/build.yml",
        "configs/extra.config",
        "scripts/prepare-config.py",
        "scripts/verify-source.py",
        "scripts/validate-config.sh",
        "scripts/collect-firmware.py",
        "scripts/build-local.sh",
    ]
    for rel in required_files:
        if not (ROOT / rel).is_file():
            fail(f"missing required project file: {rel}")

    workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    required_tokens = [
        "python3 scripts/self-check.py",
        "python3 scripts/verify-source.py",
        "python3 scripts/prepare-config.py",
        "./scripts/validate-config.sh",
        "python3 scripts/collect-firmware.py",
        "actions/upload-artifact@v4",
        "actions/download-artifact@v4",
        "defconfig/mt7981-ax3000.config",
    ]
    for token in required_tokens:
        if token not in workflow:
            fail(f"workflow does not wire required gate/source contract: {token}")

    forbidden_tokens = [
        'find bin/targets/ -name "*.bin"',
        "CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_",
        "mv $CONFIG_FILE immortalwrt/.config",
    ]
    for token in forbidden_tokens:
        if token in workflow:
            fail(f"workflow contains forbidden legacy/broad-collection pattern: {token}")

    extra = (ROOT / "configs/extra.config").read_text(encoding="utf-8")
    for line in extra.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("CONFIG_TARGET"):
            fail("configs/extra.config must not contain target/device selection")

    print("Project self-check passed: source-derived config generation and all publication gates are wired.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
