#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> int:
    required = [
        ".github/workflows/build.yml",
        "scripts/verify_source.py",
        "scripts/prepare_config.py",
        "scripts/validate_config.py",
        "scripts/collect_artifact.py",
        "scripts/final_gate.py",
        "tests/run_tests.py",
        "FLASH-SAFETY.md",
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}")
    if (ROOT / ".config").exists():
        fail("a static root .config is forbidden; R7 generates it from upstream defconfig")

    workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    required_tokens = [
        "padavanonly/immortalwrt-mt798x-6.6.git",
        "openwrt-24.10-6.6",
        "python3 scripts/verify_source.py",
        "python3 scripts/prepare_config.py",
        "python3 scripts/validate_config.py",
        "python3 scripts/collect_artifact.py",
        "python3 scripts/final_gate.py",
        "actions/upload-artifact@v4",
        "contents: read",
    ]
    for token in required_tokens:
        if token not in workflow:
            fail(f"workflow missing required token: {token}")
    forbidden = [
        "contents: write",
        "gh release",
        "actions/download-artifact",
        'find bin/targets/ -name "*.bin"',
        "CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_",
        "./scripts/validate-config.sh",
        "publish_release",
    ]
    for token in forbidden:
        if token in workflow:
            fail(f"workflow contains forbidden legacy/risky token: {token}")

    pycache = list(ROOT.rglob("__pycache__")) + list(ROOT.rglob("*.pyc"))
    if pycache:
        fail(f"generated Python cache files must not ship: {pycache}")

    print("PROJECT SELF-CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
