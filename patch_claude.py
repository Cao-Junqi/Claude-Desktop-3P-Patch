#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Desktop 终极修补工具 (0623 适配版 v6)
=============================================
针对 Claude Desktop 0623 版本 (app.asar ~35.7 MB) 的多层防御逐一破解。

兼容版本：
- 0623 (2026-06-23) — 当前主适配目标
- 0604 (2026-06-04) — 仍可工作（特征码已覆盖老变量名）

破解的 11 处防御：
  1. L1   3P enterprise config 抛错校验 (safeParse) — 伪造成功对象
  2. L2   PVt 白名单过滤（e.length===0）— 放行非 claude- 模型
  3. L2b  PVt.some 终态过滤 — 让所有 model 都过
  4. L2c  v4i gateway 校验（PX/HCt/YCt）— 禁用 catalog 白名单
  5. L3b  claude-swift isVirtualizationSupported — 劫持虚拟化
  6. L4   D$t / _$t disableAutoUpdates 早期返回 — 屏蔽自动更新
  7. L5a  O$i inferenceModels catalog 校验 — 短路 throw
  8. L5b  C$i provider/models 校验 — 短路 throw
  9. L6   session title 兜底 (本地占位) — minimax-m3 spawn 失败时 fallback
  10. L7  qUA effort 校验禁用 xhigh — 3P 模型不让 xhigh 透传
  11. +  ASAR 4MB 分块 SHA-256 完整性 + macOS 重签名

特征码说明（0623 实测偏移）：
  L1     主进程: const a=b$i.safeParse(s);                       (6486487)
  L2/L2b 主进程: function PVt(A,e){...}                          (12400483)
  L2c    主进程: function v4i(A){return PX(A)?{ok:!0}            (6306574)
  L3b    claude-swift/js/index.js 注释行（"// ComputerUse bindings ..."）
  L4a    主进程: D$t 中 if(A.disableAutoUpdates){...;return}      (12637330)
  L4b    主进程: _$t 中 if(fi().disableAutoUpdates){...;return}    (12642170)
  L5a    主进程: const c=O$i(A);if(c)throw                        (6486883)
  L5b    主进程: const g=C$i(a.data.provider,a.data.models);if(g)throw
  L6     主进程: .catch(Q=>(D.warn("[title-gen] failed",...))      (12615268)
  L7     主进程: function qUA(A){return A!=null&&wQr.has(A)        (7963703)
"""

import os
import shutil
import struct
import json
import subprocess
import plistlib
import hashlib
import glob
import re
import sys

APP_PATH = os.environ.get("CLAUDE_APP_PATH", "/Applications/Claude.app")
ASAR_PATH = os.path.join(APP_PATH, "Contents/Resources/app.asar")
BACKUP_PATH = ASAR_PATH + ".bak"
PLIST_PATH = os.path.join(APP_PATH, "Contents/Info.plist")
ENTITLEMENTS_PATH = "/tmp/claude_entitlements.plist"

# 默认 Entitlements（DMG 提取失败时回退用）
DEFAULT_ENTITLEMENTS = {
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

# 会被清洗掉的受限字段（不能脱离原 TeamID 使用）
RESTRICTED_KEYS = [
    "com.apple.application-identifier",
    "com.apple.developer.team-identifier",
    "keychain-access-groups",
    "com.apple.developer.associated-domains",
    "com.apple.developer.default-data-protection",
]


# ---------------------------- 工具函数 ----------------------------

def calc_integrity(file_data, block_size=4194304):
    """复刻 Electron 的 4MB 分块 SHA-256 完整性算法"""
    blocks = []
    for i in range(0, len(file_data), block_size):
        chunk = file_data[i:i + block_size]
        blocks.append(hashlib.sha256(chunk).hexdigest())
    full_hash = hashlib.sha256(file_data).hexdigest()
    return {
        "algorithm": "SHA256",
        "hash": full_hash,
        "blockSize": block_size,
        "blocks": blocks,
    }


def find_dmg_mount():
    """动态寻找挂载的 Claude DMG 挂载点（不写死 Claude0604 / Claude）。"""
    candidates = glob.glob("/Volumes/Claude*")
    candidates = [c for c in candidates if os.path.isdir(os.path.join(c, "Claude.app"))]
    if not candidates:
        return None
    # 优先选含 Claude.app/Contents/Resources/app.asar 的
    for c in candidates:
        if os.path.isfile(os.path.join(c, "Claude.app/Contents/Resources/app.asar")):
            return c
    return candidates[0]


def patch_bytes(haystack, original, replacement, *, allow_zero=False, label=""):
    """在 haystack 中把 original 替换为 replacement，命中数必须 == 1。"""
    count = haystack.count(original)
    if count == 0:
        if allow_zero:
            print(f"   ↪︎ [skip] {label or 'pattern'} 未命中 (0 处)，跳过")
            return haystack
        raise RuntimeError(
            f"特征码未命中: {label or original[:60]!r}\n"
            f"  长度: {len(original)} 字节\n"
            f"  这通常意味着 Claude Desktop 已更新到未兼容的版本。"
        )
    if count > 1:
        # 多处命中只 patch 第一处，避免误伤同名变量
        print(f"   ⚠️  [warn] {label or 'pattern'} 命中 {count} 处，仅替换第 1 处")
        idx = haystack.find(original)
        return haystack[:idx] + replacement + haystack[idx + len(original):]
    return haystack.replace(original, replacement)


# ---------------------------- 核心 Patch ----------------------------

def patch_index_js(data, header, base_offset):
    """对主进程 index.js 应用 11 处特征码 patch。返回 (data, applied_count, applied_names)"""
    index_node = header["files"][".vite"]["files"]["build"]["files"]["index.js"]
    idx_offset = base_offset + int(index_node["offset"])
    idx_size = int(index_node["size"])
    idx = bytearray(data[idx_offset:idx_offset + idx_size])

    applied = []

    # Layer 1: 3P enterprise config 抛错校验
    # 新版: const a=b$i.safeParse(s);
    # 老版: const l=Ewi.safeParse(E);
    for orig, repl, label in [
        (b'const a=b$i.safeParse(s);', b'var a={data:s,success:1};', "L1 new safeParse"),
        (b'const l=Ewi.safeParse(E);', b'var l={data:E,success:1};', "L1 old safeParse"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # Layer 2: PVt 白名单过滤（用长特征码避免误伤其他库里的 e.length===0）
    # 0623 新版:
    #   if(A.startsWith("claude-"))return!0;if(e.length===0)return!1;
    # 0604 老版:
    #   if(e.startsWith("claude-"))return!0;if(A.length===0)return!1;
    # 等长 patch：把 return!1 改成 return!0，让 e 为空时也放行（绕过白名单）
    for orig, repl, label in [
        (b'if(A.startsWith("claude-"))return!0;if(e.length===0)return!1;',
         b'if(A.startsWith("claude-"))return!0;if(e.length===0)return!0;',
         "L2 PVt new (claude- + e.length===0)"),
        (b'if(e.startsWith("claude-"))return!0;if(A.length===0)return!1;',
         b'if(e.startsWith("claude-"))return!0;if(A.length===0)return!0;',
         "L2 PVt legacy (e.startsWith + A.length===0)"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # Layer 2b: PVt.some 终态过滤（让所有 model 都过 PVt 校验）
    # 0623 PVt 最后一行: return e.some(i=>i===A||$d(i)===t)
    # 改成: return e.some(i=>!0);  (callback 永远 true)
    for orig, repl, label in [
        (b'return e.some(i=>i===A||$d(i)===t)}',
         b'return e.some(i=>!0);/*padpadpad*/}',
         "L2b PVt.some 永远 true (e.some callback !0)"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # Layer 2c: v4i gateway provider 校验（mcr.filter(n=>YX(provider,n.id).ok) → v4i → PX）
    # PX 会拒绝 non-anthropic 模型（gpt/gemini/doubao/kimi 等黑名单 + claude-/anthropic/sonnet 白名单）
    # v4i 是 gateway/mantle provider 的入口；直接短路成永远 ok
    # 36 字节等长: function v4i(A){return PX(A)?{ok:!0}  →  function v4i(A){return 1!==0?{ok:!0}
    for orig, repl, label in [
        (b'function v4i(A){return PX(A)?{ok:!0}',
         b'function v4i(A){return 1!==0?{ok:!0}',
         "L2c v4i gateway 永远 ok (PX 短路)"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # Layer 4: 关闭 D$t / _$t 中的自动更新检查
    # 新版 D$t: if(A.disableAutoUpdates){D.info("[updater] Auto-updates disabled by enterprise policy"),Ye("desktop_update_disabled",{reason:"enterprise_policy"});return}
    #   → 改为 if(0){...} 即可短路（保持等长）
    # 新版 _$t: if(fi().disableAutoUpdates){D.info("[updater] Auto-updates disabled by enterprise policy");return}
    #   → 改为 if(0&&fi().disableAutoUpda){...} 保持等长
    for orig, repl, label in [
        (b'if(A.disableAutoUpdates){D.info("[updater] Auto-updates disabled by enterprise policy"),Ye("desktop_update_disabled",{reason:"enterprise_policy"});return}',
         b'if(0&&A.disableAutoUpda){D.info("[updater] Auto-updates disabled by enterprise policy"),Ye("desktop_update_disabled",{reason:"enterprise_policy"});return}',
         "L4 D$t disableAutoUpdates"),
        (b'if(fi().disableAutoUpdates){D.info("[updater] Auto-updates disabled by enterprise policy");return}',
         b'if(0&&fi().disableAutoUpda){D.info("[updater] Auto-updates disabled by enterprise policy");return}',
         "L4 _$t disableAutoUpdates"),
        # 兼容老版（0604）写法
        (b'if(e.disableAutoUpdates)',
         b'if(0&&e.disableAutoU)',
         "L4 legacy if(e.disableAutoUpdates)"),
        (b'if(ki().disableAutoUpdates)',
         b'if(0&&ki().disableAutoU)',
         "L4 legacy if(ki().disableAutoUpdates)"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # Layer 5: 3P enterprise config 二次校验（inferenceModels / provider/models 列表）
    # 0623 L5a: const c=O$i(A);if(c)throw →  const c=O$i(A);if(0)throw
    # 0623 L5b: const g=C$i(a.data.provider,a.data.models);if(g)throw →  const g=C$i(a.data.provider,a.data.models);if(0)throw
    for orig, repl, label in [
        (b'const c=O$i(A);if(c)throw',
         b'const c=O$i(A);if(0)throw',
         "L5a O$i inferenceModels catalog 校验短路"),
        (b'const g=C$i(a.data.provider,a.data.models);if(g)throw',
         b'const g=C$i(a.data.provider,a.data.models);if(0)throw',
         "L5b C$i provider/models 列表校验短路"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # Layer 6: session title 兜底（minimax-m3 spawn 失败时本地占位）
    # 0623 _6e 函数 spawn minimax-m3 跑 title 生成，3P 配置下会失败
    # patch .catch fallback: 失败时返回 d.first_session_message 前 46 字符
    # 62 字节等长: .catch(Q=>(D.warn("[title-gen] failed",{error:String(Q)}),""))
    #            → .catch(()=>d.first_session_message.slice(0,46)/*aaaaaaaaaaa*/)
    # 命中 2 处: generate_session_title + generate_title_and_branch
    for orig, repl, label in [
        (b'.catch(Q=>(D.warn("[title-gen] failed",{error:String(Q)}),""))',
         b'.catch(()=>d.first_session_message.slice(0,46)/*aaaaaaaaaaa*/)',
         "L6 title fallback (first 46 chars)"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # Layer 7: 禁用 xhigh effort (3P 模型不识别 xhigh，minimax-m3 期望 low/medium/high/max)
    # qUA 是 effortByModel 字典值校验函数，原版用 wQr（含 xhigh）放行 xhigh
    # 改成用 mQr（只 low/medium/high/max），xhigh 被拒绝 → effort 字段不发
    # 52 字节等长: function qUA(A){return A!=null&&wQr.has(A)?A:void 0}
    #            → function qUA(A){return A!=null&&mQr.has(A)?A:void 0}
    for orig, repl, label in [
        (b'function qUA(A){return A!=null&&wQr.has(A)?A:void 0}',
         b'function qUA(A){return A!=null&&mQr.has(A)?A:void 0}',
         "L7 qUA 禁用 xhigh (wQr→mQr)"),
    ]:
        if orig in idx:
            idx = patch_bytes(idx, orig, repl, label=label)
            applied.append(label)

    # 写回 index.js 段
    data[idx_offset:idx_offset + idx_size] = idx
    if "integrity" in index_node:
        index_node["integrity"] = calc_integrity(bytes(idx))

    return data, applied


def patch_claude_swift(data, header, base_offset):
    """对 @ant/claude-swift/js/index.js 劫持 isVirtualizationSupported。"""
    try:
        swift_node = (header["files"]["node_modules"]["files"]["@ant"]
                      ["files"]["claude-swift"]["files"]["js"]["files"]["index.js"])
    except KeyError:
        print("   ↪︎ [skip] @ant/claude-swift/js/index.js 不存在，跳过 L3b")
        return data, []

    sw_offset = base_offset + int(swift_node["offset"])
    sw_size = int(swift_node["size"])
    sw = bytearray(data[sw_offset:sw_offset + sw_size])

    # 0623 / 0604 共有特征码：注释行 + 缩进
    orig = b'    // ComputerUse bindings live in a separate SPM product (ComputerUseSwift)\n'
    repl = b'    this.vm.isVirtualizationSupported = () => "supported";                   \n'

    if orig not in sw:
        print("   ↪︎ [skip] claude-swift 注释行未命中，跳过 L3b")
        return data, []

    sw = patch_bytes(sw, orig, repl, label="L3b claude-swift isVirtualizationSupported")
    data[sw_offset:sw_offset + sw_size] = sw
    if "integrity" in swift_node:
        swift_node["integrity"] = calc_integrity(bytes(sw))
    return data, ["L3b claude-swift hijack"]


def patch_asar():
    """主入口：解析 asar header，逐个 patch 文件，重算 integrity。"""
    if not os.path.exists(BACKUP_PATH):
        print("📦 首次运行，创建 app.asar 备份...")
        shutil.copy2(ASAR_PATH, BACKUP_PATH)

    with open(BACKUP_PATH, "rb") as f:
        data = bytearray(f.read())

    header_size = struct.unpack("<I", data[4:8])[0]
    header_json_size = struct.unpack("<I", data[12:16])[0]
    header_json_str = data[16:16 + header_json_size].decode("utf-8")
    header = json.loads(header_json_str)
    base_offset = 8 + header_size

    all_applied = []

    print("\n🩹 [Layer 1~7] 修补主进程 index.js ...")
    data, applied = patch_index_js(data, header, base_offset)
    all_applied.extend(applied)
    for name in applied:
        print(f"   ✅ {name}")

    print("\n🩹 [Layer 3b] 修补 @ant/claude-swift ...")
    data, applied = patch_claude_swift(data, header, base_offset)
    all_applied.extend(applied)
    for name in applied:
        print(f"   ✅ {name}")

    if not all_applied:
        raise RuntimeError("没有命中任何特征码 — 此 app.asar 可能不是 0604 / 0623，请检查版本")

    # 重写 header JSON
    new_json = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(new_json) > header_json_size:
        raise RuntimeError(
            f"header JSON 超长 {len(new_json)} > {header_json_size}，asar 结构不安全"
        )
    new_json += b" " * (header_json_size - len(new_json))
    data[16:16 + header_json_size] = new_json

    new_hash = hashlib.sha256(new_json).hexdigest()

    with open(ASAR_PATH, "wb") as f:
        f.write(data)

    print(f"\n✅ app.asar 修补完成，共 {len(all_applied)} 处 patch")
    return new_hash, all_applied


# ---------------------------- Info.plist & 重签名 ----------------------------

def update_info_plist_hash(new_hash):
    if not os.path.exists(PLIST_PATH):
        print("⚠️  Info.plist 不存在，跳过")
        return
    with open(PLIST_PATH, "rb") as f:
        pl = plistlib.load(f)
    if "ElectronAsarIntegrity" in pl and "Resources/app.asar" in pl["ElectronAsarIntegrity"]:
        pl["ElectronAsarIntegrity"]["Resources/app.asar"]["hash"] = new_hash
        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(pl, f)
        print("✅ Info.plist 已更新 ElectronAsarIntegrity.hash")
    else:
        print("⚠️  Info.plist 未发现 ElectronAsarIntegrity（可能此版本未启用）")


def extract_entitlements_from_dmg():
    mount = find_dmg_mount()
    if not mount:
        return None
    pristine = os.path.join(mount, "Claude.app")
    if not os.path.isdir(pristine):
        return None
    print(f"📀 从挂载卷 {mount} 提取原生 Entitlements ...")
    result = subprocess.run(
        ["codesign", "-d", "--entitlements", ":-", pristine],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    xml_start = result.stdout.find("<?xml")
    if xml_start == -1:
        return None
    return plistlib.loads(result.stdout[xml_start:].encode("utf-8"))


def sanitize_and_write_entitlements(ent):
    if ent is None:
        print("⚠️  无法提取原生 Entitlements，使用默认列表")
        ent = dict(DEFAULT_ENTITLEMENTS)
    else:
        for k in RESTRICTED_KEYS:
            ent.pop(k, None)
    # 强制注入 disable-library-validation，重签后才能加载原生 .node
    ent["com.apple.security.cs.disable-library-validation"] = True
    with open(ENTITLEMENTS_PATH, "wb") as f:
        plistlib.dump(ent, f)
    print(f"✅ Entitlements 已脱壳清洗并写入 {ENTITLEMENTS_PATH}")
    return ENTITLEMENTS_PATH


def resign_app():
    print("\n🔏 重新签名 (清理 xattr + codesign --deep) ...")
    subprocess.run(["xattr", "-cr", APP_PATH])
    result = subprocess.run([
        "codesign", "--force", "--deep",
        "--entitlements", ENTITLEMENTS_PATH,
        "--sign", "-", APP_PATH,
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 签名失败: {result.stderr}")
        return False
    print("✅ 重签名成功")
    return True


# ---------------------------- 主流程 ----------------------------

def main():
    print("=" * 64)
    print(" Claude Desktop 终极修补工具 v6  (0623 全量适配) ")
    print("=" * 64)

    if not os.path.exists(ASAR_PATH):
        print(f"❌ 找不到 {ASAR_PATH}，请确认 Claude Desktop 已安装")
        sys.exit(1)

    # 还原备份以保证幂等
    if os.path.exists(BACKUP_PATH):
        print("♻️  从 .bak 还原干净 app.asar ...")
        shutil.copy2(BACKUP_PATH, ASAR_PATH)

    print("\n[步骤 1/3] 修补 app.asar ...")
    new_hash, applied = patch_asar()
    print(f"🔒 新 ASAR Hash: {new_hash}")

    print("\n[步骤 2/3] 更新 Info.plist ...")
    update_info_plist_hash(new_hash)

    print("\n[步骤 3/3] 提取 & 清洗 Entitlements + 重签名 ...")
    ent = extract_entitlements_from_dmg()
    sanitize_and_write_entitlements(ent)
    if not resign_app():
        sys.exit(2)

    print("\n" + "=" * 64)
    print(f"🎉 全部完成！本次共应用 {len(applied)} 处 patch：")
    for name in applied:
        print(f"   • {name}")
    print("=" * 64)
    print("👉 现在可以正常打开 Claude Desktop 了")
    print("   第三方模型（如 minimax-m3、doubao-seed）将出现在下拉框中")
    print("   Cowork 功能已绕过 entitlement 校验")
    print("   Session 标题会在 LLM 失败时本地兜底")
    print("   3P 模型不会再发 xhigh effort 请求（兼容 low/medium/high/max）")


if __name__ == "__main__":
    main()
