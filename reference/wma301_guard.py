#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

VERSION = "R9.1"
TARGET_REL = Path("bin/targets/mediatek/filogic")
SELECTED_RE = re.compile(r"^CONFIG_TARGET_mediatek_filogic_DEVICE_.+=y$")
DEVICE_LINE = re.compile(r"^CONFIG_TARGET_DEVICE_.+_DEVICE_.+=")
DEVICE_PACKAGE_LINE = re.compile(r"^CONFIG_TARGET_DEVICE_PACKAGES_.+=")
SINGLE_DEVICE_LINE = re.compile(r"^CONFIG_TARGET_mediatek_filogic_DEVICE_.+=")

@dataclass(frozen=True)
class Profile:
    profile: str
    vendor: str
    model: str
    variant: str | None
    dts: str
    image_size: str
    factory_pattern: str
    sysupgrade_pattern: str
    initramfs_pattern: str

    @property
    def device_symbol(self) -> str:
        return f"CONFIG_TARGET_mediatek_filogic_DEVICE_{self.profile}=y"

    @property
    def package_symbol(self) -> str:
        return f'CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_{self.profile}=""'

SAFE = {
    "tplink_wma301": Profile(
        "tplink_wma301", "TP-Link", "WMA301", None,
        "mt7981b-tplink-wma301", "116736k",
        "*-tplink_wma301-squashfs-factory.bin",
        "*-tplink_wma301-squashfs-sysupgrade.bin",
        "*-tplink_wma301-initramfs-kernel.bin",
    ),
    "tplink_wma301-stock": Profile(
        "tplink_wma301-stock", "TP-Link", "WMA301", "(stock layout)",
        "mt7981b-tplink-wma301-stock", "65536k",
        "*-tplink_wma301-stock-squashfs-factory.bin",
        "*-tplink_wma301-stock-squashfs-sysupgrade.bin",
        "*-tplink_wma301-stock-initramfs-kernel.bin",
    ),
    "tplink_wma301_2.1": Profile(
        "tplink_wma301_2.1", "TP-Link", "WMA301 2.1", "(stock layout)",
        "mt7981b-tplink-wma301_2.1", "65536k",
        "*-tplink_wma301_2.1-squashfs-factory.bin",
        "*-tplink_wma301_2.1-squashfs-sysupgrade.bin",
        "*-tplink_wma301_2.1-initramfs-kernel.bin",
    ),
}
ADVANCED = {"tplink_wma301-ubootmod"}
KNOWN = set(SAFE) | ADVANCED

def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")

def profile(name: str) -> Profile:
    if name not in SAFE:
        die(f"unsupported/advanced profile {name!r}; allowed: {', '.join(SAFE)}")
    return SAFE[name]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def device_block(text: str, name: str) -> str:
    m = re.search(rf"(?ms)^define Device/{re.escape(name)}\s*$\n(?P<body>.*?)^endef\s*$", text)
    if not m:
        die(f"cannot find complete Device/{name} block")
    return m.group(0)

def check_source(source: Path, spec: Profile) -> None:
    target_mk = source / "target/linux/mediatek/Makefile"
    subtarget_mk = source / "target/linux/mediatek/filogic/target.mk"
    image_mk = source / "target/linux/mediatek/image/filogic.mk"
    base_cfg = source / "defconfig/mt7981-ax3000.config"
    for p in (target_mk, subtarget_mk, image_mk, base_cfg):
        if not p.is_file() or p.stat().st_size == 0:
            die(f"required upstream file missing/empty: {p}")

    target_text = target_mk.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?m)^SUBTARGETS:=(.*)$", target_text)
    if not m or "filogic" not in m.group(1).split():
        die("MediaTek no longer declares filogic in SUBTARGETS")

    subtarget_text = subtarget_mk.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"(?m)^SUBTARGET:=filogic\s*$", subtarget_text):
        die("filogic target.mk no longer declares SUBTARGET:=filogic")

    cfg_text = base_cfg.read_text(encoding="utf-8", errors="replace")
    for required in (
        "CONFIG_TARGET_mediatek=y",
        "CONFIG_TARGET_mediatek_mt7981=y",
        "CONFIG_TARGET_MULTI_PROFILE=y",
        "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
        "CONFIG_HAS_SUBTARGETS=y",
    ):
        if required not in cfg_text:
            die(f"canonical MT7981 meta-defconfig changed; missing {required}")
    if "CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_" not in cfg_text:
        die("canonical MT7981 meta-defconfig no longer uses filogic per-device symbols")

    image_text = image_mk.read_text(encoding="utf-8", errors="replace")
    registered = set(re.findall(r"(?m)^TARGET_DEVICES \+= (tplink_wma301[^\s]*)\s*$", image_text))
    if registered != KNOWN:
        die(f"WMA301 profile inventory changed; expected {sorted(KNOWN)}, found {sorted(registered)}")

    block = device_block(image_text, spec.profile)
    required = [
        f"DEVICE_VENDOR := {spec.vendor}",
        f"DEVICE_MODEL := {spec.model}",
        f"DEVICE_DTS := {spec.dts}",
        "SUPPORTED_DEVICES += mediatek,mt7981-spim-snand-rfb",
        f"IMAGE_SIZE := {spec.image_size}",
        "KERNEL_IN_UBI := 1",
        "IMAGES += factory.bin",
        "IMAGE/factory.bin := append-ubi",
        "IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata",
        "KERNEL_INITRAMFS = kernel-bin",
    ]
    if spec.variant:
        required.append(f"DEVICE_VARIANT := {spec.variant}")
    for token in required:
        if token not in block:
            die(f"source contract changed for {spec.profile}; missing {token}")
    if spec.variant is None and "DEVICE_VARIANT :=" in block:
        die(f"base profile {spec.profile} unexpectedly became a variant")

def prepare(source: Path, out_path: Path, spec: Profile, initramfs: bool) -> None:
    check_source(source, spec)
    base_cfg = source / "defconfig/mt7981-ax3000.config"
    raw = base_cfg.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    for line in raw:
        if DEVICE_LINE.match(line) or DEVICE_PACKAGE_LINE.match(line) or SINGLE_DEVICE_LINE.match(line):
            continue
        if line in {
            "CONFIG_TARGET_mediatek=y",
            "CONFIG_TARGET_mediatek_mt7981=y",
            "CONFIG_TARGET_mediatek_filogic=y",
            "CONFIG_TARGET_MULTI_PROFILE=y",
            "# CONFIG_TARGET_MULTI_PROFILE is not set",
            "CONFIG_TARGET_ALL_PROFILES=y",
            "# CONFIG_TARGET_ALL_PROFILES is not set",
            "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
            "# CONFIG_TARGET_PER_DEVICE_ROOTFS is not set",
            "CONFIG_TARGET_ROOTFS_INITRAMFS=y",
            "# CONFIG_TARGET_ROOTFS_INITRAMFS is not set",
        }:
            continue
        out.append(line)

    out += [
        "CONFIG_TARGET_mediatek=y",
        "CONFIG_TARGET_mediatek_filogic=y",
        "# CONFIG_TARGET_MULTI_PROFILE is not set",
        "# CONFIG_TARGET_ALL_PROFILES is not set",
        "CONFIG_TARGET_PER_DEVICE_ROOTFS=y",
        spec.device_symbol,
        "CONFIG_TARGET_ROOTFS_INITRAMFS=y" if initramfs else "# CONFIG_TARGET_ROOTFS_INITRAMFS is not set",
    ]
    selected = [x for x in out if SELECTED_RE.match(x)]
    if selected != [spec.device_symbol]:
        die(f"generated config is not exactly one requested device: {selected}")
    if any("abt_asr3000" in x.lower() for x in out):
        die("ASR3000 survived config generation")
    if any("CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_" in x for x in out):
        die("obsolete mediatek_mt7981 per-device namespace survived config generation")
    if any(x.startswith("CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_") and x.endswith("=y") for x in out):
        die("multi-profile device namespace survived single-profile generation")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")

def validate_resolved(source: Path, spec: Profile, initramfs: bool) -> None:
    cfg = source / ".config"
    if not cfg.is_file() or cfg.stat().st_size == 0:
        die(f"resolved config missing/empty: {cfg}")
    lines = cfg.read_text(encoding="utf-8", errors="replace").splitlines()
    s = set(lines)
    for required in ("CONFIG_TARGET_mediatek=y", "CONFIG_TARGET_mediatek_filogic=y", spec.device_symbol):
        if required not in s:
            die(f"resolved config missing required identity: {required}")
    if "CONFIG_TARGET_MULTI_PROFILE=y" in s or "CONFIG_TARGET_ALL_PROFILES=y" in s:
        die("multi/all-profile mode is enabled")
    if initramfs and "CONFIG_TARGET_ROOTFS_INITRAMFS=y" not in s:
        die("initramfs was requested but is disabled")
    selected = [x for x in lines if SELECTED_RE.match(x)]
    if selected != [spec.device_symbol]:
        die(f"resolved device mismatch; selected={selected}, expected={[spec.device_symbol]}")
    if any("abt_asr3000" in x.lower() and x.endswith("=y") for x in lines):
        die("ABT ASR3000 is selected")
    if any(x.startswith("CONFIG_TARGET_DEVICE_mediatek_mt7981_DEVICE_") and x.endswith("=y") for x in lines):
        die("obsolete mediatek_mt7981 per-device namespace is selected")
    if any(x.startswith("CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_") and x.endswith("=y") for x in lines):
        die("multi-profile device namespace is selected")

def read_sums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line.strip())
        if m:
            out[m.group(2)] = m.group(1).lower()
    return out

def exactly_one(target: Path, pattern: str, label: str) -> Path:
    hits = sorted(p for p in target.glob(pattern) if p.is_file() and not p.is_symlink())
    if len(hits) != 1:
        die(f"expected exactly one {label} matching {pattern!r}; found {[p.name for p in hits]}")
    if hits[0].stat().st_size <= 0:
        die(f"{label} is empty: {hits[0].name}")
    return hits[0]

def collect(source: Path, output: Path, spec: Profile, initramfs: bool,
            source_repo: str, source_ref: str, source_commit: str) -> None:
    target = source / TARGET_REL
    if not target.is_dir():
        die(f"target output missing: {target}")
    names = [p.name for p in target.iterdir() if p.is_file()]
    if any("abt_asr3000" in n.lower() for n in names):
        die("ASR3000 output is present in target directory")
    if any("tplink_wma301-ubootmod" in n for n in names):
        die("unsafe ubootmod output is present in safe build")

    for other_name, other in SAFE.items():
        if other_name == spec.profile:
            continue
        for pat in (other.factory_pattern, other.sysupgrade_pattern, other.initramfs_pattern):
            wrong = [n for n in names if fnmatch.fnmatch(n, pat)]
            if wrong:
                die(f"sibling profile output detected ({other_name}): {wrong}")

    factory = exactly_one(target, spec.factory_pattern, "factory image")
    sysupgrade = exactly_one(target, spec.sysupgrade_pattern, "sysupgrade image")
    images = [factory, sysupgrade]
    init_hits = sorted(p for p in target.glob(spec.initramfs_pattern) if p.is_file())
    if initramfs:
        images.append(exactly_one(target, spec.initramfs_pattern, "initramfs image"))
    elif len(init_hits) == 1:
        images.append(init_hits[0])
    elif len(init_hits) > 1:
        die(f"multiple initramfs images found: {[p.name for p in init_hits]}")

    sums_file = target / "sha256sums"
    if not sums_file.is_file() or sums_file.stat().st_size == 0:
        die("target sha256sums is missing")
    upstream_sums = read_sums(sums_file)
    for image in images:
        expected = upstream_sums.get(image.name)
        if not expected:
            die(f"{image.name} not listed in upstream sha256sums")
        actual = sha256(image)
        if actual != expected:
            die(f"upstream SHA-256 mismatch for {image.name}")

    profiles_file = target / "profiles.json"
    if not profiles_file.is_file() or profiles_file.stat().st_size == 0:
        die("profiles.json missing/empty")
    pdata = json.loads(profiles_file.read_text(encoding="utf-8"))
    profiles = pdata.get("profiles") or {}
    if set(profiles) != {spec.profile}:
        die(f"profiles.json must contain exactly {spec.profile}; found {sorted(profiles)}")
    meta = json.dumps(profiles[spec.profile], ensure_ascii=False).lower()
    if spec.vendor.lower() not in meta or spec.model.lower() not in meta:
        die("profiles.json does not identify expected vendor/model")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    copied = []
    for image in images:
        dst = output / image.name
        shutil.copy2(image, dst)
        copied.append(dst)
    for name in ("profiles.json", "config.buildinfo", "feeds.buildinfo", "version.buildinfo"):
        src = target / name
        if src.is_file():
            shutil.copy2(src, output / name)
    shutil.copy2(sums_file, output / "TARGET-sha256sums.txt")

    (output / "SHA256SUMS-VERIFIED-WMA301.txt").write_text(
        "".join(f"{sha256(p)}  {p.name}\n" for p in copied), encoding="utf-8"
    )
    manifest = {
        "schema": 4,
        "verification_status": "PASSED_R9_SELF_CONTAINED_FAIL_CLOSED_GATES",
        "source_device_vendor": spec.vendor,
        "source_device_model": spec.model,
        "source_device_variant": spec.variant,
        "profile": spec.profile,
        "dts": spec.dts,
        "target": "mediatek/filogic",
        "source_repo": source_repo,
        "source_ref": source_ref,
        "source_commit": source_commit,
        "images": [
            {"name": p.name, "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in copied
        ],
    }
    (output / "WMA301-BUILD-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "BUILD-IDENTITY.txt").write_text(
        "\n".join([
            "verification_status=PASSED_R9_SELF_CONTAINED_FAIL_CLOSED_GATES",
            f"source_device_vendor={spec.vendor}",
            f"source_device_model={spec.model}",
            f"source_device_variant={spec.variant or ''}",
            f"profile={spec.profile}",
            f"dts={spec.dts}",
            "target=mediatek/filogic",
            f"source_repo={source_repo}",
            f"source_ref={source_ref}",
            f"source_commit={source_commit}",
        ]) + "\n", encoding="utf-8"
    )

def final_gate(root: Path, spec: Profile, initramfs: bool) -> None:
    manifest_file = root / "WMA301-BUILD-MANIFEST.json"
    sums_file = root / "SHA256SUMS-VERIFIED-WMA301.txt"
    identity_file = root / "BUILD-IDENTITY.txt"
    for p in (manifest_file, sums_file, identity_file):
        if not p.is_file() or p.stat().st_size == 0:
            die(f"required verification file missing: {p.name}")

    m = json.loads(manifest_file.read_text(encoding="utf-8"))
    expected = {
        "schema": 4,
        "verification_status": "PASSED_R9_SELF_CONTAINED_FAIL_CLOSED_GATES",
        "source_device_vendor": spec.vendor,
        "source_device_model": spec.model,
        "source_device_variant": spec.variant,
        "profile": spec.profile,
        "dts": spec.dts,
        "target": "mediatek/filogic",
    }
    for k, v in expected.items():
        if m.get(k) != v:
            die(f"manifest identity mismatch {k}: {m.get(k)!r} != {v!r}")

    files = [Path(x["name"]).name for x in m.get("images", [])]
    pats = [spec.factory_pattern, spec.sysupgrade_pattern]
    if initramfs:
        pats.append(spec.initramfs_pattern)
    for pat in pats:
        if sum(fnmatch.fnmatch(n, pat) for n in files) != 1:
            die(f"manifest must contain exactly one file matching {pat}")

    expected_sums = read_sums(sums_file)
    for item in m["images"]:
        p = root / item["name"]
        if not p.is_file() or p.stat().st_size <= 0:
            die(f"manifest image missing/empty: {item['name']}")
        digest = sha256(p)
        if digest != item["sha256"] or expected_sums.get(p.name) != digest:
            die(f"final SHA-256 mismatch: {p.name}")

    ident = identity_file.read_text(encoding="utf-8", errors="replace")
    for token in (
        "verification_status=PASSED_R9_SELF_CONTAINED_FAIL_CLOSED_GATES",
        f"profile={spec.profile}",
        f"dts={spec.dts}",
        "target=mediatek/filogic",
    ):
        if token not in ident:
            die(f"BUILD-IDENTITY missing token: {token}")

def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("profile")
    p.add_argument("--profile", required=True)

    p = sub.add_parser("verify-source")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--profile", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--initramfs", action="store_true")

    p = sub.add_parser("validate")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--initramfs", action="store_true")

    p = sub.add_parser("collect")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--initramfs", action="store_true")
    p.add_argument("--source-repo", required=True)
    p.add_argument("--source-ref", required=True)
    p.add_argument("--source-commit", required=True)

    p = sub.add_parser("final")
    p.add_argument("--artifact-dir", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--initramfs", action="store_true")

    a = ap.parse_args()
    spec = profile(a.profile)

    if a.cmd == "profile":
        print(f"profile={spec.profile}")
        print(f"vendor={spec.vendor}")
        print(f"model={spec.model}")
        print(f"variant={spec.variant or '(none)'}")
        print(f"dts={spec.dts}")
        print("target=mediatek/filogic")
        print(f"device_symbol={spec.device_symbol}")
    elif a.cmd == "verify-source":
        check_source(Path(a.source_dir).resolve(), spec)
        print(f"SOURCE GATE PASSED: {spec.vendor} {spec.model} / {spec.profile}")
    elif a.cmd == "prepare":
        prepare(Path(a.source_dir).resolve(), Path(a.output).resolve(), spec, a.initramfs)
        print(f"CONFIG GENERATED: {spec.profile}")
    elif a.cmd == "validate":
        validate_resolved(Path(a.source_dir).resolve(), spec, a.initramfs)
        print(f"RESOLVED CONFIG PASSED: {spec.profile} / mediatek/filogic")
    elif a.cmd == "collect":
        collect(
            Path(a.source_dir).resolve(), Path(a.output_dir).resolve(), spec, a.initramfs,
            a.source_repo, a.source_ref, a.source_commit
        )
        print(f"COLLECTOR PASSED: {spec.profile}")
    elif a.cmd == "final":
        final_gate(Path(a.artifact_dir).resolve(), spec, a.initramfs)
        print(f"FINAL R9 GATE PASSED: {spec.profile}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
