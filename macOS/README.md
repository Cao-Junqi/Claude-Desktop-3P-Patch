# Claude Desktop macOS Patch

## 📦 脚本说明

### 1. patch_claude_3p_macos_0903.py ⭐️ 最新
**适配版本**: Claude Desktop 0903 (1.44121.4)  
**功能**: 第三方模型解锁 (OpenAI/Azure/自定义模型)

**使用方法**:
```bash
cd macOS
sudo python3 patch_claude_3p_macos_0903.py
```

**更新内容**:
- L1: 更新 safeParse 模式（变量名变化：um→syt, o→r, s→i）
- L5: 移除（0903 版本中此特性已不存在）
- L2/L4/L6: 保持不变，模式仍然有效

### 2. patch_claude_zhcn_macos_0903.py ⭐️ 最新
**适配版本**: Claude Desktop 0903 (1.44121.4)  
**功能**: 完整中文汉化  
**翻译条目**: 24000+ 条（自研翻译）

**使用方法**:
```bash
cd macOS
sudo python3 patch_claude_zhcn_macos_0903.py --user-home "$HOME"
```

**0903 版本变化**:
- 语言验证改为基于文件系统扫描（无需 patch JS 语言数组）
- 汉化文件位置：`ion-dist/i18n/zh-CN.json` (前端) + `Resources/i18n/zh-CN.json` (桌面端)
- 3P 模型验证逻辑可能已移除或重构（脚本会优雅跳过）

---

### 旧版本脚本（已过时）

#### patch_claude_3p_macos_0811.py
**适配版本**: Claude Desktop 0811 (1.26832.0)  
**功能**: 第三方模型解锁

**使用方法**:
```bash
cd macOS
sudo python3 patch_claude_3p_macos_0811.py
```

#### patch_claude_zhcn_macos.py
**适配版本**: Claude Desktop 0811 及更早版本  
**功能**: 完整中文汉化

**使用方法**:
```bash
cd macOS
sudo python3 patch_claude_zhcn_macos.py --user-home "$HOME"
```

## 📂 resources/
汉化翻译资源文件（自研）：
- `frontend-zh-CN.json` - 前端翻译（24019 keys）
- `desktop-zh-CN.json` - 桌面端翻译
- `statsig-zh-CN.json` - 统计配置翻译
- `Localizable.strings` - 原生字符串

## ⚠️ 注意事项
- 需要 sudo 权限
- 运行前关闭 Claude Desktop
- 会自动备份原 App
- 推荐使用最新 0903 版本脚本

## 📥 Claude Desktop 下载

**0903 版本 (1.44121.4)** - 最新  
- macOS: `Claude-0903.dmg`
- 下载后放置在项目根目录或 macOS 目录

**0811 版本 (1.26832.0)**  
- 已过时，建议升级到 0903

---

**更新日期**: 2026-09-03  
**系统要求**: macOS 10.15+
