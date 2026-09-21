# Claude Desktop 2.2553.1 (0921) Patch 测试报告

## 测试时间
2026-09-21

## 版本信息
- **Claude Desktop 版本**: `2.2553.1`（构建日 2026-09-18）
- **上一版本**: `1.44121.4`（0903）
- **DMG**: `~/Downloads/Claude.dmg`
- **3P 脚本**: `patch_claude_3p_macos_0921.py`
- **汉化脚本**: `patch_claude_zhcn_macos_0921.py`
- **安装目标**: `/Applications/Claude.app`

## 本次核心发现

`Contents/Resources/ion-dist/` **不在 `app.asar` 内**。此前所有 patch 层只扫 `.vite/build/`
（主进程），漏掉了渲染进程——它带着**独立的一份**模型校验器和语言列表。这是用户报告的
两个问题的根因：

| 现象 | 根因 | 新增层 |
|---|---|---|
| 报 `Doesn't look like an Anthropic model: 需要一个引用 Anthropic 模型的网关模型路由…` | 只补了主进程 `Yo()`，渲染进程 `At()` 仍是旧的 | **L2d** |
| 语言文件已装好，但 Settings → Language 无中文 | 语言下拉框读硬编码数组 `Am`，`zh-CN` 不在其中 | **L9** |

这两个文件带内容哈希（如 `ce459c687-B4NlOXPM.js`），每个版本文件名都变，
脚本改为**按内容定位**（`find_renderer_files()`）。

## Patch 结果

### ASAR 层（app.asar 内）

| 层 | 描述 | 文件 | 偏移量 | 状态 |
|---|---|---|---|---|
| L1 | safeParse bypass | `index.chunk-ChZ67Jhw.js` | 2202100, 2204237 | ✅ applied ×2 |
| L2 | model picker allowlist | `index.chunk-l0PS_wmg.js` | 544651 | ✅ applied |
| L2c | 主进程 provider 校验器 | `index.chunk-ChZ67Jhw.js` | 656212–657608 | ✅ applied ×5 |
| L2c | preload 校验器 | `index.pre.js` | 331722–332984 | ✅ applied ×5 |
| L4 | auto-update 早期返回 | `index.chunk-ChZ67Jhw.js` | 3723488–4008385 | ✅ applied ×5 |
| L6 | session title 兜底 | `index.chunk-ChZ67Jhw.js` | 3965744, 3966058 | ✅ applied ×2 |
| L3b | swift 虚拟化支持 | `claude-swift/js/index.js` | 3353 | ✅ applied |

### renderer 层（ion-dist，ASAR 外）

| 层 | 描述 | 文件 | 状态 |
|---|---|---|---|
| L2d | 渲染进程模型校验器（`wt` 门 + `Dt`/`Ot`/`kt` + Vertex/Bedrock） | `ce459c687-*.js` | ✅ applied ×6 |
| L9 | 语言列表数组 `Am`（zh-CN/zh-TW/zh-HK） | `shared-2-*.js` | ✅ applied ×3 |

### 无需 patch 的层

| 层 | 原因 |
|---|---|
| L2b | 终端 `.some()` 白名单自 0811 起已不存在 |
| L5 | `inferenceModels` 过滤（`Cke`/`wke`）只做剔除不抛错 |
| L7 | `cwn` 集合原生排除 xhigh，`uwn()` 兜底 `medium` |

## 功能验证

### 系统策略
- ✅ Auto-updates disabled by policy: True
- ✅ secureVmFeaturesEnabled / isDesktopExtensionEnabled / isLocalDevMcpEnabled / isClaudeCodeForDesktopEnabled: True

### 代码签名与完整性
- ✅ `codesign --verify --deep --strict`: OK
- ✅ entitlements: virtualization=True, allow_jit=True, disable_library_validation=True
- ✅ `ElectronAsarIntegrity` 已更新

### 静态检查
- ✅ 全部被改文件 `node --check` 通过（ASAR 内 4 个按 header 提取后检查 + renderer 2 个散文件）
- ✅ 幂等性：对已打补丁的 App 重跑，全部报 `already_applied`，语言数组无重复项

### 行为验证
将补丁后的校验器抽到 Node 中执行，provider=gateway：

```
minimax-m3                   -> ok=true
glm-4.6                      -> ok=true
deepseek-v3                  -> ok=true
gpt-4o                       -> ok=true
claude-sonnet-4-5            -> ok=true
anthropic/claude-sonnet-4-5  -> ok=true
```

### 运行时
- ✅ App 从 `/Applications` 启动，无崩溃
- ✅ **用户实测确认：汉化与 3P 模型拦截均已正常**

## 汉化覆盖率

2.2553 的 `en-US.json` 从 24954 增至 **29442 key**（新增 6683）。现有
`resources/frontend-zh-CN.json`（24019 key）覆盖 17332/29442，**12110 条回落英文**
（0903 时缺 6107，属新增内容而非回归）。

补齐流程见 `translations/README.md`。本次按用户要求暂缓。

## 安装记录

- 备份: `/Applications/Claude.backup-before-3p-v2-20260921-171748.app`（0903 / 1.44121.4）
- 临时备份: `/tmp/Claude-backup-0903-20260921-171713.app`
- 安装命令：
  ```bash
  cd macOS
  python3 patch_claude_3p_macos_0921.py \
    --dmg ~/Downloads/Claude.dmg \
    --install --provider gateway --feature-recovery --zh-cn --write-policy
  ```

## 结论

✅ **2.2553.1 适配成功，全部 28 处 patch 命中，已安装生效。**

新增的 L2d / L9 两层是本次关键修复——它们解释了为什么此前「主进程已补丁但 UI 仍拦截 3P 模型」
「汉化文件已装但语言选项里没有中文」。