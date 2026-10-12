# Changelog

本项目遵循「日期 — 主题」的变更记录格式。最新在上。

---

## 2026-10-13 — 适配 Claude Desktop 2.31226.1 + 正式 App 重装

### 版本

- 新版：`2.31226.1`（本机 `/Applications` 官方安装版，直接复制到 `/tmp` 分析）
- 上一版：`2.2553.1`（0918）
- 脚本：`patch_claude_3p_macos_0921.py`（继续沿用，追加 2.31226 特征码）

### 初测失效层（3 层）

| 层 | 旧特征串为何失效 | 2.31226 新位置 / 新形态 |
|---|---|---|
| L1 | 两个 custom3p helper 校验器改名（`uOt`/`vOt` → `rUt`/`dUt`） | `index.chunk-Cyt2WTko.js`（2114065, 2116202） |
| L10 | renderer 模型选择器门控局部变量改名（`o=`/`n.some`/`q` → `s=`/`o.some`/`D`） | `ion-dist/assets/v1/c593f7513-DQShcHgn.js`（21206） |
| L12 | SDK 参数拼装改用 `Y7()` helper 包装（`T.push(\`--setting-sources=…\`)` → `w.push(Y7("--setting-sources",ee.join(",")))`） | `index.chunk-D6Q00DJz.js`（1108353） |

### 初测漏掉的隐患：L2d 共享门改名

首轮 dry-run 显示 L2d「applied ×2」，但**幂等复检报 missing** —— 说明命中的只是两条兜底分支
（Bedrock / Vertex 的 reason 字符串），真正的共享黑名单门 `wt` 已改名 `pr`（黑名单/白名单/列表
局部变量同步改为 `fr`/`ur`/`dr`），旧特征串完全没匹配到。若不补，renderer 仍会拦 minimax/glm/
deepseek 等 3P 模型名。已追加新门特征码（同样 pin `t` 到 `` `claude` ``）：

```
function pr(e){let t=e.toLowerCase();return fr.test(t)?!1:ur.test(t)||dr.some(e=>t.includes(e))}
```

并在 `RENDERER_VALIDATOR_NEEDLES` 增加前/后置检测串，恢复幂等性。

### 其余层原样命中 2.2553 特征码

L2（`index.chunk-epGqPC4W.js` 516388）、L2c（`index.chunk-Cyt2WTko.js` 537381 + `index.pre.js` 334222）、
L4（5 处）、L6（2 处）、L11（`index.chunk-BCHP6ll9.js` 1490161 + `index.chunk-QEr06WaZ.js` 362859）、
L3b（3372）、L9（`shared-50-Bmc9oUMm.js` 105047）、L2d 兜底分支。L2b / L5 / L7 依旧原生已处理。

### 验证

- dry-run：全部实际层 applied（L2b/L7 属已知不需要），无 ambiguous
- `node --check`：ASAR 内 7 个被 patch 文件 + renderer 3333 个 JS 全部通过
- 幂等复检：对已 patch App 重跑，全部 `already_applied`；语言数组无重复项
- `codesign --verify`：OK；`ElectronAsarIntegrity` 已更新；entitlements 保持 virtualization/allow_jit
- 装机：App 从 `/Applications` 启动，主进程稳定运行 ≥1 分钟，无崩溃报告，renderer 以 `--lang=zh-CN` 启动，
  managed config 显示 `deploymentMode:3p`

### 安装方式变化（重要）

macOS App Management（TCC）会拒绝**非授权进程写入 app bundle 内部**（`Operation not permitted`，
即使属主是当前用户、`/Applications` 目录可写）。因此本次改为 **bundle 级替换**（与 SOP 流程 1 一致）：

```bash
mv /Applications/Claude.app /Applications/Claude-backup-2.31226.1.app
cp -R /tmp/claude-new-test/Claude.app /Applications/Claude.app   # 已在 /tmp 内 patch + 重签 + 验证
xattr -cr /Applications/Claude.app
```

原版备份保留在 `/Applications/Claude-backup-2.31226.1.app`（另有更早的
`/Applications/Claude.backup-before-3p-v2-20260921-171748.app` 未动）。

### 汉化

- 硬编码字符串：810 处替换（245 个文件）
- 前端 locale merge：16058 translated / 17900 fallback / 7706 extra old keys ignored
  （2.31226 的 en-US 文案基数进一步增大，fallback 属新增内容，非回归）

---

## 2026-10-05 — L12：恢复用户技能与斜杠命令

### 症状

L11 之后 3P 模型不再被组织设置拒绝，但 Desktop 的 `/speckit` 等用户斜杠命令
不再出现候选。`~/.claude/skills` 与 `~/.claude/commands` 本身都在。

### 根因

L11 把桌面会话的 `settingSources` 改为 `[]`，但 SDK 对每个已定义数组都会拼出
`--setting-sources=`。CLI 把这个显式空来源列表当作权威配置，于是跳过用户技能
和 legacy commands。

### 修复（L12）

等长把空数组判定从“已定义”收窄为“至少有一个来源”：

| 目标 | 特征串 | offset（2.2553） |
|---|---|---|
| SDK CLI 参数拼装（`index.chunk-Bepat7CB.js`） | `C!==void 0&&T.push(...)` → `C?.length&&T.push(...)` | 896472 |

非空来源仍原样传递；只有空数组恢复 CLI 默认加载路径，L11 的模型白名单隔离保持不变。

### 验证

- dry-run：L12 命中 1 处
- 已安装 `/Applications/Claude.app`：旧特征串 0 处、新特征串 1 处
- `node --check`、幂等复检 `already_applied`、`codesign --verify --deep --strict` 通过
- 备份：`/Users/junqi/Library/Application Support/Claude-3P-Backups/Claude-before-l12-20261005-125411.app`
- 用户侧 `/speckit` 候选显示仍待新 Desktop Code 会话确认

---

## 2026-10-01 — L11：会话层模型拒绝修复

### 症状

L10 之后 picker 不再灰化，但选中发现的非 Claude 模型（GLM-5.3 等）提示
「… is restricted by your organization. Still using Opus 5.5.」，会话回落旧模型。

### 根因

拒绝来自 **CLI 会话本身**（桌面只解析会话输出弹 toast，主进程无任何 entitlement 逻辑）：

- 桌面聊天 spawn 用 `settingSources:["user"]`，CLI 读入 `~/.claude/settings.json` 的
  `availableModels: ["opus","sonnet","fable"]`（终端别名，只匹配 claude-* 行）；
- CLI 的 `Fr()` 策略门对白名单外的模型直接拒绝切换；managed 3P 配置没有静态模型列表，
  user 层成为生效白名单。
- 终端 CLI `-p` 初始模型不走切换门（实测 GLM 正常），只有桌面会话的切换路径被拦。

### 修复（L11）

等长把两处桌面会话 spawn 的 `settingSources` 改为 `[]`（探针会话本就如此）：
会话不再读 settings 文件 → 生效白名单为空 → `Fr()` 提前放行所有模型。
桌面自备 provider env 与完整模型 ID；orca hooks 在桌面会话本就空转。
特征串不含混淆名，0903 / 2.2553 通用：

| 目标 | 特征串 | offset（2.2553） |
|---|---|---|
| 聊天 spawn（DM8UiapT / CvmK1tLJ） | `settingSources:["user"],settings:` → `[],` | 316182 |
| brokered 会话（l0PS_wmg / CZBa8sWq） | `settingSources:["user","project","local"],includePartialMessages:` → `[]` | 809575 |

### 验证

- dry-run：L11 命中两个 chunk，其余层 already_applied
- 临时 App：`node --check`（两个被 patch 的 chunk）通过、幂等复检 already_applied、codesign 通过
- 已安装 /Applications 并重启验证

---

## 2026-09-30 — L10：模型选择器 availableModels 过滤绕过

### 症状

模型发现（`/v1/models`）填充的模型选择器里，非 Claude 模型（GPT/Grok/Haiku 等）全部灰化，
tooltip「不在 你的 Claude Code 设置 设置的 availableModels 中 (~/.claude/settings.json)」，
后缀「Unavailable」，无法选择。

### 根因

发现本身正常，是 **picker 的 UI 门控**把它们禁用了：

- 主进程 SettingsResolver 跨层级合并 `availableModels`（用户级 `~/.claude/settings.json` 优先，
  本例为 `["opus","sonnet","fable"]`）；
- 渲染进程 picker 的 `Rl()`（0903 为 `ld()`）在 `t.state==="set"` 时激活 allowlist 门控，
  行名不匹配 `q(model, value)` 的全部灰化。别名 opus/sonnet/fable 只能匹配 claude-* 行，
  于是发现的 3P 模型全被拦在 UI 层。

### 修复（L10）

把激活判定 `t.state==="set"` 等长改成永不匹配的 `t.state==="zet"`，门控恒走无限制路径
`Il()`；同函数的 desktop/CLI 版本门控不受影响。特征串在对应文件中各只有 1 处：

| 版本 | 文件 | offset |
|---|---|---|
| 2.2553 | `ion-dist/assets/v1/c360a9e1c-*.js`（`Rl`） | 22886 |
| 0903 | `ion-dist/assets/v1/c66fe388e-*.js`（`ld`） | — |

> 不改代码的替代方案：把发现的模型 ID 加进 `~/.claude/settings.json` 的 `availableModels`。
> 但该文件由外部工具维护、模型列表动态变化，patch 方案更省心。

### 验证

- 已安装 App dry-run：L10 命中 `c360a9e1c-GPs-MV9u.js`，其余层 already_applied
- 临时 App 实 patch：`node --check` 通过、幂等复检 already_applied、`codesign --verify --deep --strict` 通过
- 0903 DMG dry-run：L10 备选特征码命中 `c66fe388e-DOFZnzRG.js`

---

## 2026-09-21 — 适配 2.2553.1 + renderer 层补丁（关键修复）

### 新增：renderer 层补丁（L2d / L9）

**这是本次最重要的发现**：`Contents/Resources/ion-dist/` 位于 `app.asar` **之外**，此前所有 patch 层只扫 `.vite/build/`，因此完全漏掉了渲染进程。2.2553 起模型校验和语言列表都在这里各有一份独立实现：

| 层 | 位置 | 作用 |
|---|---|---|
| L2d | `ion-dist/assets/v1/ce459c687-*.js` | 渲染进程的模型校验器（`wt` 门 + `Dt`/`Ot`/`kt` 三个 provider 校验器 + Vertex/Bedrock） |
| L9 | `ion-dist/assets/v1/shared-2-*.js` | 语言选择器的可选语言数组 `Am`（导出为 `vm`，被 `shared-21` 当作 `offeredLocales`） |

症状与根因：
- **报错「Doesn't look like an Anthropic model: 需要一个引用 Anthropic 模型的网关模型路由…」**：来自渲染进程的 `At()` → `kt()`，与主进程 `Yo()` 是两套独立代码。只补主进程时，Settings 仍会用渲染进程那套拒绝 3P 模型名。
- **语言列表没有中文**：`Am` 数组决定下拉框内容，`zh-CN.json` 存在但不在数组里就不显示。0903 时期该数组也存在于 `shared-3-*.js`，同样未被打补丁。

文件名带内容哈希（`ce459c687-B4NlOXPM.js`），因此按**内容**定位而非文件名。两个文件都在 `app.asar` 之外，等长替换不是硬性要求（无 ASAR layout 约束），但校验器仍用等长替换以保持一致；`resign_app()` 的 `Contents/` 全树遍历已覆盖这两个文件的签名。

### 适配 Claude Desktop 2.2553.1

版本号方案从 `1.44121.4`（日期型）改为 `2.2553.1`（语义型）。逐层结果：

| 层 | 状态 | 说明 |
|---|---|---|
| L1 | 更新 | `uOt`/`vOt` 两个 custom3p helper 校验器（`index.chunk-ChZ67Jhw.js`） |
| L2 | 更新 | 选择器空白名单改为 `hC(e,n)`（`index.chunk-l0PS_wmg.js`） |
| L2b | 仍不需要 | 终端 `.some()` 白名单在新版依旧不存在 |
| L2c | 更新 | 主进程 `Hxe`/`Uxe`/`Wxe` + 共享门 `Jo`；preload `KS`/`qS`/`JS` + 共享门 `US`；另加 Vertex 内联校验器 |
| L2d | **新增** | 渲染进程校验器（见上） |
| L4 | 更新 | 更新器守卫接收器变为 `K()`（3 处 block + 1 处 early-return） |
| L5 | 仍不需要 | `inferenceModels` 过滤（`Cke`/`wke`）只做剔除不抛错 |
| L6 | 更新 | `/dust/generate_title_and_branch` 兜底值从 `""` 变为 `{title:""}`，需独立特征码 |
| L7 | 仍不需要 | `cwn` 集合原生排除 xhigh，`uwn()` 兜底 `medium` |
| L9 | **新增** | 渲染进程语言列表（见上） |

### 修复：汉化脚本桥接路径失效

`patch_claude_3p_macos_0921.py` 的 `load_zh_cn_patcher()` 仍指向已改名的 `patch_claude_zh_cn.py`，导致 `--zh-cn` 直接 `SystemExit`。现按 `patch_claude_zhcn_macos_0921.py` → `patch_claude_zh_cn.py` 顺序回退查找。

### 修复：独立汉化脚本的语言列表

`patch_claude_zhcn_macos_0921.py` 的 `patch_language_whitelist()` 原本假定「0903 改为文件系统扫描，无需改 JS」，实际 2.2553 仍依赖硬编码数组。现改为真正把语言拼进 `Am`，并把 locale 文件安装提到该步骤之前（否则会误报「locale files not installed yet」）。

### 汉化覆盖率说明

2.2553 的 `en-US.json` 从 24954 增至 29442 key（新增 6683）。现有 `resources/frontend-zh-CN.json`（24019 key）覆盖 17332/29442，**12110 条回落英文**。这属于新增内容而非回归（0903 时缺 6107）。补齐方式见 `translations/README.md`。

### 验证

- dry-run 全层命中（ASAR 19 处 + renderer 9 处），无 `missing`/`ambiguous`。
- 全部被改文件 `node --check` 通过（ASAR 内 4 个 + renderer 2 个）。
- `codesign --verify --deep --strict` 通过；`ElectronAsarIntegrity` 已更新。
- 幂等性：对已打补丁的 app 重跑，全部报告 `already_applied`，语言数组无重复项。
- 校验器行为验证：抽出补丁后的 `At()`/`Yo()` 在 Node 中执行，`minimax-m3`/`glm-4.6`/`deepseek-v3`/`gpt-4o` 均返回 `ok=true`。
- 用户实测确认：汉化与 3P 模型拦截均正常。

### 脚本重命名

`patch_claude_3p_macos_0903.py` → `patch_claude_3p_macos_0921.py`
`patch_claude_zhcn_macos_0903.py` → `patch_claude_zhcn_macos_0921.py`

沿用「版本日期」命名惯例（`0811` = 1.26832.0、`0903` = 1.44121.4），`0921` 对应
2.2553.1 的适配版本。3P 脚本的汉化桥接保留 `_0903` 与 `patch_claude_zh_cn` 作为回退名。

### 已安装生效

- 目标：`/Applications/Claude.app`，版本 `2.2553.1`
- 备份：`/Applications/Claude.backup-before-3p-v2-20260921-171748.app`（0903 / 1.44121.4）
- 命令：
  ```bash
  python3 macOS/patch_claude_3p_macos_0921.py \
    --dmg ~/Downloads/Claude.dmg \
    --install --provider gateway --feature-recovery --zh-cn --write-policy
  ```
- 测试报告：[`macOS/test_0921_summary.md`](macOS/test_0921_summary.md)

### 待办

- 汉化补全：2.2553 的 `en-US.json` 增至 29442 key，当前覆盖 17332/29442，
  **12110 条回落英文**（新增内容，非回归）。流程见 `translations/README.md`，本次暂缓。

---

## 2026-09-03 — Windows 适配 + macOS L6 修复

### Windows 适配

- 新增 `patch_claude_3p_windows.py`：Windows 版本的 3P patch 脚本。
- 核心功能移植：
  - ASAR patch 逻辑（与 macOS 完全相同的特征码和 patch 规则）
  - **中文汉化**：完整移植（语言白名单、frontend/desktop/statsig 翻译、硬编码字符串替换）
  - Windows 路径适配：`resources/app.asar`（vs macOS `Contents/Resources/app.asar`）
  - 注册表策略：`HKLM\SOFTWARE\Policies\Anthropic\Claude` 禁用自动更新
  - 跳过代码签名（Windows Electron 应用不需要）
- 自动查找安装位置：`%LOCALAPPDATA%\Programs\Claude` 或 `%PROGRAMFILES%\Claude`
- 命令行参数：`--zh-cn` / `--lang zh-CN/zh-TW/zh-HK` / `--write-policy` / `--dry-run`

### macOS 修复

- 修复 L6 层 `pad_bytes()` 长度计算错误：原代码在传参时使用了 `len(原字符串)` 包裹导致运行时报错 "non-equal replacement length"。
- 现已改为直接传入常量 `64`（两处 0811 特征码的实际长度）。
- 验证通过：dry-run 全层 `already_applied`，语法检查通过。

### 文档

- README 新增 Windows 使用说明。
- WINDOWS_GUIDE.md 新增完整 Windows 使用指南。
- 文件说明表更新，标注 macOS/Windows 脚本分工。

---

## 2026-08-11 — 适配 0811（1.26832.0）+ 汉化全量补全

### 0811 适配

- `patch_claude_3p_v2.py` 从单文件扫描改为**多文件扫描**：0811 的 `.vite/build/index.js` 被代码分割成约 250 个 `index.chunk-*.js` / `index2.chunk-*.js` + `index.pre.js`（4.4MB），旧脚本只扫单个 `index.js` 导致 L1-L7 全 miss。
- 新增 `find_index_build_files()` + `patch_index_files()`，`patch_asar()` 改为多文件写回；0703 兼容保留。
- 各层 0811 新特征码（已实测命中 14 处）：
  - L1 `let s=um.safeParse(o);if(!s.success)throw` → 伪造成功
  - L2 / L2c 各 provider validator（`de`/`YB`/`me`/`fe`/`pe`/`QB`/`XB`/`ZB`）的 `{ok:!1,reason:` → `{ok:!0,reason:`
  - L4 `if(r.autoUpdate.disabled){`、`if(a.a().autoUpdate.disabled){`（×3，allow_multi）
  - L5 `s.data.models);if(u)throw` → `if(0)throw`
  - L6 入口 `index.js` 的 `[title-gen] failed` catch → 兜底 `first_session_message`
  - L3b 直接命中（offset 1750→1830）
  - L2b / L7 在 0811 中已被新版结构吸收/原生 gate，无需 patch
- 修复 L4 早期写法漏掉 if 条件右括号 `)` 导致的启动 SyntaxError。

### 汉化全量补全

- `resources/frontend-zh-CN.json` 从 12355 → **24019 key**，机翻补齐 11664 条缺译。
- 重打补丁后：**20436 translated / 0 fallback**（此前 8956 translated / 11664 fallback）。
- 翻译管线入库 `translations/`（batch 源 + translated 结果 + check_and_merge.py + README）。
- 规则：ICU plural/`{占位符}`/`<标签>` 保留；专有名词（Claude/MCP/模型名等）留英文。
- 官方 Anthropic 中文包本就只覆盖 44%（9057/20721），本补全超出官方范围。

### 文档

- 新增 `HANDOFF.md`、`SOP.md`、本 `CHANGELOG.md`；`AGENTS.md` 补 0811 适配记录 + TCC 注意事项。

---

## 2026-07-03 — 0703 功能恢复补丁（`b6d0eb3`）

- 新增 `patch_claude_3p_v2.py`，适配 Claude Desktop 1.18286.0（0703）。
- 修复 FrA gateway validator 生成非法 JS（`return 1!==0?{ok:!0};`）为合法等长 `if(1)return{ok:!0};`。
- 修复 0703 语言白名单失效（语言数组迁移到 `ion-dist/assets/v1/*.js`，加 fallback 扫描）。
- 自动更新禁用改为 `if(1||...)` 强制早期返回。
- 新增 `--feature-recovery` / `--enable-local-code-features` / `--local-market-report` / `--zh-cn` / `--lang`。
- 支持 DMG → 临时 App → patch → 验证 →（显式 `--install`）的安全流程。

## 2026-07-04 — SkillHub 移除（`f2c7596`）

- 完全移除 SkillHub（面板/IPC/embed/CLI args），功能收敛为 3P patch + Cowork + 中文 + 本地恢复。
- 清理 README / INSTALL_APPLICATION_PATCH.md 中的 SkillHub 引用。

## 2026-07-05 — 3P 调研与 marketplace 结论（`49eba0e`）

- 补 3P 模式 vs 官方订阅功能差异表。
- Marketplace 调研结论：banner 服务端下发、`allowedPluginMarketplaces` 3P 下为空、`hasOrgPolicyBackend()` 恒 false；脚本层面已到本地 patch 极限，改走本地 sideload / 自建 marketplace。

## 2026-08-11 — 汉化翻译管线入库（`b23aa9e`）

- `translations/` 入库：24 批英文源 + 24 批机翻结果 + `check_and_merge.py`（校验/合并，改仓库相对路径）+ README。

---

## 2026-06-23 — 0623 基线（`47c71a0`）

- `patch_claude.py`：11 处 patch，实测 Claude Desktop 1.14271.0。
- L1 3P safeParse / L2 model picker / L2c gateway validator / L3b claude-swift 虚拟化 / L4 自动更新 / L5 inference 校验 / L6 session title / L7 effort xhigh。
- 中文汉化资源 `resources/` + `patch_claude_zh_cn.py`。
