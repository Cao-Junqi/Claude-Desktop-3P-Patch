# 项目结构说明 (2026-09-03)

## 📁 完整目录树

```
Claude-Desktop-3P-Patch/
│
├── macOS/                                    🍎 macOS 平台（本机更新）
│   ├── patch_claude_3p_macos_0811.py       (53KB) 第三方模型 patch
│   ├── patch_claude_zhcn_macos.py          (67KB) 中文汉化脚本
│   ├── resources/                           汉化资源（20 个文件）
│   └── README.md                            使用说明
│
├── Windows/                                  🪟 Windows 平台（Windows 机器更新）
│   ├── patch_claude_3p_windows_0811.py     (23KB) 主脚本
│   ├── resources/                           汉化资源（20 个文件）
│   ├── Windows-Delivery-Package/           完整交付包（需 Windows 更新）
│   │   ├── Claude-Setup-x64.exe           (126MB) 官方安装包
│   │   ├── install.bat                    一键安装脚本
│   │   ├── patch_claude_3p_windows.py     独立脚本
│   │   ├── resources/                      汉化资源
│   │   ├── README.txt                      快速指南
│   │   └── TROUBLESHOOTING.md             故障排除
│   └── README.md                            使用说明
│
├── resources/                                📦 根目录资源备份（20 个文件）
│   ├── frontend-zh-CN.json                 (1.5MB) 前端翻译 24019 keys
│   ├── desktop-zh-CN.json                  (19KB) 桌面端翻译
│   ├── statsig-zh-CN.json                  (2.4KB) 统计配置
│   └── ...                                  其他语言和资源
│
├── translations/                             📝 翻译工具（开发用）
│   ├── check_and_merge.py                  校验和合并工具
│   ├── README.md                            翻译管线说明
│   └── batch-*.json                         翻译批次文件
│
├── Windows-Project-Docs/                    📚 Windows 项目文档（归档）
│   ├── README_WINDOWS_PROJECT.md           项目报告
│   ├── WINDOWS_DELIVERY.md                 交付报告
│   └── WINDOWS_TEST_STATUS.md              测试状态
│
├── README.md                                 📖 主文档
├── CLEANUP_SUMMARY.md                       🗑️ 清理总结
├── RESTRUCTURE_SUMMARY.md                   🔄 重构总结
├── CHANGELOG.md                             📋 更新日志
├── SOP.md                                   📝 标准操作流程
├── HANDOFF.md                               🤝 交接文档
├── .gitignore                               🚫 Git 忽略规则
│
└── (其他文档)
    ├── BUILD_EXE_GUIDE.md
    ├── WINDOWS_GUIDE.md
    ├── INSTALL_APPLICATION_PATCH.md
    └── ...
```

## 📊 文件统计

| 类型 | macOS | Windows | 共享 |
|-----|-------|---------|------|
| 主脚本 | 2 个 | 1 个 | - |
| 汉化资源 | 20 个 | 20 个 | 20 个备份 |
| 文档 | 1 个 README | 1 个 README | 根目录多个 |
| 交付包 | - | 1 个完整包 (126MB) | - |

## 🎯 核心文件说明

### macOS 核心
1. **patch_claude_3p_macos_0811.py** (53KB)
   - 适配 Claude Desktop 0811 (1.26832.0)
   - 第三方模型解锁 (OpenAI/Azure/自定义)
   - 需要 sudo 权限

2. **patch_claude_zhcn_macos.py** (67KB)
   - 完整中文汉化
   - 24000+ 条自研翻译
   - 需要 sudo 权限和 --user-home 参数

### Windows 核心
1. **patch_claude_3p_windows_0811.py** (23KB)
   - 适配 Claude Desktop 0811
   - 第三方模型解锁 + 中文汉化
   - 需要管理员权限

2. **Windows-Delivery-Package/** (完整交付包)
   - 包含官方安装包 Claude-Setup-x64.exe (126MB)
   - 一键安装脚本 install.bat
   - 独立 patch 脚本和资源
   - 用户文档

### 汉化资源 (自研)
- **frontend-zh-CN.json** (1.5MB) - 24019 keys, 20436 translated
- **desktop-zh-CN.json** (19KB) - 桌面端翻译
- **statsig-zh-CN.json** (2.4KB) - 统计配置翻译
- **Localizable.strings** (3.4KB) - 原生字符串
- 其他：zh-TW (繁体台湾), zh-HK (繁体香港) 版本

## ⚠️ 重要说明

### Git 管理
- ✅ **已提交**: 脚本、资源、文档
- 🚫 **不提交**: `*.exe`, `*.dmg` (在 .gitignore 中)
- ⚠️ **注意**: Windows-Delivery-Package/Claude-Setup-x64.exe (126MB) 不会被 git 提交

### 更新位置
- **macOS 脚本**: 在本机 Mac 上更新和测试
- **Windows 脚本**: 必须在 Windows 机器上更新和测试
- **Windows 交付包**: 更新后需要在 Windows 机器上重新打包

### 分发方式
1. **代码仓库**: 只包含脚本和资源（不含 exe）
2. **Windows 交付包**: 通过局域网或 U 盘分发（包含 exe）

## 🔄 更新流程

### macOS 更新
```bash
cd macOS
# 修改 patch_claude_3p_macos_0811.py
# 测试
sudo python3 patch_claude_3p_macos_0811.py
# 提交
git add macOS/
git commit -m "更新 macOS 脚本"
```

### Windows 更新
```bash
# 在 Windows 机器上
cd Windows
# 修改 patch_claude_3p_windows_0811.py
# 测试
python patch_claude_3p_windows_0811.py
# 同步到 Windows-Delivery-Package
cp patch_claude_3p_windows_0811.py Windows-Delivery-Package/patch_claude_3p_windows.py
# 提交（不含 exe）
git add Windows/
git commit -m "更新 Windows 脚本"
```

---

**最后更新**: 2026-09-03  
**目录结构**: 清晰 | 平台分离 | 易维护
