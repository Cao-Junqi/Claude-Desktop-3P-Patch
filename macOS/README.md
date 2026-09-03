# Claude Desktop macOS Patch

## 📦 脚本说明

### 1. patch_claude_3p_macos_0811.py
**适配版本**: Claude Desktop 0811 (1.26832.0)  
**功能**: 第三方模型解锁 (OpenAI/Azure/自定义模型)

**使用方法**:
```bash
cd macOS
sudo python3 patch_claude_3p_macos_0811.py
```

### 2. patch_claude_zhcn_macos.py
**功能**: 完整中文汉化  
**翻译条目**: 24000+ 条（自研翻译，2026-08-11 完成）

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
- 适配 0811 版本，其他版本可能需要更新脚本

---

**更新日期**: 2026-09-03  
**系统要求**: macOS 10.15+
