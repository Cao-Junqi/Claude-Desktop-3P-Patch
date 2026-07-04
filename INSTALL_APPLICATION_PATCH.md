# 本地 `/Applications/Claude.app` 全功能 Patch 命令

适用场景：你已经把新版 `Claude.app` 放到了：

```text
/Applications/Claude.app
```

然后希望直接对系统里的 Claude Desktop 执行：

- 3P / Gateway 模型兼容 patch；
- 自动更新禁用；
- 本地功能恢复；
- Claude Code / MCP / extension 相关偏好启用；
- 中文汉化；
- 中文语言选择器白名单修复；
- 重签名；
- 启动 Claude。

---

## 1. 先退出 Claude

```bash
osascript -e 'quit app "Claude"' 2>/dev/null || true
```

---

## 2. 先执行 dry-run，不修改 App

```bash
python3 patch_claude_3p_v2.py \
  --app /Applications/Claude.app \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --dry-run \
  --report-json /tmp/claude-3p-installed-dryrun.json
```

检查输出里是否有类似内容：

```text
ASAR: would_patch
L1/L2/L2b/L2c/L4/L6/L7/L3b 命中
Local feature UI patch: would_patch
Localization: would_patch zh-CN 简体中文
```

---

## 3. 正式 patch `/Applications/Claude.app`

确认 dry-run 正常后执行：

```bash
sudo python3 patch_claude_3p_v2.py \
  --app /Applications/Claude.app \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --write-policy \
  --launch \
  --report-json /tmp/claude-3p-installed-patched.json
```

---

## 4. 参数说明

| 参数 | 作用 |
|---|---|
| `--app /Applications/Claude.app` | 直接 patch 系统 Applications 里的 Claude.app |
| `--provider gateway` | 按 gateway/3P 模式输出能力报告 |
| `--feature-recovery` | 启用本地功能恢复组合项 |
| `--zh-cn` | 安装简体中文汉化资源 |
| `--local-market-report` | 扫描本地 skills/plugins/extensions |
| `--write-policy` | 写入系统级禁用自动更新 policy |
| `--launch` | patch 完成后启动 Claude |
| `--report-json` | 输出 JSON 报告，方便排查 |

---

## 5. 预期成功输出

正式 patch 成功时应看到类似内容：

```text
ASAR: patched
Signing: signed
codesign verify: OK
Local feature UI patch: patched
Localization: patched zh-CN 简体中文
```

如果中文语言选择器修复成功，应看到：

```text
Patched language whitelist: c4b350ac1-BTR_0NaM.js
```

或者：

```text
Language whitelist already contains zh-CN
```

---

## 6. Patch 后检查

启动 Claude 后检查：

1. App 是否能正常打开；
2. 模型下拉框是否能看到 3P/Gateway 模型；
3. 设置里的语言选择器是否出现"简体中文"；
4. 选择"简体中文"后 UI 是否切换；
5. Claude Code / MCP / extension 相关入口是否可见；
6. 会话标题是否不再全部相同。

---

## 7. 如果失败

### 启动失败

直接运行 binary 看错误：

```bash
/Applications/Claude.app/Contents/MacOS/Claude
```

### 查看报告

```bash
open /tmp/claude-3p-installed-patched.json
```

### 重新从新版 App 开始

如果你重新覆盖安装了 Claude Desktop，需要再次运行本 patch 命令。

---

## 8. 最短正式命令

如果你已经确认 dry-run 没问题，可以直接用这一条：

```bash
osascript -e 'quit app "Claude"' 2>/dev/null || true && \
sudo python3 patch_claude_3p_v2.py \
  --app /Applications/Claude.app \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --local-market-report \
  --write-policy \
  --launch \
  --report-json /tmp/claude-3p-installed-patched.json
```
