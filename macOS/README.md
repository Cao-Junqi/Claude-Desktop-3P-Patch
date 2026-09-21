# Claude Desktop macOS Patch

## 📦 脚本说明

### 1. patch_claude_3p_macos_0921.py ⭐️ 最新
**适配版本**: Claude Desktop `2.2553.1`（构建日 0918）+ `1.44121.4`（0903）
**功能**: 第三方模型解锁（Gateway / OpenAI / Azure / 自定义模型）+ 禁用自动更新 + 本地能力恢复 + 可选汉化

**使用方法**:
```bash
cd macOS

# 先 dry-run 确认全层命中
python3 patch_claude_3p_macos_0921.py \
  --app /Applications/Claude.app \
  --provider gateway --feature-recovery --zh-cn --dry-run

# 正式打补丁（会重签名）
sudo python3 patch_claude_3p_macos_0921.py \
  --app /Applications/Claude.app \
  --provider gateway --feature-recovery --zh-cn
```

**2.2553.1 更新内容**:
- **新增 L2d**：渲染进程（`ion-dist`）的模型校验器。此前只补主进程，导致 Settings 仍报
  `Doesn't look like an Anthropic model: 需要一个引用 Anthropic 模型的网关模型路由…`
- **新增 L9**：渲染进程的语言列表数组。此前 `zh-CN.json` 已装好但下拉框里没有中文。
- L1 / L2 / L2c / L4 / L6 更新特征码（变量名与接收器变化）。
- L2b / L5 / L7 在新版原生已处理，无需 patch。

### 2. patch_claude_zhcn_macos_0921.py ⭐️ 最新
**适配版本**: Claude Desktop `2.2553.1` + `1.44121.4`
**功能**: 完整中文汉化
**翻译条目**: 24019 条（自研翻译）

**使用方法**:
```bash
cd macOS
sudo python3 patch_claude_zhcn_macos_0921.py --user-home "$HOME"
```

**2.2553.1 变化**:
- 语言列表不再是「装文件即可」：脚本会真正把 `zh-CN` 拼进渲染进程的 `Am` 数组，否则
  Settings → Language 里看不到中文。
- 汉化文件位置：`ion-dist/i18n/zh-CN.json`（前端）+ `Resources/zh-CN.json`（桌面端）。
- 3P 模型校验自 0903 起已移出 `app.asar`，本脚本不再尝试 patch（请用 3P 脚本）。

> ⚠️ **汉化覆盖率**：2.2553 的 `en-US.json` 增至 29442 key（较 0903 新增 6683），当前
> 24019 条翻译覆盖 17332/29442，**约 12110 条回落英文**。补齐方式见
> [`../translations/README.md`](../translations/README.md)。

---

### 旧版本脚本（已过时）

#### patch_claude_3p_macos_0811.py
**适配版本**: Claude Desktop 0811 (1.26832.0)

#### patch_claude_zhcn_macos.py
**适配版本**: Claude Desktop 0811 及更早版本

## 📂 resources/
汉化翻译资源文件（自研）：
- `frontend-zh-CN.json` - 前端翻译（24019 keys）
- `desktop-zh-CN.json` - 桌面端翻译
- `statsig-zh-CN.json` - 统计配置翻译
- `Localizable.strings` - 原生字符串

## ⚠️ 注意事项
- 需要 sudo 权限（写 `/Applications` 时）
- 运行前关闭 Claude Desktop
- 会自动备份原 App
- 打补丁后必须重签名；脚本已自动处理（含 `ion-dist` 下的散文件）

## 📥 Claude Desktop 下载

从 [claude.ai/download](https://claude.ai/download) 获取最新 DMG（当前验证版本 `2.2553.1`）。

---

**更新日期**: 2026-09-21
**系统要求**: macOS 10.15+