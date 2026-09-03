# Windows 安装失败诊断

## 问题：BAT/PS1 脚本一闪而过

这是典型的 Windows 脚本错误导致的立即退出。可能原因：

### 1. 编码问题（最常见）
macOS 创建的文本文件默认是 UTF-8 with BOM 或 LF 换行符，Windows 需要：
- **UTF-8 without BOM** 或 **ANSI**
- **CRLF 换行符**（`\r\n`）

### 2. PowerShell 执行策略限制
Windows 默认禁止运行未签名的 PS1 脚本。

### 3. 路径问题
文件路径或工作目录可能有特殊字符。

---

## 立即解决方案

### 方案 A：直接命令行执行（绕过脚本）

在 Windows 上以**管理员身份**打开 PowerShell，逐步执行：

```powershell
# 进入目录
cd "C:\Path\To\Windows-Delivery-Package"

# 1. 安装 Claude
.\Claude-Setup-x64.exe /S
Start-Sleep -Seconds 30

# 2. 应用 Patch（如果有 Python）
python patch_claude_3p_windows.py --zh-cn --write-policy --report-json C:\temp\patched.json

# 3. 查看结果
Get-Content C:\temp\patched.json

# 4. 启动 Claude
Start-Process "$env:LOCALAPPDATA\Programs\Claude\Claude.exe"
```

### 方案 B：修复文件编码

在 Windows 上重新创建 BAT 文件：

1. 用 **记事本** 打开 `install.bat`
2. 文件 → 另存为
3. **编码选择 ANSI**
4. 保存后重新运行

### 方案 C：解除 PowerShell 限制

```powershell
# 以管理员身份运行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后运行 PS1
.\verify_installation.ps1
```

---

## 我创建了简化版 BAT

已生成 `install_simple.bat`：
- 纯 ASCII 内容（无中文）
- 简化逻辑，减少出错点
- 保留所有 `pause` 确保能看到错误

**在 Windows 上测试**：
1. 右键 `install_simple.bat`
2. 以管理员身份运行
3. 如果仍然闪退，截图**第一行错误信息**

---

## 调试方法

如果脚本仍然闪退，在 Windows 上创建测试文件：

**test.bat**:
```batch
@echo off
echo Current directory: %CD%
echo.
echo Files in this directory:
dir /b
echo.
echo Press any key to continue...
pause
```

如果这个都闪退，说明是 Windows 环境配置问题（不是脚本问题）。

---

## 手动验证步骤

完全绕过脚本，手动验证每一步：

```powershell
# 1. 检查文件
Get-ChildItem

# 2. 检查 Python
python --version

# 3. 安装 Claude（双击 exe 或命令行）
.\Claude-Setup-x64.exe /S

# 4. 等待
Start-Sleep -Seconds 30

# 5. 检查是否安装成功
Test-Path "$env:LOCALAPPDATA\Programs\Claude\Claude.exe"

# 6. Dry-run 测试
python patch_claude_3p_windows.py --dry-run --zh-cn

# 7. 正式 Patch
python patch_claude_3p_windows.py --zh-cn --write-policy
```

---

**请在 Windows 上尝试：**
1. 用 `install_simple.bat`（新生成的英文版）
2. 或直接在 PowerShell 中逐行执行命令
3. 截图第一个报错信息，我来针对性修复
