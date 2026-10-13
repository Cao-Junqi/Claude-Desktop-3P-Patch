# Claude Desktop 2.31226.1 Patch 测试报告

## 测试时间
2026-10-13

## 版本信息
- **Claude Desktop 版本**: `2.31226.1`
- **上一版本**: `2.2553.1`（0918）
- **来源**: 本机 `/Applications/Claude.app` 官方安装版（复制到 `/tmp/claude-new` 分析，未用 DMG）
- **3P 脚本**: `patch_claude_3p_macos_0921.py`（追加 2.31226 特征码）
- **汉化脚本**: `patch_claude_zhcn_macos_0921.py`
- **安装目标**: `/Applications/Claude.app`

## 本次核心发现

### 1. 三层特征码失效（L1 / L10 / L12）

| 层 | 2.2553 旧形态 | 2.31226 新形态 | 文件 |
|---|---|---|---|
| L1 | `uOt`/`vOt` 两个 helper 校验器 | 改名 `rUt`（clientSecretHelper strict）/ `dUt`（envHelper record） | `index.chunk-Cyt2WTko.js` |
| L10 | `o=t.state==="set"&&n.some(e=>q(e,t.value))?t:void 0` | `s=t.state==="set"&&o.some(e=>D(e,t.value))?t:void 0` | `c593f7513-DQShcHgn.js` |
| L12 | `C!==void 0&&T.push(\`--setting-sources=${C.join(",")}\`)` | `ee!==void 0&&w.push(Y7("--setting-sources",ee.join(",")))`（改用 `Y7()` helper） | `index.chunk-D6Q00DJz.js` |

### 2. ⚠️ 首轮 dry-run 的 L2d 假命中

首轮 dry-run 报 L2d「applied ×2」，但**幂等复检报 missing**。原因：命中的是两条兜底分支
（Bedrock / Vertex 的 reason 字符串），真正的共享黑名单门已从 `wt` 改名 `pr`，
且黑名单/白名单/列表局部变量从 `Ct`/`xt`/`St` 改为 `fr`/`ur`/`dr`：

```
function pr(e){let t=e.toLowerCase();return fr.test(t)?!1:ur.test(t)||dr.some(e=>t.includes(e))}
```

旧特征串完全不匹配 → renderer 仍会拦 minimax/glm/deepseek 等 3P 模型名。已追加门特征码
（pin `t` 到 `` `claude` ``）与前后置检测 needle，恢复幂等。

> **教训**：dry-run 必须配合幂等复检；「applied 条数」不能只看数量，要看是否含关键门层。

## Patch 结果

### ASAR 层（app.asar 内）

| 层 | 描述 | 文件 | 偏移量 | 状态 |
|---|---|---|---|---|
| L1 | custom3p helper 校验器（×2） | `index.chunk-Cyt2WTko.js` | 2114065, 2116202 | ✅ applied ×2 |
| L2 | model picker allowlist | `index.chunk-epGqPC4W.js` | 516388 | ✅ applied |
| L2c | 主进程 provider 校验器 | `index.chunk-Cyt2WTko.js` | 537381 | ✅ applied |
| L2c | preload 校验器 | `index.pre.js` | 334222 | ✅ applied |
| L4 | auto-update 早期返回 | `index.chunk-Cyt2WTko.js` | 3922471–4316814 | ✅ applied ×5 |
| L6 | session title 兜底 | `index.chunk-Cyt2WTko.js` | 4261777, 4262091 | ✅ applied ×2 |
| L11 | 会话 settingSources 隔离 | `index.chunk-BCHP6ll9.js` + `index.chunk-QEr06WaZ.js` | 1490161, 362859 | ✅ applied ×2 |
| L12 | 空 setting-sources 不拼参数 | `index.chunk-D6Q00DJz.js` | 1108353 | ✅ applied |
| L3b | swift 虚拟化支持 | `claude-swift/js/index.js` | 3372 | ✅ applied |

### renderer 层（ion-dist，ASAR 外）

| 层 | 描述 | 文件 | 状态 |
|---|---|---|---|
| L2d | 门 `pr`（fr/ur/dr）+ Bedrock / Vertex 分支 | `c6f6cf4c2-Cu4nXqjL.js` | ✅ applied ×3 |
| L9 | 语言列表数组 `w_`（+zh-CN/zh-TW/zh-HK） | `shared-50-Bmc9oUMm.js` | ✅ applied ×3 |
| L10 | picker availableModels 门控（`s=`/`o.some`/`D`） | `c593f7513-DQShcHgn.js` | ✅ applied |

### 无需 patch 的层

| 层 | 原因 |
|---|---|
| L2b | 终端 `.some()` 白名单自 0811 起已不存在 |
| L5 | `inferenceModels` 过滤只做剔除不抛错 |
| L7 | xhigh 原生被排除，解析器兜底 medium |

## 功能验证

### 静态检查
- ✅ `node --check`：ASAR 内 7 个被 patch 文件（按 header 正确偏移 `8+header_size` 提取）全部通过
- ✅ `node --check`：renderer **3333** 个 JS 全部通过
- ✅ 幂等复检：重跑全部 `already_applied`（L2b/L7 除外），语言数组无 `"zh-CN","zh-CN"` 重复

### 代码签名与完整性
- ✅ `codesign --verify`: valid on disk / satisfies its Designated Requirement（adhoc + runtime）
- ✅ `ElectronAsarIntegrity`: True（已更新）
- ✅ entitlements: virtualization=True, allow_jit=True, disable_library_validation=True

### 运行时
- ✅ App 从 `/Applications` 启动，主进程稳定 ≥1 分钟无崩溃、无 DiagnosticReports
- ✅ renderer 以 `--lang=zh-CN` 启动；managed config `deploymentMode:3p`
- ✅ 自动更新策略仍为禁用（`disableAutoUpdates system=True`）

## 汉化覆盖率

- 硬编码字符串替换：810 处 / 245 文件
- 前端 locale merge：16058 translated / 17900 fallback / 7706 extra old keys ignored
  （2.31226 的 en-US 文案基数继续增大，fallback 属新增内容而非回归；补齐流程见 `translations/README.md`）

## 安装记录

**⚠️ 本次安装方式与以往不同**：macOS App Management 拒绝非授权进程写入 app bundle 内部
（`PermissionError: Operation not permitted`，属主为当前用户、`/Applications` 目录可写也不行），
改为 **bundle 级替换**：

```bash
# 1. 原版移出备份
mv /Applications/Claude.app /Applications/Claude-backup-2.31226.1.app

# 2. 放入已 patch + 重签 + 验证过的副本（在 /tmp 内完成）
cp -R /tmp/claude-new-test/Claude.app /Applications/Claude.app
xattr -cr /Applications/Claude.app

# 3. 复检
codesign --verify --verbose=2 /Applications/Claude.app
python3 patch_claude_3p_macos_0921.py --app /Applications/Claude.app \
  --provider gateway --feature-recovery --zh-cn --dry-run   # 期望全部 already_applied
```

- 原版备份：`/Applications/Claude-backup-2.31226.1.app`
- 更早备份：`/Applications/Claude.backup-before-3p-v2-20260921-171748.app`（未动）

## 结论

✅ **2.31226.1 适配成功：L1/L10/L12 更新特征码，L2d 补共享门；全部实际层 applied，已装机生效。**

关键提醒：**L2d 的共享门（`wt`→`pr`）是本次最隐蔽的失效点** —— dry-run 表面 applied，
只有幂等复检才能暴露。后续适配新版必须重跑「已 patch App 的 dry-run」。

---

# 追加：L13 模型切换被 org 设置拒绝（同日修复）

## 症状

装机后选择发现的 3P 模型（`gemini-3.8-flash-high`、`anthropic/magpie-*`）弹出
「… is restricted by your organization('s settings) …」，会话继续用旧模型。

## 根因链（真机 CLI 探针逐条验证）

用 stream-json 协议直接驱动 CLI（`initialize` + `set_model` 控制请求）：

| 探针条件 | 结果 |
|---|---|
| `--setting-sources=user` + 切到 `gemini-3.8-flash-high` | ❌ `restricted_by_org`（用户白名单生效） |
| **不带 `--setting-sources`**（L12 现状） | ❌ 同样拒绝 —— **CLI 默认加载用户 settings** |
| `--setting-sources=`（显式空） | ✅ 放行，但用户技能/命令消失（命令数 182 → 51） |
| 默认来源 + `--managed-settings {"availableModels":[…]}` | ✅ 放行（policy 层覆盖用户层） |
| managed 白名单含基础 ID，切 `…[1m]` 变体 | ✅ 前缀匹配放行 |

结论：1) 技能与用户设置同源，无法靠 `--setting-sources` 解耦（L12 的副作用无法避免）；
2) 用户 `~/.claude/settings.json` 的 `availableModels: ["opus","sonnet","fable"]` 成为桌面会话的实际白名单；
3) 桌面 3P 本应在 managed settings 下发自己的白名单来覆盖，但 `ZBt()` 只在部署配置带
`inferenceModels` 时才有清单 —— 本机生效配置（"magpie"）没有该字段（走 discovery），于是什么都没下发。

## 修复（L13）与验证

`ZBt()` 的白名单改从 `resolvedModels()` 构造（该方法已内置「admin 清单优先、否则发现列表」，
并给条目打 `restricted`/`updateRequired` 标记），等长替换 165 → 143 字节：

```
L13:  offset 2085214   (.vite/build/index.chunk-Cyt2WTko.js)
```

- **真函数单测**（从补丁前后 bundle 提取 `ZBt` + 桩）：原版在 discovery 模式下不下发白名单（复现缺陷）；
  补丁版下发发现列表且排除 restricted/updateRequired；admin 清单与非 3P 路径行为不变
- `node --check` 通过；幂等复检 20 层 ASAR + 7 层 renderer 全 `already_applied`；codesign 通过
- 已 bundle 级替换装机并启动验证（原版备份 `/Applications/Claude-backup-2.31226.1.app` 保留）
