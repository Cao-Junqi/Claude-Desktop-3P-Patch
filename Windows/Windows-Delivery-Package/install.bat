@echo off
chcp 65001 >nul

REM 切换到脚本所在目录
cd /d "%~dp0"

echo ========================================
echo Claude Desktop 3P Patch
echo 中文汉化 + 第三方模型支持
echo ========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 需要管理员权限！
    echo 请右键此文件，选择"以管理员身份运行"
    echo.
    pause
    exit /b 1
)

echo [1/4] 检查管理员权限... OK
echo.

REM 查找 Claude 安装路径
echo [2/4] 查找 Claude 安装位置...
set "CLAUDE_PATH="
set "CLAUDE_EXE="

REM 方法 1: 从正在运行的进程获取路径
for /f "usebackq tokens=*" %%a in (`powershell -Command "Get-Process Claude -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path"`) do (
    set "CLAUDE_EXE=%%a"
)

REM 方法 2: 检查标准安装位置
if not defined CLAUDE_EXE (
    if exist "%LOCALAPPDATA%\Programs\Claude\Claude.exe" (
        set "CLAUDE_EXE=%LOCALAPPDATA%\Programs\Claude\Claude.exe"
    ) else if exist "%PROGRAMFILES%\Claude\Claude.exe" (
        set "CLAUDE_EXE=%PROGRAMFILES%\Claude\Claude.exe"
    )
)

if not defined CLAUDE_EXE (
    echo [错误] 未找到 Claude Desktop！
    echo.
    echo 请先启动 Claude Desktop，让它运行着，
    echo 然后再次运行此脚本（会自动从进程获取路径并关闭）
    echo.
    pause
    exit /b 1
)

REM 提取安装目录
for %%F in ("%CLAUDE_EXE%") do set "CLAUDE_PATH=%%~dpF"
set "CLAUDE_PATH=%CLAUDE_PATH:~0,-1%"

echo [OK] 找到 Claude: %CLAUDE_EXE%
echo [OK] 安装目录: %CLAUDE_PATH%
echo.

REM 检查版本（检查 app.asar 是否存在）
if not exist "%CLAUDE_PATH%\resources\app.asar" (
    echo [错误] Claude 安装不完整（缺少 app.asar）
    echo 路径: %CLAUDE_PATH%\resources\app.asar
    echo.
    pause
    exit /b 1
)

echo [OK] Claude 版本检查通过
echo.

REM 停止 Claude 进程
echo [3/4] 停止 Claude 进程...
tasklist /FI "IMAGENAME eq Claude.exe" 2>NUL | find /I /N "Claude.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [提示] 正在关闭 Claude 进程...
    taskkill /F /IM Claude.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
    echo [OK] Claude 已关闭
) else (
    echo [OK] Claude 未运行
)
echo.

REM 检查运行环境
echo [4/4] 应用 Patch...

if exist "patch_claude_3p_windows.exe" (
    echo [OK] 使用独立可执行文件
    set "PATCH_CMD=patch_claude_3p_windows.exe"
) else (
    python --version >nul 2>&1
    if errorLevel 1 (
        echo [错误] 需要 Python 3.8+ 或 patch_claude_3p_windows.exe
        echo.
        echo 下载 Python: https://python.org/downloads/
        echo 安装时勾选 "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
    echo [OK] 使用 Python 脚本
    set "PATCH_CMD=python patch_claude_3p_windows.py"
)

REM 执行 Patch
echo.
echo 正在 patch: %CLAUDE_PATH%
echo.
%PATCH_CMD% --app "%CLAUDE_PATH%" --zh-cn --write-policy --report-json "%TEMP%\claude-patched.json"

if %errorLevel% neq 0 (
    echo.
    echo [错误] Patch 失败
    echo 详细日志: %TEMP%\claude-patched.json
    echo.
    pause
    exit /b 1
)

REM 显示结果
echo.
echo ========================================
if exist "%TEMP%\claude-patched.json" (
    type "%TEMP%\claude-patched.json"
    echo.
)
echo ========================================
echo 安装成功！
echo ========================================
echo.
echo 已完成：
echo   - 第三方模型限制解除
echo   - 中文汉化（24019 条）
echo   - 自动更新已禁用
echo.
echo 现在可以启动 Claude 了
echo.
pause
