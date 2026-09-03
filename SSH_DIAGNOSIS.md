# SSH 连接诊断报告

## 连接信息
- **公网地址**: 113.219.237.121:34140
- **用户名**: VZAN
- **端口连通性**: ✅ 成功（nc 测试通过）
- **SSH 握手**: ✅ 主机密钥已添加
- **认证状态**: ⏳ 挂起（连接后无响应）

## 问题分析

端口可达且 SSH 握手成功，但后续命令执行挂起，可能原因：

1. **密钥认证配置问题**
   - `authorized_keys` 文件未正确配置
   - 文件权限不正确（Windows ICACLS 权限）
   - 密钥格式不匹配

2. **Windows OpenSSH 配置问题**
   - 默认 shell 未正确设置
   - PowerShell 执行策略限制
   - 用户环境变量未加载

3. **反代配置问题**
   - TCP 反代超时时间过短
   - 反代层吞掉了某些 SSH 控制字符
   - 长连接 keep-alive 未正确配置

## 建议排查步骤

### 在 Windows 机器上执行

```powershell
# 1. 检查 OpenSSH 服务状态
Get-Service sshd | Select-Object Name, Status, StartType

# 2. 检查 SSH 配置
Get-Content C:\ProgramData\ssh\sshd_config | Select-String -Pattern "PubkeyAuthentication|PasswordAuthentication|AuthorizedKeysFile"

# 3. 检查密钥文件权限
icacls C:\Users\VZAN\.ssh\authorized_keys

# 4. 查看 SSH 服务日志
Get-EventLog -LogName Application -Source sshd -Newest 20 | Format-List

# 5. 测试本地连接
ssh VZAN@localhost

# 6. 临时启用密码认证测试（可选）
# 编辑 C:\ProgramData\ssh\sshd_config
# 将 PasswordAuthentication 改为 yes
# 重启服务：Restart-Service sshd
```

### 建议的快速解决方案

**方案 A：使用密码认证**
```powershell
# Windows 端临时启用密码认证
# 编辑 C:\ProgramData\ssh\sshd_config
PasswordAuthentication yes
# 重启 sshd
Restart-Service sshd
```

然后从 macOS 端测试：
```bash
ssh -p 34140 VZAN@113.219.237.121
# 输入密码
```

**方案 B：修复密钥权限**
```powershell
# Windows 端重新设置 authorized_keys 权限
$keyPath = "C:\Users\VZAN\.ssh\authorized_keys"
icacls $keyPath /inheritance:r
icacls $keyPath /grant:r "VZAN:(F)"
icacls $keyPath /grant:r "NT AUTHORITY\SYSTEM:(F)"

# 重启 SSH 服务
Restart-Service sshd
```

**方案 C：直接在 Windows 机器上测试**

如果 SSH 问题持续，可以直接在 Windows 机器上本地测试 patch 脚本：

1. 将 `Windows-Delivery-Package` 文件夹复制到 Windows 机器（U盘或网络共享）
2. 在 Windows 机器上以管理员身份打开 PowerShell
3. 执行测试流程（参考 `快速测试步骤.txt`）

## 下一步行动

建议用户：
1. 先在 Windows 机器上执行诊断命令
2. 选择方案 A（密码认证）或方案 B（修复密钥）
3. 或直接在 Windows 机器本地测试，不通过 SSH

---

**更新时间**: 2026-09-03 11:25
