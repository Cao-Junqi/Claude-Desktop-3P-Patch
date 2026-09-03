# Claude Desktop 3P Patch

Claude Desktop 第三方模型解锁 + 中文汉化工具

**当前适配版本**: Claude Desktop 0811 (1.26832.0)  
**汉化翻译**: 自研，24000+ 条专业翻译（2026-08-11 完成）  
**最后更新**: 2026-09-03

---

## 📋 更新日志

### 2026-09-03 - 项目重构
- ✅ 按平台分离目录结构（macOS / Windows）
- ✅ 脚本重命名并标注适配版本（0811）
- ✅ 清理自动构建流程和无用脚本
- ✅ 各平台独立维护资源和文档
- ✅ 更新 .gitignore，不对外提交内部文档

### 2026-09-03 - Windows 适配 + macOS L6 修复
- ✅ Windows 版本完整适配（3P patch + 中文汉化）
- ✅ 修复 macOS L6 层长度计算错误
- ✅ 完善 Windows 使用文档和交付包

### 2026-08-11 - 适配 0811 + 汉化全量补全
- ✅ 适配 Claude Desktop 0811 (1.26832.0)
- ✅ 多文件扫描支持（250+ chunk 文件）
- ✅ 汉化从 12355 → 24019 keys (11664 条新增)
- ✅ 翻译质量：20436 translated / 0 fallback

### 2026-07-03 - 初始版本
- ✅ 第三方模型解锁
- ✅ 禁用自动更新
- ✅ 中文汉化基础版本

---

## 📦 项目结构

```
Claude-Desktop-3P-Patch/
│
├── macOS/                                    🍎 macOS 平台
│   ├── patch_claude_3p_macos_0811.py       第三方模型 patch
│   ├── patch_claude_zhcn_macos.py          中文汉化脚本
│   ├── resources/                           汉化资源文件
│   └── README.md                            macOS 使用说明
│
├── Windows/                                  🪟 Windows 平台
│   ├── patch_claude_3p_windows_0811.py     第三方模型 patch + 汉化
│   ├── resources/                           汉化资源文件
│   ├── Windows-Delivery-Package/           完整交付包（129MB）
│   │   ├── Claude-Setup-x64.exe           官方安装包
│   │   ├── install.bat                    一键安装脚本
│   │   ├── README.txt                     快速指南
│   │   └── ...
│   └── README.md                            Windows 使用说明
│
├── translations/                             📝 翻译工具和批次文件
│   ├── check_and_merge.py                  校验和合并工具
│   └── README.md                            翻译管线说明
│
├── resources/                                📦 根目录资源（备份）
└── Windows-Project-Docs/                    📚 Windows 项目文档
```

---

## 🎯 快速开始

### macOS 用户

```bash
# 进入 macOS 目录
cd macOS

# 第三方模型 patch
sudo python3 patch_claude_3p_macos_0811.py

# 中文汉化（可选）
sudo python3 patch_claude_zhcn_macos.py --user-home "$HOME"
```

详见 [macOS/README.md](macOS/README.md)

### Windows 用户

**方式 1：使用交付包（推荐）**
1. 进入 `Windows/Windows-Delivery-Package/` 目录
2. 双击 `Claude-Setup-x64.exe` 安装
3. 启动 Claude Desktop（保持运行）
4. 右键 `install.bat` → "以管理员身份运行"
5. 重启 Claude Desktop

**方式 2：使用 Python 脚本**
```bash
cd Windows
python patch_claude_3p_windows_0811.py
```

详见 [Windows/README.md](Windows/README.md)

**⚠️ Windows 版本需在 Windows 机器上更新和测试**

---

## ✨ 功能特性

- ✅ **第三方模型支持** - OpenAI/Azure/自定义模型
- ✅ **完整中文汉化** - 24000+ 自研专业翻译
- ✅ **智能安装** - 自动检测路径、关闭进程
- ✅ **禁用自动更新** - 保持 patch 有效
- ✅ **跨平台支持** - macOS + Windows

---

## 📊 项目状态

| 平台 | 脚本版本 | 适配 Claude 版本 | 状态 | 更新位置 |
|------|---------|-----------------|------|---------|
| macOS | 0811 | 1.26832.0 | ✅ 完成 | 本机 Mac |
| Windows | 0811 | Windows 版 | ✅ 完成 | Windows 机器 |

---

## 🚀 分发建议

**Windows 交付包分发**：

1. **局域网分发（推荐）**
   - 上传 `Windows/Windows-Delivery-Package/` 到内网服务器
   - 用户下载后按 README.txt 操作

2. **U盘分发**
   - 复制整个 `Windows-Delivery-Package/` 到 U盘
   - 用户复制到本地后操作

---

## 📝 更新流程

### macOS 版本更新
1. 在本机 Mac 更新 `macOS/patch_claude_3p_macos_0811.py`
2. 更新 `macOS/resources/` 汉化资源（如需要）
3. 测试后提交

### Windows 版本更新
1. 在 Windows 机器上更新 `Windows/patch_claude_3p_windows_0811.py`
2. 更新 `Windows/resources/` 汉化资源（如需要）
3. 更新 `Windows/Windows-Delivery-Package/` 中的文件
4. 测试后提交

---

**最后更新**: 2026-09-03  
**维护者**: 项目团队  
**许可**: 内部使用
