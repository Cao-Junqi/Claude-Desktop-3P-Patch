# Windows 独立可执行文件打包说明

## 问题：跨平台打包限制

在 macOS 上无法直接打包 Windows 可执行文件（PyInstaller 架构不兼容）。

## 解决方案

### 方案 A：在 Windows 机器上本地打包（推荐）

1. **在你的 Windows 测试机（192.168.50.39）上执行**：

```powershell
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 进入项目目录
cd C:\Path\To\Claude-Desktop-3P-Patch

# 3. 打包为独立可执行文件
pyinstaller --onefile --name patch_claude_3p_windows `
  --add-data "resources;resources" `
  patch_claude_3p_windows.py

# 4. 打包完成，文件位于：
# dist\patch_claude_3p_windows.exe (约 10-15MB)

# 5. 复制到交付包
copy dist\patch_claude_3p_windows.exe Windows-Delivery-Package\
```

### 方案 B：使用 GitHub Actions 自动打包

已创建 `.github/workflows/build-windows-exe.yml`，推送代码后自动在 GitHub 的 Windows 环境中打包。

1. 推送代码到 GitHub
2. GitHub Actions 自动构建
3. 下载生成的 `patch_claude_3p_windows.exe`
4. 放入 `Windows-Delivery-Package/`

### 方案 C：使用 Docker + Wine（复杂）

需要配置 Wine 环境模拟 Windows，不推荐。

## 当前状态

- ✅ Python 脚本已完成（`patch_claude_3p_windows.py`）
- ✅ 打包配置已创建（GitHub Actions workflow）
- ⏳ 需要在 Windows 环境中执行打包
- ⏳ 生成独立可执行文件（约 10-15MB）

## 一旦打包完成

将 `patch_claude_3p_windows.exe` 放入 `Windows-Delivery-Package/`，学员就可以：

1. **无需安装 Python**
2. 右键 `patch_claude_3p_windows.exe` → "以管理员身份运行"
3. 按提示完成安装

## 临时方案

如果急需交付，当前版本要求学员安装 Python 3.8+，`install.bat` 会检查并提示。

---

**推荐行动**：SSH 连接成功后，直接在 Windows 机器上执行 PyInstaller 打包。
