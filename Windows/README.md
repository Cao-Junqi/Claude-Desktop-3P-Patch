# Claude Desktop Windows Patch

## 📦 脚本说明

### patch_claude_3p_windows_0811.py
**适配版本**: Claude Desktop 0811 (Windows 版本)  
**功能**: 
- 第三方模型解锁 (OpenAI/Azure/自定义模型)
- 完整中文汉化（内置）

**使用方法**:
```bash
cd Windows
python patch_claude_3p_windows_0811.py
```

或在 Windows 上直接运行：
```cmd
python patch_claude_3p_windows_0811.py
```

## 📂 resources/
汉化翻译资源文件（自研）：
- `frontend-zh-CN.json` - 前端翻译（24019 keys）
- `desktop-zh-CN.json` - 桌面端翻译
- `statsig-zh-CN.json` - 统计配置翻译

## 📦 Windows-Delivery-Package/
**完整交付包**（129MB）- 包含官方安装包和一键安装脚本

内容：
- `Claude-Setup-x64.exe` - Claude 官方安装包
- `install.bat` - 一键安装脚本（管理员权限运行）
- `patch_claude_3p_windows.py` - 独立 patch 脚本
- `resources/` - 汉化资源
- `README.txt` - 快速指南
- `TROUBLESHOOTING.md` - 故障排除

**使用方法**:
1. 安装 Claude Desktop
2. 右键 `install.bat` → "以管理员身份运行"
3. 重启 Claude Desktop

## ⚠️ 注意事项
- 需要在 **Windows 机器**上运行和测试
- 需要管理员权限
- 运行前先安装并启动 Claude Desktop
- 适配 0811 版本

## 🔧 打包 exe（可选）
在 Windows 机器上：
```cmd
pip install pyinstaller
pyinstaller --onefile --name patch_claude_3p_windows_0811 ^
  --add-data "resources;resources" ^
  patch_claude_3p_windows_0811.py
```

---

**更新日期**: 2026-09-03  
**系统要求**: Windows 10/11 64位 + Python 3.8+
