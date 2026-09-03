# Claude Desktop 3P Patcher

用于 macOS / Windows Claude Desktop 的 3P / Gateway / 本地功能恢复补丁脚本。

当前推荐脚本：

```text
macOS: patch_claude_3p_v2.py
Windows: patch_claude_3p_windows.py
```

当前主适配目标：

```text
Claude-0811.dmg / Claude Desktop 1.26832.0
```

已完成验证：dry-run、临时 App patch、中文汉化（24019 key 全覆盖）、重签名、`codesign`、临时 App + 正式安装启动实测。

> 变更历史见 [CHANGELOG.md](CHANGELOG.md)，操作流程见 [SOP.md](SOP.md)，Windows 详细使用见 [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md)。

---

## 功能概览

### 1. 3P / Gateway 模型兼容

脚本会 patch Claude Desktop 中的本地校验逻辑，使第三方模型在 3P/Gateway 模式下更可用：

- 绕过 managed config `safeParse` 严格校验；
- 放开模型选择器白名单；
- 绕过 gateway model route validator；
- 绕过 inference model catalog throw；
- 修复/兼容 3P 模型 `xhigh` effort 不支持的问题；
- 支持 0703 新版 minified 特征码。

### 2. 自动更新禁用

脚本会把更新检查逻辑改为强制早期返回：

```text
if(1||...)
```

避免旧版 `if(0&&...)` 导致自动更新仍然放行的问题。

同时支持额外写入 macOS policy：

```text
com.anthropic.claudefordesktop disableAutoUpdates = true
```

### 3. Cowork / Secure VM 兼容

脚本会 patch `@ant/claude-swift` 的虚拟化支持检测：

```js
this.vm.isVirtualizationSupported = () => "supported";
```

并在重签名时保留/注入关键 entitlements：

- `com.apple.security.virtualization`
- `com.apple.security.cs.disable-library-validation`
- `com.apple.security.cs.allow-jit`

### 4. 会话标题 fallback

当官方 title generation 调用失败时，脚本会使用首条消息生成不同标题：

```js
String(first_session_message || "").slice(0,46)
```

这样可以避免失败后所有会话标题为空或相同。

说明：provider 级智能摘要标题仍取决于实际 3P provider / gateway 是否支持相关调用。

### 5. 本地功能恢复

新增 `--feature-recovery` 后，脚本会尽量恢复本地可控能力：

- 本地 UI 入口恢复；
- local feature flags；
- Claude Code tab；
- 本地 MCP；
- desktop extensions；
- extension directory；
- secure VM features；
- 本地 skills/plugins/extensions 报告。

涉及的本地偏好键：

```text
secureVmFeaturesEnabled
isDesktopExtensionEnabled
isDesktopExtensionDirectoryEnabled
isLocalDevMcpEnabled
isClaudeCodeForDesktopEnabled
```

### 6. 本地 skills/plugins 管理报告

支持扫描本地 skills/plugins/extensions 目录：

```bash
--local-market-report
```

默认扫描：

```text
~/.claude/skills
~/.claude/plugins
~/.claude/workflows
~/Library/Application Support/Claude
~/Library/Application Support/Claude/extensions
~/Library/Application Support/Claude/plugins
~/Library/Application Support/Claude/skills
```

### 7. 中文汉化

新版脚本已合并中文汉化流程：

```bash
--zh-cn
--lang zh-CN
--lang zh-TW
--lang zh-HK
```

支持：

- frontend i18n 资源安装；
- desktop shell 语言资源安装；
- hardcoded frontend strings 替换；
- main process menu labels 替换；
- language display names patch；
- 0703 语言选择器白名单 patch；
- 可选设置用户 locale。

0703 语言白名单位置已适配：旧逻辑只扫描 `index-*.js`，新版会在失败后扫描 `Contents/Resources/ion-dist/assets/v1/*.js`，当前已验证命中：

```text
Contents/Resources/ion-dist/assets/v1/c4b350ac1-BTR_0NaM.js
```

并写入：

```js
"zh-CN"
```

---

## 文件说明

| 文件 | 说明 |
|---|---|
| `patch_claude_3p_v2.py` | macOS 主脚本，支持 0811（bundle 多文件扫描）、3P patch、本地功能恢复、中文汉化、签名验证 |
| `patch_claude_3p_windows.py` | Windows 主脚本，支持 3P patch、注册表策略、跨平台 ASAR 处理 |
| `patch_claude.py` | 旧版 0604/0623 基线脚本，保留作参考 |
| `patch_claude_zh_cn.py` | 独立中文汉化脚本，新版主脚本会复用其中的汉化逻辑 |
| `resources/` | 中文汉化资源目录（frontend-zh-CN.json 24019 key） |
| `translations/` | 汉化翻译管线（批次文件 + 校验/合并工具） |
| `Claude-0811.dmg` | 0811 安装包，推荐从此 DMG 复制临时 App 后 patch |
| `AGENTS.md` | 开发/维护记录，包含关键变量、patch 层、验证状态和后续维护提示 |

---

## Windows 使用方法

### 1. Dry-run 检查（Windows）

```powershell
python patch_claude_3p_windows.py --dry-run --write-policy --report-json C:\temp\claude-dryrun.json
```

### 2. 正式 Patch（Windows，需要管理员权限）

```powershell
# 以管理员身份运行 PowerShell

# 基础版本（仅 3P patch）
python patch_claude_3p_windows.py --write-policy --report-json C:\temp\claude-patched.json

# 完整版本（3P patch + 中文汉化）
python patch_claude_3p_windows.py --zh-cn --write-policy --report-json C:\temp\claude-patched.json
```

脚本会自动查找以下位置的 Claude 安装：
- `%LOCALAPPDATA%\Programs\Claude`
- `%PROGRAMFILES%\Claude`

也可以手动指定：

```powershell
python patch_claude_3p_windows.py --app "C:\Custom\Path\To\Claude" --write-policy
```

### Windows 版本说明

- **ASAR patch**：与 macOS 完全相同的 patch 逻辑（7 层全覆盖）
- **中文汉化**：✅ 已移植（24019 key，与 macOS 版本一致）
- **代码签名**：Windows Electron 应用不需要重签名
- **策略管理**：使用注册表 `HKLM\SOFTWARE\Policies\Anthropic\Claude`
- **支持语言**：`--zh-cn`（简体中文）、`--lang zh-TW`（繁体-台湾）、`--lang zh-HK`（繁体-香港）

---

## 使用方法（macOS）

### 1. Dry-run，不修改系统 App

推荐每次新版本都先执行 dry-run：

```bash
python3 patch_claude_3p_v2.py \
  --from-dmg \
  --dmg Claude-0811.dmg \
  --dry-run \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --report-json /tmp/claude-3p-feature-dryrun.json
```

### 2. Patch 临时 App，但不安装

```bash
python3 patch_claude_3p_v2.py \
  --from-dmg \
  --dmg Claude-0811.dmg \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --report-json /tmp/claude-3p-feature-patched.json
```

脚本会输出临时目录里的 `Claude.app` 路径，可先检查报告和签名结果。

### 3. 安装到 `/Applications`

确认 dry-run 和临时 App patch 都正常后，再安装：

```bash
sudo python3 patch_claude_3p_v2.py \
  --from-dmg \
  --dmg Claude-0811.dmg \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --install \
  --launch
```

脚本会在替换前备份原 App。

### 4. 只禁用自动更新 policy

```bash
sudo python3 patch_claude_3p_v2.py \
  --check-only \
  --write-policy \
  --provider gateway
```

### 5. 只检查本地 skills/plugins/extensions

```bash
python3 patch_claude_3p_v2.py \
  --check-only \
  --local-market-report \
  --provider gateway
```

### 6. 只启用本地 Claude Code / MCP / extension 偏好

```bash
python3 patch_claude_3p_v2.py \
  --check-only \
  --enable-local-code-features \
  --local-market-report \
  --provider gateway
```

---

## 常用参数

| 参数 | 说明 |
|---|---|
| `--from-dmg` | 从 DMG 复制 Claude.app 到临时目录后 patch |
| `--dmg <path>` | 指定 DMG，默认可用 `Claude-0811.dmg` |
| `--app <path>` | 指定已安装的 Claude.app，默认 `/Applications/Claude.app` |
| `--dry-run` | 只检查 patch 命中情况，不写入 App |
| `--install` | 把 patch 后的临时 App 安装到 `--app` |
| `--launch` | 安装后启动 Claude |
| `--provider` | 指定 provider 报告类型：`gateway` / `anthropic` / `bedrock` / `vertex` / `foundry` / `aws` / `unknown` |
| `--report-json <path>` | 输出 JSON 报告 |
| `--write-policy` | 写入系统级禁用自动更新 policy |
| `--feature-recovery` | 启用本地功能恢复组合项 |
| `--enable-local-code-features` | 写入本地 Claude Code / MCP / extension 偏好 |
| `--local-market-report` | 输出本地 skills/plugins/extensions 报告 |
| `--zh-cn` | 安装简体中文资源 |
| `--lang <code>` | 安装指定中文资源：`zh-CN` / `zh-TW` / `zh-HK` |
| `--user-home <path>` | 指定用户 home，用于 locale 和本地目录报告 |

---

## 验证记录

当前版本已执行过以下验证。

### 语法检查

```bash
python3 -m py_compile patch_claude.py patch_claude_3p_v2.py patch_claude_zh_cn.py
```

结果：通过。

### 0703 dry-run

```bash
python3 patch_claude_3p_v2.py \
  --from-dmg \
  --dmg Claude-0811.dmg \
  --dry-run \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --report-json /tmp/claude-3p-feature-dryrun.json
```

结果：L1/L2/L2b/L2c/L4/L6/L7/L3b 均命中，本地功能恢复、中文汉化均显示 `would_patch`。

### 临时 App 实际 patch + 功能恢复 + 中文汉化

最新验证命令：

```bash
python3 patch_claude_3p_v2.py \
  --from-dmg \
  --dmg Claude-0811.dmg \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --report-json /tmp/claude-3p-langfix.json
```

结果：

```text
ASAR: patched
Signing: signed
codesign verify: OK
Local feature UI patch: patched
Localization: patched zh-CN 简体中文
Patched language whitelist: c4b350ac1-BTR_0NaM.js
```

语言白名单验证：

```text
whitelist has zh-CN: True
zh-CN locale exists: True
desktop shell exists: True
```

实际白名单片段：

```js
S1=["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID","zh-CN"];
```

临时 App 启动验证：通过。当前已验证可直接启动临时 App binary，不再出现 `SyntaxError: Unexpected token ';'`。

---

## 更新日志

变更历史已独立成 [CHANGELOG.md](CHANGELOG.md)（日期-主题，最新在上）。本文件不再内嵌重复内容。

---

## 注意事项

1. 本项目会修改 Claude Desktop 的本地 App bundle，并进行 ad-hoc 重签名。
2. 安装到 `/Applications` 需要 `sudo`。
3. 每次新 Claude Desktop 版本都应先执行 `--dry-run`。
4. 官方云端授权能力无法通过本地 patch 保证恢复。
5. 如手动覆盖升级 Claude Desktop，需要重新执行 patch。
