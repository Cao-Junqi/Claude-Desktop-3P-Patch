# Changelog

本项目遵循「日期 — 主题」的变更记录格式。最新在上。

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