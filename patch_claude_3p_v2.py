#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Desktop 3P patcher v2 (0703-aware)
==========================================

Safer successor to patch_claude.py. It can patch an installed Claude.app or copy
Claude.app from a DMG into a temporary workspace, apply 3P/Cowork compatibility
patches, recalculate ASAR integrity, re-sign the app, and emit a capability
report for 3P deployments.

Default behavior is conservative: when --dmg/--from-dmg is used, the script
patches a temporary app and does NOT replace /Applications/Claude.app unless
--install is passed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import plistlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import importlib.util
from pathlib import Path
from typing import Any


APP_DEFAULT = Path("/Applications/Claude.app")
ROOT = Path(__file__).resolve().parent
DEFAULT_DMG = ROOT / "Claude-0703.dmg"
APP_ASAR_REL = Path("Contents/Resources/app.asar")
ASAR_INDEX = ".vite/build/index.js"
ASAR_SWIFT = "node_modules/@ant/claude-swift/js/index.js"
ASAR_INTEGRITY_BLOCK_SIZE = 4 * 1024 * 1024
POLICY_DOMAIN = "com.anthropic.claudefordesktop"
FRONTEND_ASSETS_REL = Path("Contents/Resources/ion-dist/assets/v1")

RESTRICTED_ENTITLEMENTS = {
    "com.apple.application-identifier",
    "com.apple.developer.team-identifier",
    "keychain-access-groups",
    "com.apple.developer.associated-domains",
    "com.apple.developer.default-data-protection",
}

DEFAULT_ENTITLEMENTS: dict[str, Any] = {
    "com.apple.security.cs.allow-jit": True,
    "com.apple.security.cs.allow-unsigned-executable-memory": True,
    "com.apple.security.cs.disable-library-validation": True,
    "com.apple.security.device.audio-input": True,
    "com.apple.security.device.bluetooth": True,
    "com.apple.security.device.camera": True,
    "com.apple.security.device.print": True,
    "com.apple.security.device.usb": True,
    "com.apple.security.network.client": True,
    "com.apple.security.network.server": True,
    "com.apple.security.personal-information.location": True,
    "com.apple.security.personal-information.photos-library": True,
    "com.apple.security.virtualization": True,
}

POLICY_KEYS = [
    "secureVmFeaturesEnabled",
    "allowedWorkspaceFolders",
    "disableAutoUpdates",
    "autoUpdaterEnforcementHours",
    "isDesktopExtensionEnabled",
    "isDesktopExtensionDirectoryEnabled",
    "isLocalDevMcpEnabled",
    "isClaudeCodeForDesktopEnabled",
    "forceLoginOrgUUID",
]

LOCAL_FEATURE_BOOL_KEYS = [
    "secureVmFeaturesEnabled",
    "isDesktopExtensionEnabled",
    "isDesktopExtensionDirectoryEnabled",
    "isLocalDevMcpEnabled",
    "isClaudeCodeForDesktopEnabled",
]

LANG_CHOICES = ["zh-CN", "zh-TW", "zh-HK"]


# ---------------------------------------------------------------------------
# Optional localization bridge


def load_zh_cn_patcher():
    module_path = ROOT / "patch_claude_zh_cn.py"
    if not module_path.exists():
        raise SystemExit(f"Missing localization helper: {module_path}")
    spec = importlib.util.spec_from_file_location("patch_claude_zh_cn", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load localization helper: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Basic helpers


def run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")


def quit_claude() -> None:
    run(["osascript", "-e", 'tell application "Claude" to quit'])


# ---------------------------------------------------------------------------
# ASAR helpers (ported from patch_claude_zh_cn.py style)


def align4(value: int) -> int:
    return value + ((4 - (value % 4)) % 4)


def read_asar_header(data: bytes, path: Path) -> tuple[int, str, dict[str, Any]]:
    if len(data) < 16:
        raise SystemExit(f"Unsupported app.asar header in {path}")
    size_pickle_payload = struct.unpack_from("<I", data, 0)[0]
    header_size = struct.unpack_from("<I", data, 4)[0]
    if size_pickle_payload != 4 or header_size <= 0 or len(data) < 8 + header_size:
        raise SystemExit(f"Unsupported app.asar size pickle in {path}")

    header_pickle = data[8 : 8 + header_size]
    header_payload_size = struct.unpack_from("<I", header_pickle, 0)[0]
    header_string_size = struct.unpack_from("<i", header_pickle, 4)[0]
    expected_payload_size = align4(4 + header_string_size)
    if header_payload_size != expected_payload_size or header_size != 4 + header_payload_size:
        raise SystemExit(f"Unsupported app.asar header pickle in {path}")

    header_string = header_pickle[8 : 8 + header_string_size].decode("utf-8")
    header = json.loads(header_string)
    if not isinstance(header, dict):
        raise SystemExit(f"Unsupported app.asar header JSON in {path}")
    return header_size, header_string, header


def encode_asar_header(header_string: str, expected_header_size: int) -> bytes:
    header_bytes = header_string.encode("utf-8")
    header_payload_size = align4(4 + len(header_bytes))
    header_pickle = (
        struct.pack("<I", header_payload_size)
        + struct.pack("<i", len(header_bytes))
        + header_bytes
        + b"\0" * (header_payload_size - 4 - len(header_bytes))
    )
    if len(header_pickle) != expected_header_size:
        raise SystemExit("Internal patch error: app.asar header length changed")
    return struct.pack("<I", 4) + struct.pack("<I", expected_header_size) + header_pickle


def get_asar_file_entry(header: dict[str, Any], file_path: str) -> dict[str, Any]:
    node: dict[str, Any] = header
    for part in file_path.split("/"):
        files = node.get("files")
        if not isinstance(files, dict) or part not in files:
            raise KeyError(file_path)
        child = files[part]
        if not isinstance(child, dict):
            raise SystemExit(f"Unsupported app.asar header entry for {file_path}")
        node = child
    for key in ["size", "offset"]:
        if key not in node:
            raise SystemExit(f"Missing {key} for {file_path} in app.asar header")
    return node


def calculate_file_integrity(data: bytes) -> dict[str, Any]:
    blocks = [
        hashlib.sha256(data[offset : offset + ASAR_INTEGRITY_BLOCK_SIZE]).hexdigest()
        for offset in range(0, len(data), ASAR_INTEGRITY_BLOCK_SIZE)
    ]
    if not blocks:
        blocks.append(hashlib.sha256(data).hexdigest())
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(data).hexdigest(),
        "blockSize": ASAR_INTEGRITY_BLOCK_SIZE,
        "blocks": blocks,
    }


def update_electron_asar_integrity(app: Path, header_string: str) -> bool:
    info_plist = app / "Contents/Info.plist"
    if not info_plist.exists():
        return False
    with info_plist.open("rb") as f:
        info = plistlib.load(f)
    integrity = info.get("ElectronAsarIntegrity")
    if not isinstance(integrity, dict):
        return False
    app_asar = integrity.get("Resources/app.asar")
    if not isinstance(app_asar, dict) or app_asar.get("algorithm") != "SHA256":
        return False
    app_asar["hash"] = hashlib.sha256(header_string.encode("utf-8")).hexdigest()
    tmp = info_plist.with_suffix(info_plist.suffix + ".tmp")
    with tmp.open("wb") as f:
        plistlib.dump(info, f, fmt=plistlib.FMT_XML)
    os.replace(tmp, info_plist)
    return True


# ---------------------------------------------------------------------------
# Byte patching


def pad_bytes(replacement: bytes, target_len: int) -> bytes:
    if len(replacement) > target_len:
        raise SystemExit(f"Internal patch error: replacement longer than target ({len(replacement)} > {target_len})")
    return replacement + b" " * (target_len - len(replacement))


def patch_exact(content: bytes, original: bytes, replacement: bytes, label: str, *, allow_multi: bool = False) -> tuple[bytes, dict[str, Any]]:
    if len(original) != len(replacement):
        raise SystemExit(f"Internal patch error for {label}: non-equal replacement length")
    count = content.count(original)
    already = content.count(replacement)
    result = {
        "label": label,
        "status": "missing",
        "matches": count,
        "already_matches": already,
        "offsets": [],
    }
    if count == 0:
        if already:
            result["status"] = "already_applied"
        return content, result
    if count > 1 and not allow_multi:
        result["status"] = "ambiguous"
        result["offsets"] = [m.start() for m in re.finditer(re.escape(original), content)]
        return content, result

    offsets: list[int] = []
    patched = content
    if count > 1 and allow_multi:
        patched = patched.replace(original, replacement)
        offsets = [m.start() for m in re.finditer(re.escape(original), content)]
    else:
        pos = patched.find(original)
        patched = patched[:pos] + replacement + patched[pos + len(original) :]
        offsets = [pos]
    result.update({"status": "applied", "offsets": offsets})
    return patched, result


def apply_alternatives(content: bytes, label: str, alternatives: list[tuple[bytes, bytes, bool]]) -> tuple[bytes, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    patched = content
    applied = False
    for original, replacement, allow_multi in alternatives:
        patched, res = patch_exact(patched, original, replacement, label, allow_multi=allow_multi)
        if res["status"] in {"applied", "already_applied", "ambiguous"}:
            results.append(res)
            if res["status"] == "applied":
                applied = True
            if res["status"] == "ambiguous":
                break
    if not results:
        results.append({"label": label, "status": "missing", "matches": 0, "already_matches": 0, "offsets": []})
    elif applied:
        # Keep only concrete hits for readability.
        results = [r for r in results if r["status"] in {"applied", "ambiguous"}]
    return patched, results


def build_index_patch_specs() -> list[tuple[str, list[tuple[bytes, bytes, bool]]]]:
    title_0623 = b'.catch(Q=>(D.warn("[title-gen] failed",{error:String(Q)}),""))'
    title_0703 = b'.catch(f=>(D.warn("[title-gen] failed",{error:String(f)}),""))'
    return [
        (
            "L1 3P managed config safeParse bypass",
            [
                (b'const a=b$i.safeParse(s);', b'var a={data:s,success:1};', False),
                (b'const l=Ewi.safeParse(E);', b'var l={data:E,success:1};', False),
                (b'const s=jci.safeParse(o);', b'var s={data:o,success:1};', False),
            ],
        ),
        (
            "L2 model picker empty allowlist bypass",
            [
                (b'if(A.startsWith("claude-"))return!0;if(e.length===0)return!1;', b'if(A.startsWith("claude-"))return!0;if(e.length===0)return!0;', False),
                (b'if(e.startsWith("claude-"))return!0;if(A.length===0)return!1;', b'if(e.startsWith("claude-"))return!0;if(A.length===0)return!0;', False),
            ],
        ),
        (
            "L2b model picker terminal some() bypass",
            [
                (b'return e.some(i=>i===A||$d(i)===t)}', b'return e.some(i=>!0);/*padpadpad*/}', False),
                (b'return e.some(r=>r===A||qB(r)===t)}', b'return e.some(r=>!0);/*padpadpad*/}', False),
            ],
        ),
        (
            "L2c gateway model route validator bypass",
            [
                (b'function v4i(A){return PX(A)?{ok:!0}', b'function v4i(A){return 1!==0?{ok:!0}', False),
                (b'function Tni(A){return UrA(A)?{ok:!0}', b'function Tni(A){return 1!==0 ?{ok:!0}', False),
                (
                    b'function FrA(A,e){if(A===void 0)return{ok:!0};',
                    pad_bytes(b'function FrA(A,e){if(1)return{ok:!0};', len(b'function FrA(A,e){if(A===void 0)return{ok:!0};')),
                    False,
                ),
            ],
        ),
        (
            "L4 force auto-update early return",
            [
                (
                    b'if(A.disableAutoUpdates){D.info("[updater] Auto-updates disabled by enterprise policy"),Ye("desktop_update_disabled",{reason:"enterprise_policy"});return}',
                    b'if(1||A.disableAutoUpda){D.info("[updater] Auto-updates disabled by enterprise policy"),Ye("desktop_update_disabled",{reason:"enterprise_policy"});return}',
                    False,
                ),
                (
                    b'if(fi().disableAutoUpdates){D.info("[updater] Auto-updates disabled by enterprise policy");return}',
                    b'if(1||fi().disableAutoUpda){D.info("[updater] Auto-updates disabled by enterprise policy");return}',
                    False,
                ),
                (
                    b'if(A.autoUpdate.disabled){',
                    pad_bytes(b'if(1||A.autoUpdate.dis){', len(b'if(A.autoUpdate.disabled){')),
                    False,
                ),
                (
                    b'if(cr().autoUpdate.disabled){',
                    pad_bytes(b'if(1||cr().autoUpdate.dis){', len(b'if(cr().autoUpdate.disabled){')),
                    False,
                ),
                (b'if(e.disableAutoUpdates)', pad_bytes(b'if(1||e.disableAutoU)', len(b'if(e.disableAutoUpdates)')), False),
                (b'if(ki().disableAutoUpdates)', pad_bytes(b'if(1||ki().disableAutoU)', len(b'if(ki().disableAutoUpdates)')), False),
            ],
        ),
        (
            "L5 inference model catalog throw bypass",
            [
                (b'const c=O$i(A);if(c)throw', b'const c=O$i(A);if(0)throw', False),
                (b'const g=C$i(a.data.provider,a.data.models);if(g)throw', b'const g=C$i(a.data.provider,a.data.models);if(0)throw', False),
            ],
        ),
        (
            "L6 session title fallback",
            [
                (title_0623, pad_bytes(b'.catch(()=>String(d.first_session_message||"").slice(0,46))', len(title_0623)), True),
                (title_0703, pad_bytes(b'.catch(()=>String(B.first_session_message||"").slice(0,46))', len(title_0703)), True),
            ],
        ),
        (
            "L7 effort xhigh compatibility",
            [
                (b'function qUA(A){return A!=null&&wQr.has(A)?A:void 0}', b'function qUA(A){return A!=null&&mQr.has(A)?A:void 0}', False),
                # 0703 moved this logic into config-derived effort sets. Keep xhigh out of generic/default options.
                (
                    b'const xxi=new Set(["low","medium","high","max"]),Pxi=new Set(["low","medium","high","xhigh","max","unset"]);',
                    pad_bytes(b'const xxi=new Set(["low","medium","high","max"]),Pxi=new Set(["low","medium","high","max","unset","max"]);', len(b'const xxi=new Set(["low","medium","high","max"]),Pxi=new Set(["low","medium","high","xhigh","max","unset"]);')),
                    False,
                ),
            ],
        ),
    ]


def patch_index(content: bytes) -> tuple[bytes, list[dict[str, Any]]]:
    all_results: list[dict[str, Any]] = []
    patched = content
    for label, alternatives in build_index_patch_specs():
        patched, results = apply_alternatives(patched, label, alternatives)
        all_results.extend(results)
    return patched, all_results


def patch_swift(content: bytes) -> tuple[bytes, list[dict[str, Any]]]:
    original = b'    // ComputerUse bindings live in a separate SPM product (ComputerUseSwift)\n'
    replacement = b'    this.vm.isVirtualizationSupported = () => "supported";                   \n'
    patched, result = patch_exact(content, original, replacement, "L3b claude-swift virtualization support")
    return patched, [result]


def patch_asar(app: Path, *, dry_run: bool = False) -> dict[str, Any]:
    asar = app / APP_ASAR_REL
    require_file(asar)
    before_sha = sha256_file(asar)
    data = bytearray(asar.read_bytes())
    header_size, _header_string, header = read_asar_header(data, asar)
    report: dict[str, Any] = {"path": str(asar), "sha256_before": before_sha, "files": [], "patches": []}

    modified = False
    for target, patcher in [(ASAR_INDEX, patch_index), (ASAR_SWIFT, patch_swift)]:
        try:
            entry = get_asar_file_entry(header, target)
        except KeyError:
            report["files"].append({"path": target, "status": "missing"})
            continue
        start = 8 + header_size + int(entry["offset"])
        size = int(entry["size"])
        end = start + size
        content = bytes(data[start:end])
        patched_content, patch_results = patcher(content)
        file_modified = patched_content != content
        modified = modified or file_modified
        report["files"].append({"path": target, "status": "modified" if file_modified else "unchanged", "size": size})
        report["patches"].extend({**r, "file": target} for r in patch_results)
        if file_modified and not dry_run:
            data[start:end] = patched_content
            entry["integrity"] = calculate_file_integrity(patched_content)

    ambiguous = [p for p in report["patches"] if p["status"] == "ambiguous"]
    if ambiguous:
        raise SystemExit("Ambiguous patch matches found; refusing to write. See report for details.")

    applied = [p for p in report["patches"] if p["status"] == "applied"]
    if not applied:
        report["status"] = "no_changes"
        report["sha256_after"] = before_sha
        return report

    if dry_run:
        report["status"] = "would_patch"
        report["sha256_after"] = before_sha
        return report

    updated_header_string = json.dumps(header, ensure_ascii=False, separators=(",", ":"))
    updated_header = encode_asar_header(updated_header_string, header_size)
    data[: len(updated_header)] = updated_header
    asar.write_bytes(data)
    integrity_updated = update_electron_asar_integrity(app, updated_header_string)
    report["status"] = "patched"
    report["sha256_after"] = sha256_file(asar)
    report["electron_integrity_updated"] = integrity_updated
    return report


# ---------------------------------------------------------------------------
# Entitlements and signing


def load_entitlements(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["codesign", "-d", "--entitlements", ":-", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        data = plistlib.loads(result.stdout)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def sanitize_entitlements(entitlements: dict[str, Any] | None) -> dict[str, Any]:
    ent = dict(entitlements or DEFAULT_ENTITLEMENTS)
    for key in RESTRICTED_ENTITLEMENTS:
        ent.pop(key, None)
    ent["com.apple.security.cs.disable-library-validation"] = True
    ent.setdefault("com.apple.security.virtualization", True)
    return ent


def is_signable_file(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    if path.suffix in {".dylib", ".node", ".so"}:
        return True
    return os.access(path, os.X_OK)


def sign_path(path: Path, entitlements_dir: Path) -> tuple[bool, str]:
    ent = sanitize_entitlements(load_entitlements(path)) if load_entitlements(path) else {}
    cmd = ["codesign", "--force", "--sign", "-", "--options", "runtime", "--preserve-metadata=identifier,flags"]
    if ent:
        digest = hashlib.sha1(path.as_posix().encode()).hexdigest()[:16]
        ent_path = entitlements_dir / f"{digest}.plist"
        ent_path.write_bytes(plistlib.dumps(ent, fmt=plistlib.FMT_XML))
        cmd.extend(["--entitlements", str(ent_path)])
    cmd.append(str(path))
    result = run(cmd)
    return result.returncode == 0, result.stdout


def resign_app(app: Path, *, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return {"status": "skipped_dry_run"}
    run(["xattr", "-cr", str(app)])
    entitlements_dir = Path(tempfile.mkdtemp(prefix="claude-3p-entitlements."))
    contents = app / "Contents"
    file_targets: list[Path] = []
    bundle_targets: list[Path] = []
    for root, dirs, files in os.walk(contents):
        root_path = Path(root)
        for dirname in dirs:
            p = root_path / dirname
            if p.suffix in {".app", ".framework"}:
                bundle_targets.append(p)
        for filename in files:
            p = root_path / filename
            if is_signable_file(p):
                file_targets.append(p)

    failures: list[dict[str, str]] = []
    for p in sorted(file_targets, key=lambda x: len(x.parts), reverse=True):
        ok, out = sign_path(p, entitlements_dir)
        if not ok:
            failures.append({"path": str(p), "output": out})
    for p in sorted(bundle_targets, key=lambda x: len(x.parts), reverse=True):
        ok, out = sign_path(p, entitlements_dir)
        if not ok:
            failures.append({"path": str(p), "output": out})

    outer_ent = sanitize_entitlements(load_entitlements(app))
    outer_ent_path = entitlements_dir / "outer.plist"
    outer_ent_path.write_bytes(plistlib.dumps(outer_ent, fmt=plistlib.FMT_XML))
    result = run([
        "codesign", "--force", "--deep", "--options", "runtime", "--preserve-metadata=identifier,flags",
        "--entitlements", str(outer_ent_path), "--sign", "-", str(app),
    ])
    if result.returncode != 0:
        failures.append({"path": str(app), "output": result.stdout})
    return {"status": "failed" if failures else "signed", "failures": failures}


def verify_app(app: Path) -> dict[str, Any]:
    verify = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
    ent = load_entitlements(app)
    info: dict[str, Any] = {
        "codesign_ok": verify.returncode == 0,
        "codesign_output": verify.stdout.strip(),
        "entitlements": {
            "virtualization": bool(ent.get("com.apple.security.virtualization")),
            "disable_library_validation": bool(ent.get("com.apple.security.cs.disable-library-validation")),
            "allow_jit": bool(ent.get("com.apple.security.cs.allow-jit")),
        },
    }
    return info


# ---------------------------------------------------------------------------
# DMG/app workflow


def mount_dmg(dmg: Path) -> tuple[Path, bool]:
    require_file(dmg)
    # Reuse an existing mounted Claude volume if present.
    for candidate in sorted(Path("/Volumes").glob("Claude*")):
        if (candidate / "Claude.app").exists():
            return candidate, False
    result = run(["hdiutil", "attach", "-nobrowse", "-readonly", str(dmg)])
    if result.returncode != 0:
        raise SystemExit(result.stdout)
    for line in result.stdout.splitlines():
        if "/Volumes/" in line:
            mount = Path(line.split("\t")[-1])
            if (mount / "Claude.app").exists():
                return mount, True
    for candidate in sorted(Path("/Volumes").glob("Claude*")):
        if (candidate / "Claude.app").exists():
            return candidate, True
    raise SystemExit("Mounted DMG, but could not find Claude.app")


def detach_dmg(mount: Path) -> None:
    run(["hdiutil", "detach", str(mount)])


def copy_app(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    result = run(["ditto", str(src), str(dst)])
    if result.returncode != 0:
        raise SystemExit(result.stdout)


def backup_and_install(patched_app: Path, target_app: Path, *, dry_run: bool = False) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target_app.with_name(f"Claude.backup-before-3p-v2-{stamp}.app")
    if dry_run:
        return backup
    if target_app.exists():
        shutil.move(str(target_app), str(backup))
    shutil.move(str(patched_app), str(target_app))
    return backup


# ---------------------------------------------------------------------------
# Frontend/local feature recovery helpers


def frontend_asset_bundles(app: Path) -> list[Path]:
    assets = app / FRONTEND_ASSETS_REL
    if not assets.exists():
        return []
    preferred = sorted(assets.glob("index-*.js"))
    return preferred or sorted(assets.glob("*.js"))


def append_frontend_injection(app: Path, marker: str, code: str, *, dry_run: bool = False) -> dict[str, Any]:
    bundles = frontend_asset_bundles(app)
    if not bundles:
        return {"status": "missing_assets", "marker": marker, "files": []}
    touched: list[str] = []
    already: list[str] = []
    payload = "\n;" + code.strip() + "\n"
    for path in bundles[:1]:
        text = path.read_text(encoding="utf-8")
        if marker in text:
            already.append(str(path))
            continue
        touched.append(str(path))
        if not dry_run:
            path.write_text(text + payload, encoding="utf-8")
    if touched:
        return {"status": "would_patch" if dry_run else "patched", "marker": marker, "files": touched}
    return {"status": "already_applied", "marker": marker, "files": already}



def patch_local_feature_ui(app: Path, *, dry_run: bool = False) -> dict[str, Any]:
    marker = "__claudeLocalFeatureRecoveryPatch"
    code = f'''
(()=>{{
  const MARK="{marker}";
  if(window[MARK]) return;
  window[MARK]=true;
  window.__CLAUDE_3P_LOCAL_FEATURE_RECOVERY__={{desktopExtensions:true,extensionDirectory:true,localMcp:true,claudeCode:true,secureVm:true}};
}})();
'''
    return append_frontend_injection(app, marker, code, dry_run=dry_run)


def apply_localization(app: Path, lang_code: str, user_home: Path, *, dry_run: bool = False, set_user_config: bool = False) -> dict[str, Any]:
    zh = load_zh_cn_patcher()
    config = zh.get_language_config(lang_code)
    for key in ["frontend_translation", "frontend_hardcoded", "desktop_translation", "localizable_strings"]:
        zh.require_file(config[key])
    if dry_run:
        return {"status": "would_patch", "lang": lang_code, "label": config.get("label"), "user_config": "skipped_dry_run"}
    warnings: list[str] = []
    try:
        zh.patch_language_whitelist(app, lang_code)
    except SystemExit as exc:
        assets_dir = app / FRONTEND_ASSETS_REL
        replacement = f'{zh.BASE_LANGUAGE_LIST},"{lang_code}"]'
        patched_whitelist = False
        for path in sorted(assets_dir.glob("*.js")):
            text = path.read_text(encoding="utf-8")
            if f'"{lang_code}"' in text and zh.LANG_LIST_RE.search(text):
                print(f"Language whitelist already contains {lang_code}: {path.name}")
                patched_whitelist = True
                break
            if zh.LANG_LIST_RE.search(text):
                patched = zh.LANG_LIST_RE.sub(replacement, text, count=1)
                path.write_text(patched, encoding="utf-8")
                print(f"Patched language whitelist: {path.name}")
                patched_whitelist = True
                break
        if not patched_whitelist:
            warnings.append(f"language whitelist not patched: {exc}")
    zh.patch_hardcoded_frontend_strings(app, lang_code)
    zh.patch_language_display_names(app)
    zh.patch_hardcoded_main_process_menu_labels(app)
    zh.merge_frontend_locale(app, lang_code)
    zh.install_desktop_locale(app, lang_code)
    zh.install_statsig_locale(app, lang_code)
    if set_user_config:
        zh.set_user_locale(user_home, lang_code)
        user_config = "updated"
    else:
        user_config = "skipped_not_installing"
    return {"status": "patched", "lang": lang_code, "label": config.get("label"), "user_config": user_config, "warnings": warnings}


def inspect_local_item(path: Path) -> dict[str, Any]:
    manifests = ["SKILL.md", "skill.md", "manifest.json", "plugin.json", "package.json", "mcp.json"]
    found = [name for name in manifests if (path / name).exists()] if path.is_dir() else []
    return {
        "name": path.name,
        "path": str(path),
        "is_dir": path.is_dir(),
        "manifests": found,
        "valid": bool(found) or path.suffix in {".dxt", ".mcpb", ".zip"},
    }


def local_market_report(user_home: Path) -> dict[str, Any]:
    candidates = [
        ("claude_user_skills", user_home / ".claude" / "skills"),
        ("claude_user_plugins", user_home / ".claude" / "plugins"),
        ("claude_user_workflows", user_home / ".claude" / "workflows"),
        ("claude_app_support", user_home / "Library/Application Support/Claude"),
        ("claude_desktop_extensions", user_home / "Library/Application Support/Claude/extensions"),
        ("claude_desktop_plugins", user_home / "Library/Application Support/Claude/plugins"),
        ("claude_desktop_skills", user_home / "Library/Application Support/Claude/skills"),
    ]
    dirs = []
    for label, path in candidates:
        entry: dict[str, Any] = {"label": label, "path": str(path), "exists": path.exists(), "items": []}
        if path.exists() and path.is_dir():
            children = sorted(path.iterdir(), key=lambda p: p.name.lower())
            entry["item_count"] = len(children)
            entry["items"] = [inspect_local_item(child) for child in children[:100]]
        else:
            entry["item_count"] = 0
        dirs.append(entry)
    return {
        "mode": "local_report_only",
        "note": "Local skills/plugins/extensions directories are scanned; no remote content is downloaded.",
        "directories": dirs,
    }


# ---------------------------------------------------------------------------
# Policy and capability reporting


def read_defaults_value(domain: str, key: str, *, global_domain: bool = False) -> Any:
    cmd = ["defaults", "read"]
    if global_domain:
        cmd.extend([f"/Library/Preferences/{domain}", key])
    else:
        cmd.extend([domain, key])
    result = run(cmd)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if value in {"1", "true", "TRUE", "YES", "yes"}:
        return True
    if value in {"0", "false", "FALSE", "NO", "no"}:
        return False
    try:
        return int(value)
    except ValueError:
        return value


def check_enterprise_policy() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key in POLICY_KEYS:
        values[key] = {
            "user": read_defaults_value(POLICY_DOMAIN, key),
            "system": read_defaults_value(POLICY_DOMAIN, key, global_domain=True),
        }
    disabled = any(values["disableAutoUpdates"].get(scope) is True for scope in ["user", "system"])
    return {"domain": POLICY_DOMAIN, "values": values, "auto_updates_disabled_by_policy": disabled}


def write_enterprise_policy() -> dict[str, Any]:
    result = run(["defaults", "write", f"/Library/Preferences/{POLICY_DOMAIN}", "disableAutoUpdates", "-bool", "true"])
    return {"status": "written" if result.returncode == 0 else "failed", "output": result.stdout.strip()}


def write_local_feature_preferences(*, dry_run: bool = False) -> dict[str, Any]:
    commands: list[list[str]] = []
    for key in LOCAL_FEATURE_BOOL_KEYS:
        commands.append(["defaults", "write", POLICY_DOMAIN, key, "-bool", "true"])
    results = []
    for cmd in commands:
        if dry_run:
            results.append({"command": cmd, "status": "would_write", "output": ""})
            continue
        result = run(cmd)
        results.append({"command": cmd, "status": "written" if result.returncode == 0 else "failed", "output": result.stdout.strip()})
    return {
        "status": "would_write" if dry_run else ("written" if all(r["status"] == "written" for r in results) else "partial"),
        "scope": "user_defaults",
        "keys": LOCAL_FEATURE_BOOL_KEYS,
        "allowedWorkspaceFolders": "left unset so Claude treats workspace folders as unrestricted unless another policy sets it",
        "results": results,
    }


def provider_expectations(provider: str) -> dict[str, Any]:
    common = {
        "local_claude_code_features": "CLAUDE.md memory, local skills, plugins, MCP, hooks, workflows, subagents and sandboxing are expected to be local-capable across providers.",
        "subscription_features": "Claude subscription features such as /schedule routines, web/mobile/Slack, Remote Control, Chrome extension, Artifacts and plan-gated Computer Use should not be assumed available in 3P mode.",
        "context_compaction": "Not probed. API compaction must be tested against the actual provider or gateway; many gateways may reject or drop context_management fields.",
    }
    matrix = {
        "bedrock": {
            "web_search": "unavailable",
            "fast_mode": "unavailable",
            "advisor": "unavailable",
            "channels": "unavailable",
            "loop": "explicit intervals only",
        },
        "vertex": {
            "web_search": "available for Claude 4+ models only",
            "fast_mode": "unavailable",
            "advisor": "unavailable",
            "channels": "unavailable",
            "loop": "explicit intervals only",
        },
        "foundry": {
            "web_search": "provider-dependent / not assumed",
            "fast_mode": "unavailable",
            "advisor": "unavailable",
            "channels": "unavailable",
            "loop": "explicit intervals only",
        },
        "aws": {
            "web_search": "available",
            "fast_mode": "unavailable",
            "advisor": "unavailable",
            "channels": "unavailable",
            "loop": "self-pacing available",
        },
        "anthropic": {
            "web_search": "available",
            "fast_mode": "available in supported Claude Code surfaces/models",
            "advisor": "available",
            "channels": "available where account plan supports it",
            "loop": "available",
        },
        "gateway": {
            "web_search": "depends on upstream provider and gateway pass-through",
            "fast_mode": "depends on upstream; usually unavailable for non-Anthropic providers",
            "advisor": "only if gateway forwards Anthropic API requests intact",
            "channels": "not assumed",
            "loop": "depends on upstream; use explicit intervals for compatibility",
        },
        "unknown": {},
    }
    return {**common, "provider": provider, "provider_specific": matrix.get(provider, matrix["unknown"])}


def app_metadata(app: Path) -> dict[str, Any]:
    info_path = app / "Contents/Info.plist"
    data: dict[str, Any] = {"path": str(app), "exists": app.exists()}
    if info_path.exists():
        with info_path.open("rb") as f:
            info = plistlib.load(f)
        data.update({
            "bundle_id": info.get("CFBundleIdentifier"),
            "short_version": info.get("CFBundleShortVersionString"),
            "bundle_version": info.get("CFBundleVersion"),
            "electron_asar_integrity": bool(info.get("ElectronAsarIntegrity")),
        })
    asar = app / APP_ASAR_REL
    if asar.exists():
        data["asar_sha256"] = sha256_file(asar)
        data["asar_size"] = asar.stat().st_size
    return data


def print_report(report: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print("Claude Desktop 3P patch report")
    print("=" * 72)
    app = report.get("app", {})
    print(f"App: {app.get('path')}")
    print(f"Version: {app.get('short_version')} ({app.get('bundle_version')})")
    print(f"Bundle ID: {app.get('bundle_id')}")
    if "asar" in report:
        asar = report["asar"]
        print(f"ASAR: {asar.get('status')}  {asar.get('sha256_before')} -> {asar.get('sha256_after')}")
        for p in asar.get("patches", []):
            status = p.get("status")
            if status in {"applied", "already_applied", "ambiguous"}:
                print(f"  {status:15} {p.get('label')} [{p.get('file')}] offsets={p.get('offsets')}")
    if "signing" in report:
        print(f"Signing: {report['signing'].get('status')}")
    if "verification" in report:
        v = report["verification"]
        print(f"codesign verify: {'OK' if v.get('codesign_ok') else 'FAILED'}")
        print(f"entitlements: {v.get('entitlements')}")
    if "policy" in report:
        print(f"Policy domain: {report['policy'].get('domain')}")
        print(f"Auto-updates disabled by policy: {report['policy'].get('auto_updates_disabled_by_policy')}")
        for key, val in report["policy"].get("values", {}).items():
            if val.get("user") is not None or val.get("system") is not None:
                print(f"  {key}: user={val.get('user')!r} system={val.get('system')!r}")
    if "local_features_write" in report:
        lf = report["local_features_write"]
        print(f"Local feature preferences: {lf.get('status')} keys={lf.get('keys')}")
    if "local_market" in report:
        lm = report["local_market"]
        print(f"Local skills/plugins report:")
        for d in lm.get("directories", []):
            print(f"  {d.get('label')}: exists={d.get('exists')} items={d.get('item_count')}")
    if "local_feature_ui" in report:
        print(f"Local feature UI patch: {report['local_feature_ui'].get('status')}")
    if "localization" in report:
        loc = report["localization"]
        print(f"Localization: {loc.get('status')} {loc.get('lang')} {loc.get('label')} user_config={loc.get('user_config')}")
        for warning in loc.get("warnings", []):
            print(f"  localization warning: {warning}")
    if "capabilities" in report:
        cap = report["capabilities"]
        print(f"Provider: {cap.get('provider')}")
        for k, v in cap.get("provider_specific", {}).items():
            print(f"  {k}: {v}")
        print(f"Context compaction: {cap.get('context_compaction')}")
    print("-" * 72)
    print("3P mode local capability notes")
    print("  - Local MCP servers: Settings -> Developer -> Local MCP (or `claude mcp add`).")
    print("  - Local skills folder: ~/.claude/skills/<skill>/SKILL.md")
    print("  - Local plugins folder: ~/.claude/plugins/")
    print("  - Local extension sideload: Settings -> Extensions -> Install from local file")
    print("  - Official plugin marketplace browse: server-gated by org subscription; not locally unlockable.")
    print("=" * 72)


# ---------------------------------------------------------------------------
# Main


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch Claude Desktop for 3P/Cowork usage and report feature readiness.")
    parser.add_argument("--app", type=Path, default=APP_DEFAULT, help="Installed Claude.app path")
    parser.add_argument("--dmg", type=Path, default=None, help="DMG containing Claude.app, e.g. Claude-0703.dmg")
    parser.add_argument("--from-dmg", action="store_true", help="Copy Claude.app from --dmg into a temporary workspace before patching")
    parser.add_argument("--workdir", type=Path, default=None, help="Temporary workspace root")
    parser.add_argument("--install", action="store_true", help="Install patched temp app to --app after verification")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and report patch matches without writing app changes")
    parser.add_argument("--check-only", action="store_true", help="Only inspect app, policy, and provider capability expectations")
    parser.add_argument("--launch", action="store_true", help="Launch Claude after successful install")
    parser.add_argument("--write-policy", action="store_true", help="Write /Library/Preferences policy to disable auto-updates")
    parser.add_argument("--feature-recovery", action="store_true", help="Enable all local feature-recovery patches and user preference writes")
    parser.add_argument("--enable-local-code-features", action="store_true", help="Write user defaults enabling local Claude Code, MCP, desktop extensions, extension directory and secure VM features")
    parser.add_argument("--local-market-report", action="store_true", help="Report local skills/plugins/extensions directories without installing remote content")
    parser.add_argument("--lang", choices=LANG_CHOICES, default=None, help="Install Chinese localization resources into the patched app")
    parser.add_argument("--zh-cn", action="store_true", help="Shortcut for --lang zh-CN")
    parser.add_argument("--user-home", type=Path, default=Path.home(), help="User home for Claude config and local skills/plugins reports")
    parser.add_argument("--provider", choices=["gateway", "anthropic", "bedrock", "vertex", "foundry", "aws", "unknown"], default="unknown")
    parser.add_argument("--report-json", type=Path, default=None, help="Write machine-readable report JSON")
    args = parser.parse_args()
    if args.zh_cn and args.lang is None:
        args.lang = "zh-CN"

    report: dict[str, Any] = {"created_at": dt.datetime.now().isoformat(timespec="seconds")}
    mounted_by_us = False
    mount: Path | None = None

    try:
        if args.from_dmg or args.dmg:
            dmg = args.dmg or DEFAULT_DMG
            mount, mounted_by_us = mount_dmg(dmg)
            source_app = mount / "Claude.app"
            workdir = args.workdir or Path(tempfile.mkdtemp(prefix="claude-3p-v2."))
            workdir.mkdir(parents=True, exist_ok=True)
            target_app = workdir / "Claude.app"
            if not args.check_only:
                print(f"Copying {source_app} -> {target_app}")
                copy_app(source_app, target_app)
            else:
                target_app = source_app
        else:
            target_app = args.app

        report["app"] = app_metadata(target_app)
        report["policy"] = check_enterprise_policy()
        report["capabilities"] = provider_expectations(args.provider)

        if args.local_market_report or args.feature_recovery:
            report["local_market"] = local_market_report(args.user_home)

        if args.enable_local_code_features or args.feature_recovery:
            prefs_dry_run = args.dry_run or args.check_only or ((args.from_dmg or args.dmg) and not args.install)
            report["local_features_write"] = write_local_feature_preferences(dry_run=prefs_dry_run)
            report["policy"] = check_enterprise_policy()

        if args.write_policy:
            report["policy_write"] = write_enterprise_policy()
            report["policy"] = check_enterprise_policy()

        if not args.check_only:
            if not args.dry_run:
                quit_claude()
            report["asar"] = patch_asar(target_app, dry_run=args.dry_run)
            if args.feature_recovery:
                report["local_feature_ui"] = patch_local_feature_ui(target_app, dry_run=args.dry_run)
            if args.lang:
                report["localization"] = apply_localization(target_app, args.lang, args.user_home, dry_run=args.dry_run, set_user_config=args.install)
            report["app"] = app_metadata(target_app)
            if not args.dry_run:
                report["signing"] = resign_app(target_app)
            else:
                report["signing"] = {"status": "skipped_dry_run"}
        report["verification"] = verify_app(target_app) if target_app.exists() else {"codesign_ok": False}

        if args.install and not args.check_only and not args.dry_run:
            if report["verification"].get("codesign_ok") is not True:
                raise SystemExit("Refusing to install because codesign verification failed")
            backup = backup_and_install(target_app, args.app)
            report["install"] = {"status": "installed", "target": str(args.app), "backup": str(backup)}
            if args.launch:
                run(["open", "-a", str(args.app)])
        elif (args.from_dmg or args.dmg) and not args.install:
            report["install"] = {"status": "not_installed", "patched_app": str(target_app)}

        print_report(report)
        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Report JSON written to: {args.report_json}")
        return 0
    finally:
        if mounted_by_us and mount is not None:
            detach_dmg(mount)


if __name__ == "__main__":
    raise SystemExit(main())
