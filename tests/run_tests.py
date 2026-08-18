#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != expect:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"command returned {proc.returncode}, expected {expect}: {' '.join(args)}")
    return proc


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run(PYTHON, "scripts/self_check.py")
    for script in (
        "scripts/self_check.py",
        "scripts/verify_source.py",
        "scripts/prepare_config.py",
        "scripts/validate_config.py",
        "scripts/collect_artifact.py",
        "scripts/final_gate.py",
    ):
        run(PYTHON, "-m", "py_compile", script)

    fixture = ROOT / "tests/fixtures/source"
    run(PYTHON, "scripts/verify_source.py", "--source-dir", str(fixture))

    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        source = tmp / "source"
        shutil.copytree(fixture, source)
        run(PYTHON, "scripts/prepare_config.py", "--source-dir", str(source), "--output", str(source / ".config"), "--include-initramfs")
        text = (source / ".config").read_text()
        assert "CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_tplink_wma301=y" in text
        assert text.count("CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_tplink_wma301=y") == 1
        assert "abt_asr3000" not in text
        assert "CONFIG_TARGET_MULTI_PROFILE=y" not in text
        run(PYTHON, "scripts/validate_config.py", "--source-dir", str(source), "--require-initramfs")

        # Wrong-device negative test.
        with (source / ".config").open("a", encoding="utf-8") as handle:
            handle.write("CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_abt_asr3000=y\n")
        bad = subprocess.run([PYTHON, "scripts/validate_config.py", "--source-dir", str(source)], cwd=ROOT)
        if bad.returncode == 0:
            raise SystemExit("validate_config accepted an ASR3000-contaminated config")

        # Restore a valid config and synthesize exact output metadata/images.
        run(PYTHON, "scripts/prepare_config.py", "--source-dir", str(source), "--output", str(source / ".config"), "--include-initramfs")
        target = source / "bin/targets/mediatek/filogic"
        target.mkdir(parents=True)
        images = [
            target / "immortalwrt-mediatek-filogic-tplink_wma301-squashfs-factory.bin",
            target / "immortalwrt-mediatek-filogic-tplink_wma301-squashfs-sysupgrade.bin",
            target / "immortalwrt-mediatek-filogic-tplink_wma301-initramfs-kernel.bin",
        ]
        for i, path in enumerate(images, 1):
            path.write_bytes(f"test-image-{i}\n".encode())
        (target / "sha256sums").write_text("".join(f"{digest(p)}  {p.name}\n" for p in images), encoding="utf-8")
        (target / "profiles.json").write_text(json.dumps({"profiles": {"tplink_wma301": {"image_prefix": "immortalwrt-mediatek-filogic-tplink_wma301", "titles": [{"vendor": "TP-Link", "model": "WMA301"}]}}}), encoding="utf-8")
        out = tmp / "artifact"
        run(PYTHON, "scripts/collect_artifact.py", "--source-dir", str(source), "--output-dir", str(out), "--require-initramfs", "--source-repo", "fixture", "--source-ref", "fixture", "--source-commit", "0123456789abcdef")
        run(PYTHON, "scripts/final_gate.py", "--artifact-dir", str(out), "--require-initramfs")

        # Collector must fail closed on wrong-device output.
        (target / "immortalwrt-mediatek-filogic-abt_asr3000-squashfs-factory.bin").write_text("wrong")
        bad_out = tmp / "bad-artifact"
        bad = subprocess.run([
            PYTHON, "scripts/collect_artifact.py", "--source-dir", str(source), "--output-dir", str(bad_out),
            "--require-initramfs", "--source-repo", "fixture", "--source-ref", "fixture", "--source-commit", "deadbeef"
        ], cwd=ROOT)
        if bad.returncode == 0:
            raise SystemExit("collector accepted an ASR3000-contaminated output")

    print("ALL R7 STATIC AND FAIL-CLOSED TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
