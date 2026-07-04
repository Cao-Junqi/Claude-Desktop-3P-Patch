# AGENTS.md

本文件用于记录 Claude Desktop 3P Patcher 项目的关键变量、维护状态、patch 层含义和近期工作情况，方便后续 agent / 开发者继续维护。

---

## 项目目标

维护一个面向 macOS Claude Desktop 的 3P / Gateway / 本地功能恢复补丁脚本：

```text
patch_claude_3p_v2.py
```

核心诉求：

- 恢复 3P / Gateway 模型可见和可用；
- 禁止自动更新，避免官方升级覆盖 patch；
- 保持 Cowork / Secure VM 相关本地能力可启动；
- 恢复本地 Claude Code / MCP / extensions / skills / plugins 入口；
- 合并中文汉化能力，并让 App 内语言选择器显示"简体中文"；
- 默认采用 DMG → 临时 App → patch → 验证 的安全流程，只有显式 `--install` 才替换 `/Applications/Claude.app`。

**当前状态**：脚本与 GitHub `origin/main` 一致（commit `f2c7596`），功能已精简到纯 3P patch + 本地恢复 + 中文汉化，无额外注入。

---

## 当前适配环境

| 项 | 值 |
|---|---|
| 系统 | macOS |
| 主安装包 | `Claude-0703.dmg` |
| 已验证 Claude Desktop 版本 | `1.18286.0` |
| Bundle ID | `com.anthropic.claudefordesktop` |
| 主脚本 | `patch_claude_3p_v2.py` |
| 旧基线脚本 | `patch_claude.py` |
| 中文汉化辅助脚本 | `patch_claude_zh_cn.py` |
| 中文资源目录 | `resources/` |

---

## 关键路径与常量

`patch_claude_3p_v2.py` 中的重要常量：

```python
APP_DEFAULT = Path("/Applications/Claude.app")
ROOT = Path(__file__).resolve().parent
DEFAULT_DMG = ROOT / "Claude-0703.dmg"
APP_ASAR_REL = Path("Contents/Resources/app.asar")
ASAR_INDEX = ".vite/build/index.js"
ASAR_SWIFT = "node_modules/@ant/claude-swift/js/index.js"
ASAR_INTEGRITY_BLOCK_SIZE = 4 * 1024 * 1024
POLICY_DOMAIN = "com.anthropic.claudefordesktop"
FRONTEND_ASSETS_REL = Path("Contents/Resources/ion-dist/assets/v1")
LANG_CHOICES = ["zh-CN", "zh-TW", "zh-HK"]
```

macOS policy / preferences 相关 key：

```python
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
```

---

## 主脚本功能入口

`patch_claude_3p_v2.py` 中的关键函数：

| 函数 | 用途 |
|---|---|
| `read_asar_header()` | 解析 Electron ASAR header |
| `encode_asar_header()` | 重写 ASAR header，保持原 header size |
| `calculate_file_integrity()` | 计算 Electron 4MB block SHA-256 integrity |
| `update_electron_asar_integrity()` | 更新 `Info.plist` 里的 `ElectronAsarIntegrity` |
| `patch_exact()` | 等长 byte patch，记录 offset / 状态 |
| `apply_alternatives()` | 每个 patch 层尝试多个版本特征码 |
| `build_index_patch_specs()` | 主进程 `.vite/build/index.js` patch 规格 |
| `patch_index()` | patch 主进程 index.js |
| `patch_swift()` | patch `@ant/claude-swift` 虚拟化检测 |
| `patch_asar()` | patch ASAR 并更新完整性 |
| `resign_app()` | 清理 xattr、重签 nested items 和 outer app |
| `verify_app()` | `codesign --verify` 与 entitlements 检查 |
| `apply_localization()` | 调用汉化辅助脚本并处理 0703 whitelist fallback |
| `patch_local_feature_ui()` | 注入本地 feature recovery marker |
| `write_local_feature_preferences()` | 写入本地 Claude Code / MCP / extension 偏好 |
| `local_market_report()` | 扫描本地 skills/plugins/extensions |
| `print_report()` | 输出人类可读报告 |
| `main()` | CLI 主流程 |

---

## 3P patch 层说明

当前 0703 已验证的 ASAR patch 层：

| 层 | 含义 | 目标文件 |
|---|---|---|
| L1 | 3P managed config `safeParse` bypass | `.vite/build/index.js` |
| L2 | model picker empty allowlist bypass | `.vite/build/index.js` |
| L2b | model picker terminal `some()` bypass | `.vite/build/index.js` |
| L2c | gateway model route validator bypass | `.vite/build/index.js` |
| L3b | `@ant/claude-swift` virtualization support | `node_modules/@ant/claude-swift/js/index.js` |
| L4 | auto-update forced early return | `.vite/build/index.js` |
| L6 | session title fallback | `.vite/build/index.js` |
| L7 | effort `xhigh` compatibility | `.vite/build/index.js` |

0703 验证过的典型 offsets（仅用于排查，不作为 patch 定位依据）：

```text
L1:  6621284
L2:  12921568
L2b: 12921643
L2c: 6420188, 6420394
L4:  13184052, 13188888
L6:  13161585, 13161882
L7:  8164336
L3b: 1750
```

---

## 近期重要修复

### 1. 自动更新禁用修复

旧版错误逻辑使用类似：

```js
if(0&&...)
```

导致"禁用自动更新"分支永远不执行。当前改为强制早期返回：

```js
if(1||...)
```

同时可选写入：

```text
/Library/Preferences/com.anthropic.claudefordesktop disableAutoUpdates = true
```

### 2. FrA gateway validator 语法错误修复

曾经出现启动报错：

```text
Claude Desktop failed to launch
SyntaxError: Unexpected token ';'
```

原因是 0703 的 `FrA` patch 生成了非法三元表达式：

```js
return 1!==0?{ok:!0};
```

当前改为合法且等长的 patch：

```js
if(1)return{ok:!0};
```

已通过 `node --check` 与临时 App 启动验证。

### 3. 0703 语言白名单修复

问题：中文资源注入成功，但 App 内语言选择器没有出现"简体中文"。

原因：旧汉化逻辑只扫描 `index-*.js`，0703 的实际语言白名单在：

```text
Contents/Resources/ion-dist/assets/v1/c4b350ac1-BTR_0NaM.js
```

修复：在 `apply_localization()` 中加入 fallback 扫描 `assets/v1/*.js`。当前验证片段：

```js
S1=["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID","zh-CN"];
```

### 4. SkillHub 移除（2026-07-04）

因面板存在全局显示 bug 且依赖服务端市场，已将 SkillHub 完全移除：

- 删除 `DEFAULT_SKILLHUB_URL` 常量
- 删除 `patch_skillhub_entry()` 函数
- 删除 `--skillhub-url` / `--embed-skillhub` CLI 参数
- 清理 `README.md` 和 `INSTALL_APPLICATION_PATCH.md`

脚本当前与 GitHub `origin/main` 一致。

---

## 中文汉化状态

当前 `--zh-cn` 会执行：

1. patch language whitelist（含 0703 fallback 扫描）；
2. patch hardcoded frontend strings（665 replacements in 78 files）；
3. patch language display names；
4. patch hardcoded main-process menu labels（4 replacements）；
5. merge frontend locale（10205 translated, 8053 fallback, 2045 extra old keys ignored）；
6. install desktop shell locale；
7. install statsig locale；
8. 如 `--install` 时允许，则设置用户ocale。

> `user_config=skipped_not_installing` 是预期行为：未使用 `--install` 时，不修改用户实际 Claude 配置。

语言白名单已知 warning：

```text
language whitelist not patched: Could not patch language whitelist. Claude's bundle format may have changed.
```

0703 已修复，不再出现此 warning。

---

## 3P 模式 vs 官方订阅 功能差异调研

### 模型访问

| 功能 | 官方订阅（Claude.ai） | 3P / Gateway 模式 |
|---|---|---|
| 模型来源 | Anthropic 原生 API | AWS Bedrock / Google Vertex / Microsoft Foundry / 自建网关 / OpenAI-compatible |
| claude- 系列模型 | ✅ 全部可用 | ❌ 除非 Bedrock/Vertex 上的 Anthropic 模型 |
| Web Search | ✅ 内置 | ⚠️ 取决于 provider |
| Fast Mode | ✅ | ❌ 通常不可用 |
| Effort 参数 | ✅ low–max | ⚠️ 3P 不识别 xhigh（L7 已禁用） |
| Prompt Caching | ✅ 自动 | ⚠️ 取决于 provider 是否透传 |
| Compaction | ✅ 服务端自动 | ⚠️ 取决于网关 |

### 插件 / 扩展 / 集成

| 功能 | 官方订阅 | 3P 模式 | 本地可恢复？ |
|---|---|---|---|
| Plugin Marketplace 浏览 | ✅ 官方目录 | ❌ 服务端 gated banner | ❌ |
| 官方 Plugin 一键安装 | ✅ | ❌ | ❌ |
| Desktop Extensions（.dxt） | ✅ | ✅ UI 可见，本地 sideload 可用 | ✅ 已解锁 |
| Local MCP Servers | ✅ | ✅ | ✅ 已解锁 |
| Claude Code（本地代理） | ✅ | ✅ | ✅ 已解锁 |
| Google Workspace connectors | ✅ | ❌ | ❌ |
| GitHub official integration | ✅ | ⚠️ PAT-based 可用 | ⚠️ |
| Slack/Linear connectors | ✅ | ❌ | ❌ |

### 平台 / 多端 / 云服务

| 功能 | 官方订阅 | 3P 模式 |
|---|---|---|
| Web App（claude.ai） | ✅ | ❌ |
| Mobile App | ✅ | ❌ |
| Slack Bot | ✅ | ❌ |
| Chrome Extension | ✅ | ❌ |
| Cross-device sync | ✅ | ❌ |
| Schedule / Deployments | ✅ | ❌ |
| Fast Mode | ✅ | ❌ |

---

## Plugin Marketplace 调研结论（2026-07-04）

### 调查范围

已搜索 0703 `app.asar` 中的所有 JS bundle：
- `.vite/build/index.js`（renderer, 15MB）
- `.vite/build/index.pre.js`（preload, 893KB）
- `.vite/build/mainView.js`
- `.vite/build/mainWindow.js`
- `.vite/build/aboutWindow.js`

搜索关键词：`组织` / `管理员` / `插件` / `Organization` / `Marketplace` / `pluginMarketplace` / `allowedPluginMarketplaces` / `disabled` / `hasOrgPolicyBackend` 等。

### 发现

1. **Banner 文本不在客户端**："你的组织尚未提供插件。请联系你的组织管理员来添加它们。" 这整个中文字符串在 5 个 JS bundle 中均未找到。它由 Anthropic 服务端按用户 locale 下发，客户端只负责渲染。

2. **Marketplace 是本地实现**：`allowedPluginMarketplaces` 配置存在（scope `["3p"]`, version `≥1.17377.1`, 我们的 `1.18286.0` 符合），类型是 Git repo 列表。客户端定期 clone 这些 repo 到本地路径（`getLocalUploadMarketplaceDir` → `~/Library/Application Support/Claude/extensions/`），然后建立本地索引。

3. **3P 模式下该列表为空**：没有配置任何 marketplace URL，所以 Directory 标签没有内容可渲染。

4. **有 `hasOrgPolicyBackend()` 函数始终返回 `false`**：这是 3P 模式的标志性差异，控制多个 org policy 功能的可见性。

### 结论

| 做法 | 可行性 |
|---|---|
| 删 banner 文案 | ❌ 找不到（服务端下发） |
| 让官方 marketplace 加载数据 | ❌ `allowedPluginMarketplaces` 空 + 服务端不下发 |
| 自定义 marketplace | ⚠️ 可设 Git repo（需要知道官方市场的 Git URL） |

**脚本层面已走到头**。3P marketplace 的限制是：
- 服务端认定 3P org 没订阅 → 不下发 marketplace 清单
- 客户端本地 `allowedPluginMarketplaces` 列表空 → 没内容可渲染

要让 UI 真正可用，需要走**本地 sideload**（当前已解锁）或自建 marketplace（Anthropic 官方 marketplace URL 未知）。

### 已解锁的本地替代路径

- `Settings → Extensions → Install from local file`（`.dxt` sideload）
- `Settings → Developer → Local MCP`（添加本地 MCP 服务器）
- `~/.claude/skills/<skill>/SKILL.md`（本地技能）
- `~/.claude/plugins/`（本地插件）
- `~/Library/Application Support/Claude/extensions/`（本地扩展目录）
- `claude mcp add` CLI

---

## 维护注意事项

1. 所有 JS byte patch 必须等长，避免破坏 ASAR payload layout。
2. 修改 ASAR 后必须更新文件级 integrity 和 `Info.plist` 的 `ElectronAsarIntegrity`。
3. 新 Claude Desktop 版本必须先跑 `--dry-run`，确认 patch 层命中。
4. 若启动出现 `SyntaxError`，优先提取 `.vite/build/index.js` 后跑 `node --check`。
5. 若中文资源存在但语言选择器不显示，优先搜索 `assets/v1/*.js` 中的语言数组。
6. 官方云端能力无法仅靠本地 patch 保证恢复；本项目重点是本地 UI / feature flag / validator / updater / local extension 能力。
7. 安装到 `/Applications` 是高影响操作，除非用户明确要求，否则只 patch 临时 App。
