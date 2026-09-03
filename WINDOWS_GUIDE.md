# Windows 使用指南

本文档说明如何在 Windows 上使用 `patch_claude_3p_windows.py` 为 Claude Desktop 打补丁。

---

## 前置条件

1. **Python 3.8+** 已安装（推荐 Python 3.10+）
2. **Claude Desktop** 已安装
3. **管理员权限**（写入注册表策略需要）

---

## 快速开始

### 1. 检查 Claude 安装位置

脚本会自动查找以下位置：

```
%LOCALAPPDATA%\Programs\Claude\Claude.exe
%PROGRAMFILES%\Claude\Claude.exe
```

手动确认：

```powershell
# 检查 LOCALAPPDATA
dir "$env:LOCALAPPDATA\Programs\Claude\Claude.exe"

# 检查 PROGRAMFILES
dir "$env:PROGRAMFILES\Claude\Claude.exe"
```

### 2. Dry-run 检查（不修改文件）

```powershell
cd C:\Path\To\Claude-Desktop-3P-Patch

# 仅检查 3P patch
python patch_claude_3p_windows.py --dry-run --write-policy --report-json C:\temp\claude-dryrun.json

# 检查 3P patch + 中文汉化
python patch_claude_3p_windows.py --dry-run --zh-cn --write-policy --report-json C:\temp\claude-dryrun.json
```

输出示例：

```
Claude root: C:\Users\YourName\AppData\Local\Programs\Claude
ASAR: would_patch
  applied         L1 managed config safeParse bypass [.vite/build/index.chunk-XXX.js]
  applied         L2c gateway model route validator bypass [.vite/build/index.chunk-YYY.js]
  ...
Registry policy: would_write
```

### 3. 正式 Patch（需要管理员权限）

**方法一：右键 "以管理员身份运行" PowerShell**

```powershell
cd C:\Path\To\Claude-Desktop-3P-Patch

# 基础版本（仅 3P patch）
python patch_claude_3p_windows.py --write-policy --report-json C:\temp\claude-patched.json

# 完整版本（3P patch + 中文汉化）
python patch_claude_3p_windows.py --zh-cn --write-policy --report-json C:\temp\claude-patched.json
```

**方法二：使用 `Start-Process` 提权**

```powershell
Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", "cd 'C:\Path\To\Claude-Desktop-3P-Patch'; python patch_claude_3p_windows.py --write-policy"
```

### 4. 验证结果

检查输出：

```
ASAR: patched
  applied         L1 managed config safeParse bypass
  applied         L2c gateway model route validator bypass
  applied         L4 force auto-update early return
  applied         L5 inference model catalog throw bypass
  applied         L6 session title fallback
  applied         L3b claude-swift virtualization support
Registry policy: written
```

检查注册表（可选）：

```powershell
reg query "HKLM\SOFTWARE\Policies\Anthropic\Claude" /v disableAutoUpdates
```

应该看到：

```
disableAutoUpdates    REG_DWORD    0x1
```

### 5. 重启 Claude

```powershell
Stop-Process -Name "Claude" -ErrorAction SilentlyContinue
Start-Process "$env:LOCALAPPDATA\Programs\Claude\Claude.exe"
```

---

## 参数说明

| 参数 | 说明 |
|---|---|
| `--app <path>` | 指定 Claude 安装根目录（包含 Claude.exe 的目录） |
| `--dry-run` | 只检查 patch 命中情况，不修改文件 |
| `--write-policy` | 写入注册表策略禁用自动更新（需要管理员权限） |
| `--provider <type>` | 指定 provider 类型（gateway/anthropic/bedrock 等），仅影响报告 |
| `--report-json <path>` | 输出 JSON 格式报告 |

---

## 常见问题

### Q1: 提示 "Claude not found"

**解决**：手动指定路径

```powershell
python patch_claude_3p_windows.py --app "C:\Custom\Path\To\Claude" --write-policy
```

### Q2: 注册表写入失败 "permission_denied"

**原因**：没有管理员权限

**解决**：右键 PowerShell 选择 "以管理员身份运行"

### Q3: Python 命令不存在

**解决**：
1. 安装 Python 3：https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"
3. 或使用完整路径：`C:\Python310\python.exe patch_claude_3p_windows.py ...`

### Q4: 需要中文汉化怎么办？

**已支持！** 使用 `--zh-cn` 参数：

```powershell
python patch_claude_3p_windows.py --zh-cn --write-policy
```

支持的语言：
- `--zh-cn`：简体中文（24019 key 完整翻译）
- `--lang zh-TW`：繁体中文（中国台湾）
- `--lang zh-HK`：繁体中文（中国香港）

### Q5: Patch 后 Claude 无法启动

**排查步骤**：

1. 检查 ASAR 文件是否损坏：
   ```powershell
   python -c "import json; data=open(r'%LOCALAPPDATA%\Programs\Claude\resources\app.asar','rb').read(); print('ASAR size:', len(data))"
   ```

2. 恢复原版（重新安装 Claude Desktop）

3. 重新执行 dry-run 确认所有层命中后再正式 patch

---

## Patch 层说明

Windows 版本与 macOS 版本使用**完全相同**的 patch 逻辑：

| 层 | 说明 |
|---|---|
| L1 | managed config safeParse bypass — 绕过严格的配置校验 |
| L2 | model white-list bypass — 放开模型选择器白名单 |
| L2c | gateway model route validator bypass — 绕过 gateway 路由校验 |
| L4 | force auto-update early return — 强制禁用自动更新 |
| L5 | inference model catalog throw bypass — 绕过推理模型目录检查 |
| L6 | session title fallback — 会话标题生成失败时使用首条消息兜底 |
| L3b | claude-swift virtualization support — 虚拟化支持检测 |

---

## 与 macOS 版本的差异

| 特性 | macOS | Windows |
|---|---|---|
| ASAR patch | ✅ 完全支持 | ✅ 完全支持 |
| 禁用自动更新 | ✅ defaults write | ✅ 注册表 |
| 代码签名 | ✅ codesign | ❌ 不需要 |
| 中文汉化 | ✅ 24019 key | ✅ 24019 key |
| 本地功能恢复 | ✅ 完整支持 | ⏳ 待移植 |
| DMG 处理 | ✅ hdiutil | ❌ Windows 用 .exe |

---

## 开发说明

### ASAR 结构（Windows）

```
Claude/
├── Claude.exe
├── resources/
│   ├── app.asar              ← 主要 patch 目标
│   └── app.asar.unpacked/    ← 未打包资源（汉化目标）
└── ...
```

### 注册表策略位置

```
HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Anthropic\Claude
    disableAutoUpdates = 1 (REG_DWORD)
```

### 测试环境

推荐在虚拟机或测试环境中先验证：

1. Windows 10 21H2+ / Windows 11
2. Python 3.10+
3. Claude Desktop 1.26832.0（与当前 macOS 版本对齐）

---

## 贡献与反馈

- macOS 主脚本：`patch_claude_3p_v2.py`
- Windows 主脚本：`patch_claude_3p_windows.py`
- 问题反馈：提交 Issue 或查看 [AGENTS.md](AGENTS.md)

---

## 许可

本项目仅供学习和研究使用。使用本脚本修改 Claude Desktop 可能违反 Anthropic 的服务条款。
