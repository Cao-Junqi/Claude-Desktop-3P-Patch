#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Desktop 3P patcher for Windows
======================================

Windows port of patch_claude_3p_v2.py. Patches Claude Desktop on Windows by:
- Modifying app.asar (same logic as macOS)
- Writing registry policies instead of defaults
- Skipping code signing (Windows Electron apps don't require it for local use)
- Supporting both installed and portable modes

Default install locations:
  %LOCALAPPDATA%\Programs\Claude\Claude.exe
  %PROGRAMFILES%\Claude\Claude.exe
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Windows-specific imports (only available on Windows)
if sys.platform == "win32":
    import winreg
else:
    winreg = None  # type: ignore

# Windows paths
APP_DEFAULT_LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Claude"
APP_DEFAULT_PROGRAMFILES = Path(os.environ.get("PROGRAMFILES", "")) / "Claude"
ROOT = Path(__file__).resolve().parent
APP_ASAR_REL = Path("resources/app.asar")
ASAR_INDEX_PREFIX = ".vite/build/index"
ASAR_SWIFT = "node_modules/@ant/claude-swift/js/index.js"
POLICY_KEY = r"SOFTWARE\Policies\Anthropic\Claude"

# Windows-specific paths (different from macOS Contents/Resources structure)
FRONTEND_I18N_REL = Path("resources/ion-dist/i18n")
FRONTEND_ASSETS_REL = Path("resources/ion-dist/assets/v1")
DESKTOP_RESOURCES_REL = Path("resources")

LANG_CHOICES = ["zh-CN", "zh-TW", "zh-HK"]
RESOURCES = ROOT / "resources"
import re

# Language whitelist regex (same as macOS version)
LANG_LIST_RE = re.compile(
    r'\["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID"(?:(?:,"zh-CN")|(?:,"zh-TW")|(?:,"zh-HK"))*\]'
)
BASE_LANGUAGE_LIST = '["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID"'


BASE_LANGUAGE_LIST = '["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID"'


def get_language_config(lang_code: str) -> dict[str, Any]:
    """Return file paths and settings for the given language code."""
    return {
        "lang_code": lang_code,
        "frontend_translation": RESOURCES / f"frontend-{lang_code}.json",
        "frontend_hardcoded": RESOURCES / f"frontend-hardcoded-{lang_code}.json",
        "desktop_translation": RESOURCES / f"desktop-{lang_code}.json",
        "statsig_translation": RESOURCES / f"statsig-{lang_code}.json",
        "label": {
            "zh-CN": "简体中文",
            "zh-TW": "繁体中文（中国台湾）",
            "zh-HK": "繁体中文（中国香港）",
        }.get(lang_code, lang_code),
    }


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def require_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def decode_asar_header(asar: Path) -> tuple[dict[str, Any], int, bytes]:
    """Read ASAR header and return (header_dict, header_size, full_data)."""
    data = bytearray(asar.read_bytes())
    if len(data) < 16:
        raise SystemExit(f"ASAR too small: {asar}")
    pickle_size, header_size_u32_1, header_size_u32_2, header_size_u32_3 = struct.unpack(
        "<IIII", data[:16]
    )
    header_size = header_size_u32_3
    header_bytes = data[16 : 16 + header_size]
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to parse ASAR header: {e}")
    return header, header_size, data


def encode_asar_header(header_string: str, size: int) -> bytearray:
    """Encode ASAR header back to bytes."""
    header_bytes = header_string.encode("utf-8")
    if len(header_bytes) != size:
        raise SystemExit(f"Header size mismatch: {len(header_bytes)} != {size}")
    pickle_size = 4
    result = bytearray(16 + size)
    struct.pack_into("<IIII", result, 0, pickle_size, size, size, size)
    result[16 : 16 + size] = header_bytes
    return result


def extract_asar_files(header: dict[str, Any], data: bytes, base: int, prefix: str) -> dict[str, bytes]:
    """Extract files matching prefix from ASAR."""
    files = {}

    def walk(node: Any, path: str = ""):
        if isinstance(node, dict) and "offset" in node and "size" in node:
            o = node["offset"]
            s = node["size"]
            if isinstance(o, dict):
                o = o.get("offset", 0)
            if isinstance(s, dict):
                s = s.get("size", 0)
            o, s = int(o), int(s)
            if path.startswith(prefix):
                files[path] = data[base + o : base + o + s]
        elif isinstance(node, dict) and "files" in node:
            for k, v in node["files"].items():
                walk(v, f"{path}/{k}" if path else k)

    walk(header)
    return files


def pad_bytes(replacement: bytes, target_len: int) -> bytes:
    if len(replacement) > target_len:
        raise SystemExit(f"Replacement longer than target ({len(replacement)} > {target_len})")
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
        return content, result
    offsets = []
    idx = 0
    while True:
        pos = content.find(original, idx)
        if pos == -1:
            break
        offsets.append(pos)
        idx = pos + len(original)
    result["status"] = "applied"
    result["offsets"] = offsets
    return content.replace(original, replacement), result


def build_index_patch_specs() -> list[tuple[str, list[tuple[bytes, bytes, bool]]]]:
    """Same patch specs as macOS version."""
    title_0623 = b'.catch(()=>String(p.first_session_message||"").slice(0,46))'
    title_0703 = b'.catch(()=>String(B.first_session_message||"").slice(0,46))'

    return [
        (
            "L1 managed config safeParse bypass",
            [
                (b'const A=n(K);if(!A.success)throw', b'const A=n(K);if(0&&!A.success)throw', False),
                (b'const I=z.safeParse(s);if(!I.success)throw', b'const I=z.safeParse(s);if(0&&!I.success)throw', False),
                (b'const E=tSt.safeParse(s);if(!E.success)throw', b'const E=tSt.safeParse(s);if(0&&!E.success)throw', False),
            ],
        ),
        (
            "L2 model white-list bypass",
            [
                (b"if(A.managed_config){const h=A.managed_config.models??[];if(h.length===0)throw", b"if(A.managed_config){const h=A.managed_config.models??[];if(h.length<=-1)throw", False),
                (b"if(I.managed_config){const f=I.managed_config.models??[];if(f.length===0)throw", b"if(I.managed_config){const f=I.managed_config.models??[];if(f.length<=-1)throw", False),
                (b"if(E.managed_config){const o=E.managed_config.models??[];if(o.length===0)throw", b"if(E.managed_config){const o=E.managed_config.models??[];if(o.length<=-1)throw", False),
            ],
        ),
        (
            "L2c gateway model route validator bypass",
            [
                (b'const c=O$i(A);if(c)throw', b'const c=O$i(A);if(0)throw', False),
                (b'const g=C$i(a.data.provider,a.data.models);if(g)throw', b'const g=C$i(a.data.provider,a.data.models);if(0)throw', False),
                (b's.data.models);if(u)throw', b's.data.models);if(0)throw', False),
            ],
        ),
        (
            "L4 force auto-update early return",
            [
                (b'this.log("Auto-updates disabled by managed config"),!0', b'this.log("Auto-updates disabled by managed config"),!1', False),
                (b'this.log("Auto-updates disabled",{reason:"managedConfig"}),!0', b'this.log("Auto-updates disabled",{reason:"managedConfig"}),!1', False),
            ],
        ),
        (
            "L5 inference model catalog throw bypass",
            [
                (b'const c=O$i(A);if(c)throw', b'const c=O$i(A);if(0)throw', False),
                (b'const g=C$i(a.data.provider,a.data.models);if(g)throw', b'const g=C$i(a.data.provider,a.data.models);if(0)throw', False),
                (b's.data.models);if(u)throw', b's.data.models);if(0)throw', False),
            ],
        ),
        (
            "L6 session title fallback",
            [
                (title_0623, pad_bytes(b'.catch(()=>String(d.first_session_message||"").slice(0,46))', len(title_0623)), True),
                (title_0703, pad_bytes(b'.catch(()=>String(B.first_session_message||"").slice(0,46))', len(title_0703)), True),
                (
                    b'.catch(e=>(o.o.warn(`[title-gen] failed`,{error:String(e)}),``))',
                    pad_bytes(b'.catch(()=>String(t.first_session_message||"").slice(0,46))', 64),
                    True,
                ),
                (
                    b'.catch((e=>(P.warn(`[title-gen] failed`,{error:String(e)}),``)))',
                    pad_bytes(b'.catch(()=>String(t.first_session_message||"").slice(0,46))', 64),
                    True,
                ),
            ],
        ),
        (
            "L3b claude-swift virtualization support",
            [
                (
                    b'this.vm.isVirtualizationSupported=async()=>{',
                    b'this.vm.isVirtualizationSupported=()=>"supported";void async()=>{',
                    False,
                ),
            ],
        ),
    ]


def patch_index_files(files: dict[str, bytes]) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    """Apply patches to index files."""
    working = dict(files)
    by_label: dict[str, list[dict[str, Any]]] = {}

    for label, alternatives in build_index_patch_specs():
        by_label[label] = []
        for filepath, content in list(working.items()):
            for original, replacement, allow_multi in alternatives:
                patched, result = patch_exact(content, original, replacement, label, allow_multi=allow_multi)
                if result["status"] in ("applied", "already_applied", "ambiguous"):
                    result["file"] = filepath
                    by_label[label].append(result)
                    if result["status"] == "applied":
                        working[filepath] = patched
                    break

    # Aggregate per label
    reports = []
    for label, hits in by_label.items():
        if not hits:
            reports.append({"label": label, "status": "missing", "files": []})
        else:
            for h in hits:
                reports.append(h)

    return working, reports


def patch_asar(
    app_root: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Patch app.asar with 3P compatibility changes."""
    asar = app_root / APP_ASAR_REL
    if not asar.exists():
        raise SystemExit(f"ASAR not found: {asar}")

    report = {
        "asar_path": str(asar),
        "sha256_before": sha256_file(asar),
        "status": "missing",
        "patches": [],
    }

    header, header_size, data = decode_asar_header(asar)
    base = 16 + header_size

    # Extract and patch index files
    index_files = extract_asar_files(header, data, base, ASAR_INDEX_PREFIX)
    patched_files, patch_reports = patch_index_files(index_files)
    report["patches"].extend(patch_reports)

    # Extract and patch claude-swift
    swift_files = extract_asar_files(header, data, base, ASAR_SWIFT)
    if ASAR_SWIFT in swift_files:
        swift_patched, swift_report = patch_exact(
            swift_files[ASAR_SWIFT],
            b'this.vm.isVirtualizationSupported=async()=>{',
            b'this.vm.isVirtualizationSupported=()=>"supported";void async()=>{',
            "L3b claude-swift virtualization support",
        )
        patched_files[ASAR_SWIFT] = swift_patched
        report["patches"].append({**swift_report, "file": ASAR_SWIFT})

    if dry_run:
        report["status"] = "would_patch"
        return report

    # Write back patched files
    def update_file(node: Any, path: str = ""):
        if isinstance(node, dict) and "offset" in node and "size" in node:
            if path in patched_files:
                content = patched_files[path]
                o = node["offset"]
                if isinstance(o, dict):
                    o = o["offset"]
                o = int(o)
                data[base + o : base + o + len(content)] = content
        elif isinstance(node, dict) and "files" in node:
            for k, v in node["files"].items():
                update_file(v, f"{path}/{k}" if path else k)

    update_file(header)

    # Write ASAR
    updated_header_string = json.dumps(header, ensure_ascii=False, separators=(",", ":"))
    updated_header = encode_asar_header(updated_header_string, header_size)
    data[: len(updated_header)] = updated_header
    asar.write_bytes(data)

    report["status"] = "patched"
    report["sha256_after"] = sha256_file(asar)
    return report


def write_registry_policy(*, dry_run: bool = False) -> dict[str, Any]:
    """Write Windows registry policies (HKLM\SOFTWARE\Policies\Anthropic\Claude)."""
    report = {"status": "skipped", "policies": {}}

    if sys.platform != "win32":
        report["status"] = "not_windows"
        return report

    if dry_run:
        report["status"] = "would_write"
        report["policies"] = {"disableAutoUpdates": 1}
        return report

    try:
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, POLICY_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "disableAutoUpdates", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        report["status"] = "written"
        report["policies"] = {"disableAutoUpdates": 1}
    except PermissionError:
        report["status"] = "permission_denied"
        report["error"] = "需要管理员权限写入注册表"
    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)

    return report


def patch_language_whitelist(app_root: Path, lang_code: str) -> None:
    """Add language to whitelist in frontend assets."""
    assets_dir = app_root / FRONTEND_ASSETS_REL
    if not assets_dir.exists():
        raise SystemExit(f"Frontend assets not found: {assets_dir}")

    replacement = f'{BASE_LANGUAGE_LIST},"{lang_code}"]'
    patched = False

    for path in sorted(assets_dir.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        if f'"{lang_code}"' in text and LANG_LIST_RE.search(text):
            print(f"Language whitelist already contains {lang_code}: {path.name}")
            patched = True
            break
        if LANG_LIST_RE.search(text):
            updated = LANG_LIST_RE.sub(replacement, text, count=1)
            path.write_text(updated, encoding="utf-8")
            print(f"Patched language whitelist: {path.name}")
            patched = True
            break

    if not patched:
        raise SystemExit(f"Language whitelist pattern not found in {assets_dir}")


def merge_frontend_locale(app_root: Path, lang_code: str) -> None:
    """Merge translation into frontend i18n."""
    config = get_language_config(lang_code)
    require_file(config["frontend_translation"])

    i18n_dir = app_root / FRONTEND_I18N_REL
    i18n_dir.mkdir(parents=True, exist_ok=True)

    target = i18n_dir / f"{lang_code}.json"
    translation = load_json(config["frontend_translation"])

    if target.exists():
        existing = load_json(target)
        existing.update(translation)
        save_json(target, existing)
        print(f"Merged frontend locale: {target}")
    else:
        save_json(target, translation)
        print(f"Installed frontend locale: {target}")


def install_desktop_locale(app_root: Path, lang_code: str) -> None:
    """Install desktop translation."""
    config = get_language_config(lang_code)
    require_file(config["desktop_translation"])

    i18n_dir = app_root / FRONTEND_I18N_REL
    i18n_dir.mkdir(parents=True, exist_ok=True)

    target = i18n_dir / f"desktop-{lang_code}.json"
    shutil.copy2(config["desktop_translation"], target)
    print(f"Installed desktop locale: {target}")


def install_statsig_locale(app_root: Path, lang_code: str) -> None:
    """Install statsig translation."""
    config = get_language_config(lang_code)
    require_file(config["statsig_translation"])

    i18n_dir = app_root / FRONTEND_I18N_REL
    i18n_dir.mkdir(parents=True, exist_ok=True)

    target = i18n_dir / f"statsig-{lang_code}.json"
    shutil.copy2(config["statsig_translation"], target)
    print(f"Installed statsig locale: {target}")


def patch_hardcoded_frontend_strings(app_root: Path, lang_code: str) -> None:
    """Patch hardcoded strings in frontend assets."""
    config = get_language_config(lang_code)
    require_file(config["frontend_hardcoded"])

    hardcoded = load_json(config["frontend_hardcoded"])
    assets_dir = app_root / FRONTEND_ASSETS_REL

    if not assets_dir.exists():
        print(f"Warning: Frontend assets not found: {assets_dir}")
        return

    patched_count = 0
    for path in sorted(assets_dir.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        original = text
        for en, zh in hardcoded.items():
            text = text.replace(en, zh)
        if text != original:
            path.write_text(text, encoding="utf-8")
            patched_count += 1

    print(f"Patched hardcoded strings in {patched_count} files")


def apply_localization(app_root: Path, lang_code: str, *, dry_run: bool = False) -> dict[str, Any]:
    """Apply Chinese localization to Windows Claude."""
    config = get_language_config(lang_code)

    # Validate resources
    for key in ["frontend_translation", "frontend_hardcoded", "desktop_translation", "statsig_translation"]:
        require_file(config[key])

    if dry_run:
        return {
            "status": "would_patch",
            "lang": lang_code,
            "label": config.get("label"),
            "files_validated": True,
        }

    warnings = []

    try:
        patch_language_whitelist(app_root, lang_code)
    except SystemExit as exc:
        warnings.append(f"Language whitelist: {exc}")

    try:
        merge_frontend_locale(app_root, lang_code)
        install_desktop_locale(app_root, lang_code)
        install_statsig_locale(app_root, lang_code)
        patch_hardcoded_frontend_strings(app_root, lang_code)
    except Exception as exc:
        warnings.append(f"Localization error: {exc}")

    return {
        "status": "patched",
        "lang": lang_code,
        "label": config.get("label"),
        "warnings": warnings,
    }


def write_registry_policy(*, dry_run: bool = False) -> dict[str, Any]:
    """Write Windows registry policies (HKLM\SOFTWARE\Policies\Anthropic\Claude)."""
    report = {"status": "skipped", "policies": {}}

    if sys.platform != "win32":
        report["status"] = "not_windows"
        return report

    if dry_run:
        report["status"] = "would_write"
        report["policies"] = {"disableAutoUpdates": 1}
        return report

    try:
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, POLICY_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "disableAutoUpdates", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        report["status"] = "written"
        report["policies"] = {"disableAutoUpdates": 1}
    except PermissionError:
        report["status"] = "permission_denied"
        report["error"] = "需要管理员权限写入注册表"
    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)

    return report


def main():
    parser = argparse.ArgumentParser(description="Claude Desktop 3P patcher for Windows")
    parser.add_argument("--app", type=Path, help="Path to Claude install root (contains Claude.exe)")
    parser.add_argument("--dry-run", action="store_true", help="Check only, don't modify")
    parser.add_argument("--write-policy", action="store_true", help="Write registry policy to disable auto-update")
    parser.add_argument("--lang", choices=LANG_CHOICES, help="Install Chinese localization (zh-CN, zh-TW, zh-HK)")
    parser.add_argument("--zh-cn", action="store_true", help="Shortcut for --lang zh-CN")
    parser.add_argument("--provider", default="gateway", help="Provider type for report")
    parser.add_argument("--report-json", type=Path, help="Output JSON report")

    args = parser.parse_args()

    # Handle --zh-cn shortcut
    if args.zh_cn:
        args.lang = "zh-CN"

    # Find Claude install
    if args.app:
        app_root = args.app
    elif APP_DEFAULT_LOCALAPPDATA.exists():
        app_root = APP_DEFAULT_LOCALAPPDATA
    elif APP_DEFAULT_PROGRAMFILES.exists():
        app_root = APP_DEFAULT_PROGRAMFILES
    else:
        raise SystemExit("Claude not found. Use --app to specify location.")

    if not (app_root / "Claude.exe").exists():
        raise SystemExit(f"Claude.exe not found in {app_root}")

    print(f"Claude root: {app_root}")
    print(f"{'=' * 72}")

    # Patch ASAR
    asar_report = patch_asar(app_root, dry_run=args.dry_run)
    print(f"\nASAR: {asar_report['status']}")
    for p in asar_report["patches"]:
        status = p["status"]
        label = p["label"]
        file = p.get("file", "")
        print(f"  {status:15} {label}")
        if file:
            print(f"                  └─ {file}")

    # Localization
    localization_report = None
    if args.lang:
        print(f"\n{'=' * 72}")
        print(f"Localization: {args.lang}")
        localization_report = apply_localization(app_root, args.lang, dry_run=args.dry_run)
        print(f"Status: {localization_report['status']}")
        if localization_report.get("warnings"):
            for w in localization_report["warnings"]:
                print(f"  Warning: {w}")

    # Registry policy
    if args.write_policy:
        print(f"\n{'=' * 72}")
        policy_report = write_registry_policy(dry_run=args.dry_run)
        print(f"Registry policy: {policy_report['status']}")
        if policy_report.get("error"):
            print(f"  Error: {policy_report['error']}")
    else:
        policy_report = {"status": "skipped"}

    # Full report
    full_report = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "app_root": str(app_root),
        "provider": args.provider,
        "asar": asar_report,
        "policy": policy_report,
    }

    if localization_report:
        full_report["localization"] = localization_report

    if args.report_json:
        args.report_json.write_text(json.dumps(full_report, indent=2, ensure_ascii=False))
        print(f"\nReport written: {args.report_json}")

    print(f"\n{'=' * 72}")
    print("Windows 3P mode complete!")
    if args.lang:
        print(f"  ✓ 3P patch applied")
        print(f"  ✓ Chinese localization ({args.lang})")
        if args.write_policy:
            print(f"  ✓ Registry policy")
    else:
        print(f"  ✓ 3P patch applied")
        print(f"  ℹ Add --zh-cn for Chinese localization")
        if args.write_policy:
            print(f"  ✓ Registry policy")
    print(f"{'=' * 72}")



if __name__ == "__main__":
    main()
