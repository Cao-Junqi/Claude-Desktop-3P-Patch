# TODO — 未闭环事项

> 编号项目内递增。`HANDOFF.md` 记"当前这件事做到哪"，本文件记"还有哪些没做"。

## 未闭环

- ⬜ T1 Windows 版适配 4.x / 2.x（长期项：`Windows/patch_claude_3p_windows_0811.py` 仍为 0811 基线，需在 Windows 机器上更新测试；来源：README 状态表，2026-11-07 确认仍未跟进）
- ⬜ T2 Claude Desktop 下一版本发布后的例行适配（触发式：新版 DMG + dry-run 出现 missing 时按 SOP 流程 2 走；注意 SOP 新增的 digest 机制说明）

## 待验收

（空）

## 已闭环

- ✅ T3 4.23118.0 适配 + 启动崩溃修复（Framework 内嵌 digest）+ 装机 + 文档 + 推送（2026-11-07 完成）
- ✅ T4 2.31226.1 适配 + L13（2026-10-13 完成，见 PROCESS-LOG）
