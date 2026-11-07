# PROCESS-LOG — 项目过程日志

> 记录格式：「日期 — 主题」，最新在上。技术细节见 CHANGELOG.md / AGENTS.md，操作流程见 SOP.md。

## 2026-11-07 — 适配 Claude Desktop 4.23118.0 + 启动崩溃修复 + 装机

- **需求**：用户下载新版 DMG，要求按 SOP 更新脚本、替换本机 Claude Desktop（不留备份）、推送 GitHub。
- **完成内容**：
  - 9 层失效特征码补齐（L1/L2/L4/L6/L12/L13 主进程 + L2d/L9/L10 renderer），旧版 fallback 全保留
  - renderer 迁入 `ion-dist.asar` 的结构变化：新增解包/重打包流程（`extract_ion_dist_asar` / `repack_ion_dist_asar`）+ Info.plist ion-dist hash 更新（`update_electron_asar_integrity_entry`）
  - 装机首验崩溃：定位 Electron 44.9.3 新增的 Framework 内嵌 integrity digest 校验（`integrity_digest.mm`，44.4.3 无此机制），新增 `update_electron_asar_digest()` 自动重算写回
  - SOP 步骤 3 的 asar base 计算错误修正（`8 + header_size`）
- **验证**：dry-run 全 applied、幂等 36 条 `already_applied`、node --check 全 PASS、L9 数组无重复、codesign OK、临时 App 启动稳定、装机版启动稳定 + 幂等复检通过；人工验证（中文/3P 模型/标题兜底/自动更新禁用）由用户确认通过
- **交付**：已装机 `/Applications/Claude.app`（4.23118.0）；文档更新（README/CHANGELOG/AGENTS/SOP/HANDOFF）；git 提交推送

## 2026-10-13 — 适配 2.31226.1 + L13 模型白名单修复 + 正式 App 重装

- 见 CHANGELOG 2026-10-13 两条目；当时 HANDOFF 为项目唯一过程记录，自本日起按全局规范启用本文件。
