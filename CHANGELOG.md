# Changelog

本项目遵循「日期 — 主题」的变更记录格式。最新在上。

---

## 2026-09-21 — 适配 2.2553.1 + renderer 层补丁（关键修复）

### 新增：renderer 层补丁（L2d / L9）

**这是本次最重要的发现**：`Contents/Resources/ion-dist/` 位于 `app.asar` **之外**，此前所有 patch 层只扫 `.vite/build/`，因此完全漏掉了渲染进程。2.2553 起模型校验和语言列表都在这里各有一份独立实现：

| 层 | 位置 | 作用 |
|---|---|---|
| L2d | `ion-dist/assets/v1/ce459c687-*.js` | 渲染进程的模型校验器（`wt` 门 + `Dt`/`Ot`/`kt` 三个 provider 校验器 + Vertex/Bedrock） |
| L9 | `ion-dist/assets/v1/shared-2-*.js` | 语言选择器的可选语言数组 `Am`（导出为 `vm`，被 `shared-21` 当作 `offeredLocales`） |

症状与根因：
- **报错「Doesn't look like an Anthropic model: 需要一个引用 Anthropic 模型的网关模型路由…」**：来自渲染进程的 `At()` → `kt()`，与主进程 `Yo()` 是两套独立代码。只补主进程时，Settings 仍会用渲染进程那套拒绝 3P 模型名。
- **语言列表没有中文**：`Am` 数组决定下拉框内容，`zh-CN.json` 存在但不在数组里就不显示。0903 时期该数组也存在于 `shared-3-*.js`，同样未被打补丁。

文件名带内容哈希（`ce459c687-B4NlOXPM.js`），因此按**内容**定位而非文件名。两个文件都在 `app.asar` 之外，等长替换不是硬性要求（无 ASAR layout 约束），但校验器仍用等长替换以保持一致；`resign_app()` 的 `Contents/` 全树遍历已覆盖这两个文件的签名。

### 适配 Claude Desktop 2.2553.1

版本号方案从 `1.44121.4`（日期型）改为 `2.2553.1`（语义型）。逐层结果：

| 层 | 状态 | 说明 |
|---|---|---|
| L1 | 更新 | `uOt`/`vOt` 两个 custom3p helper 校验器（`index.chunk-ChZ67Jhw.js`） |
| L2 | 更新 | 选择器空白名单改为 `hC(e,n)`（`index.chunk-l0PS_wmg.js`） |
| L2b | 仍不需要 | 终端 `.some()` 白名单在新版依旧不存在 |
| L2c | 更新 | 主进程 `Hxe`/`Uxe`/`Wxe` + 共享门 `Jo`；preload `KS`/`qS`/`JS` + 共享门 `US`；另加 Vertex 内联校验器 |
| L2d | **新增** | 渲染进程校验器（见上） |
| L4 | 更新 | 更新器守卫接收器变为 `K()`（3 处 block + 1 处 early-return） |
| L5 | 仍不需要 | `inferenceModels` 过滤（`Cke`/`wke`）只做剔除不抛错 |
| L6 | 更新 | `/dust/generate_title_and_branch` 兜底值从 `""` 变为 `{title:""}`，需独立特征码 |
| L7 | 仍不需要 | `cwn` 集合原生排除 xhigh，`uwn()` 兜底 `medium` |
| L9 | **新增** | 渲染进程语言列表（见上） |

### 修复：汉化脚本桥接路径失效

`patch_claude_3p_macos_0921.py` 的 `load_zh_cn_patcher()` 仍指向已改名的 `patch_claude_zh_cn.py`，导致 `--zh-cn` 直接 `SystemExit`。现按 `patch_claude_zhcn_macos_0921.py` → `patch_claude_zh_cn.py` 顺序回退查找。

### 修复：独立汉化脚本的语言列表

`patch_claude_zhcn_macos_0921.py` 的 `patch_language_whitelist()` 原本假定「0903 改为文件系统扫描，无需改 JS」，实际 2.2553 仍依赖硬编码数组。现改为真正把语言拼进 `Am`，并把 locale 文件安装提到该步骤之前（否则会误报「locale files not installed yet」）。

### 汉化覆盖率说明

2.2553 的 `en-US.json` 从 24954 增至 29442 key（新增 6683）。现有 `resources/frontend-zh-CN.json`（24019 key）覆盖 17332/29442，**12110 条回落英文**。这属于新增内容而非回归（0903 时缺 6107）。补齐方式见 `translations/README.md`。

### 验证

- dry-run 全层命中（ASAR 19 处 + renderer 9 处），无 `missing`/`ambiguous`。
- 全部被改文件 `node --check` 通过（ASAR 内 4 个 + renderer 2 个）。
- `codesign --verify --deep --strict` 通过；`ElectronAsarIntegrity` 已更新。
- 幂等性：对已打补丁的 app 重跑，全部报告 `already_applied`，语言数组无重复项。
- 校验器行为验证：抽出补丁后的 `At()`/`Yo()` 在 Node 中执行，`minimax-m3`/`glm-4.6`/`deepseek-v3`/`gpt-4o` 均返回 `ok=true`。
- 用户实测确认：汉化与 3P 模型拦截均正常。

### 脚本重命名

`patch_claude_3p_macos_0903.py` → `patch_claude_3p_macos_0921.py`
`patch_claude_zhcn_macos_0903.py` → `patch_claude_zhcn_macos_0921.py`

沿用「版本日期」命名惯例（`0811` = 1.26832.0、`0903` = 1.44121.4），`0921` 对应
2.2553.1 的适配版本。3P 脚本的汉化桥接保留 `_0903` 与 `patch_claude_zh_cn` 作为回退名。

### 已安装生效

- 目标：`/Applications/Claude.app`，版本 `2.2553.1`
- 备份：`/Applications/Claude.backup-before-3p-v2-20260921-171748.app`（0903 / 1.44121.4）
- 命令：
  ```bash
  python3 macOS/patch_claude_3p_macos_0921.py \
    --dmg ~/Downloads/Claude.dmg \
    --install --provider gateway --feature-recovery --zh-cn --write-policy
  ```
- 测试报告：[`macOS/test_0921_summary.md`](macOS/test_0921_summary.md)

### 待办

- 汉化补全：2.2553 的 `en-US.json` 增至 29442 key，当前覆盖 17332/29442，
  **12110 条回落英文**（新增内容，非回归）。流程见 `translations/README.md`，本次暂缓。

---

## 2026-09-03 — Windows 适配 + macOS L6 修复

### Windows 适配

- 新增 `patch_claude_3p_windows.py`：Windows 版本的 3P patch 脚本。
- 核心功能移植：
  - ASAR patch 逻辑（与 macOS 完全相同的特征码和 patch 规则）
  - **中文汉化**：完整移植（语言白名单、frontend/desktop/statsig 翻译、硬编码字符串替换）
  - Windows 路径适配：`resources/app.asar`（vs macOS `Contents/Resources/app.asar`）
  - 注册表策略：`HKLM\SOFTWARE\Policies\Anthropic\Claude` 禁用自动更新
  - 跳过代码签名（Windows Electron 应用不需要）
- 自动查找安装位置：`%LOCALAPPDATA%\Programs\Claude` 或 `%PROGRAMFILES%\Claude`
- 命令行参数：`--zh-cn` / `--lang zh-CN/zh-TW/zh-HK` / `--write-policy` / `--dry-run`

### macOS 修复

- 修复 L6 层 `pad_bytes()` 长度计算错误：原代码在传参时使用了 `len(原字符串)` 包裹导致运行时报错 "non-equal replacement length"。
- 现已改为直接传入常量 `64`（两处 0811 特征码的实际长度）。
- 验证通过：dry-run 全层 `already_applied`，语法检查通过。

### 文档

- README 新增 Windows 使用说明。
- WINDOWS_GUIDE.md 新增完整 Windows 使用指南。
- 文件说明表更新，标注 macOS/Windows 脚本分工。

---

## 2026-08-11 — 适配 0811（1.26832.0）+ 汉化全量补全

### 0811 适配

- `patch_claude_3p_v2.py` 从单文件扫描改为**多文件扫描**：0811 的 `.vite/build/index.js` 被代码分割成约 250 个 `index.chunk-*.js` / `index2.chunk-*.js` + `index.pre.js`（4.4MB），旧脚本只扫单个 `index.js` 导致 L1-L7 全 miss。
- 新增 `find_index_build_files()` + `patch_index_files()`，`patch_asar()` 改为多文件写回；0703 兼容保留。
- 各层 0811 新特征码（已实测命中 14 处）：
  - L1 `let s=um.safeParse(o);if(!s.success)throw` → 伪造成功
  - L2 / L2c 各 provider validator（`de`/`YB`/`me`/`fe`/`pe`/`QB`/`XB`/`ZB`）的 `{ok:!1,reason:` → `{ok:!0,reason:`
  - L4 `if(r.autoUpdate.disabled){`、`if(a.a().autoUpdate.disabled){`（×3，allow_multi）
  - L5 `s.data.models);if(u)throw` → `if(0)throw`
  - L6 入口 `index.js` 的 `[title-gen] failed` catch → 兜底 `first_session_message`
  - L3b 直接命中（offset 1750→1830）
  - L2b / L7 在 0811 中已被新版结构吸收/原生 gate，无需 patch
- 修复 L4 早期写法漏掉 if 条件右括号 `)` 导致的启动 SyntaxError。

### 汉化全量补全

- `resources/frontend-zh-CN.json` 从 12355 → **24019 key**，机翻补齐 11664 条缺译。
- 重打补丁后：**20436 translated / 0 fallback**（此前 8956 translated / 11664 fallback）。
- 翻译管线入库 `translations/`（batch 源 + translated 结果 + check_and_merge.py + README）。
- 规则：ICU plural/`{占位符}`/`<标签>` 保留；专有名词（Claude/MCP/模型名等）留英文。
- 官方 Anthropic 中文包本就只覆盖 44%（9057/20721），本补全超出官方范围。

### 文档

- 新增 `HANDOFF.md`、`SOP.md`、本 `CHANGELOG.md`；`AGENTS.md` 补 0811 适配记录 + TCC 注意事项。

---

## 2026-07-03 — 0703 功能恢复补丁（`b6d0eb3`）

- 新增 `patch_claude_3p_v2.py`，适配 Claude Desktop 1.18286.0（0703）。
- 修复 FrA gateway validator 生成非法 JS（`return 1!==0?{ok:!0};`）为合法等长 `if(1)return{ok:!0};`。
- 修复 0703 语言白名单失效（语言数组迁移到 `ion-dist/assets/v1/*.js`，加 fallback 扫描）。
- 自动更新禁用改为 `if(1||...)` 强制早期返回。
- 新增 `--feature-recovery` / `--enable-local-code-features` / `--local-market-report` / `--zh-cn` / `--lang`。
- 支持 DMG → 临时 App → patch → 验证 →（显式 `--install`）的安全流程。

## 2026-07-04 — SkillHub 移除（`f2c7596`）

- 完全移除 SkillHub（面板/IPC/embed/CLI args），功能收敛为 3P patch + Cowork + 中文 + 本地恢复。
- 清理 README / INSTALL_APPLICATION_PATCH.md 中的 SkillHub 引用。

## 2026-07-05 — 3P 调研与 marketplace 结论（`49eba0e`）

- 补 3P 模式 vs 官方订阅功能差异表。
- Marketplace 调研结论：banner 服务端下发、`allowedPluginMarketplaces` 3P 下为空、`hasOrgPolicyBackend()` 恒 false；脚本层面已到本地 patch 极限，改走本地 sideload / 自建 marketplace。

## 2026-08-11 — 汉化翻译管线入库（`b23aa9e`）

- `translations/` 入库：24 批英文源 + 24 批机翻结果 + `check_and_merge.py`（校验/合并，改仓库相对路径）+ README。

---

## 2026-06-23 — 0623 基线（`47c71a0`）

- `patch_claude.py`：11 处 patch，实测 Claude Desktop 1.14271.0。
- L1 3P safeParse / L2 model picker / L2c gateway validator / L3b claude-swift 虚拟化 / L4 自动更新 / L5 inference 校验 / L6 session title / L7 effort xhigh。
- 中文汉化资源 `resources/` + `patch_claude_zh_cn.py`。