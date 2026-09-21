# HANDOFF — Claude-Desktop-3P-Patch 交接文档

> 用途：给后续 agent / 开发者接手本项目的**历史处理记录 + 记录存放索引**。
> 技术细节（patch 层、常量、函数）看 [AGENTS.md](AGENTS.md)；操作流程看 [SOP.md](SOP.md)；变更历史看 [CHANGELOG.md](CHANGELOG.md)。
> 本文件回答"这个项目做过什么、记录在哪、下一步该干嘛"。
>
> 最后更新：2026-08-11（0811 适配 + 汉化补全完成，已提交 GitHub 后时点）

---

## 0. 文档地图

| 文档 | 何时读 |
|---|---|
| [SOP.md](SOP.md) | 要做**任何操作**（安装/升级/适配新版）前 —— 含脚本更新流程 |
| [AGENTS.md](AGENTS.md) | 要改 patch 层 / 常量 / 查近况 |
| [CHANGELOG.md](CHANGELOG.md) | 要改 README 版本号 / 写发布说明前 |
| [INSTALL_APPLICATION_PATCH.md](INSTALL_APPLICATION_PATCH.md) | 只装已下载版本、打补丁 |

---

## 1. 项目速览

macOS Claude Desktop 的本地补丁脚本，把 3P / Gateway 模式下的模型可见可用、禁用自动更新、本地 Claude Code / MCP / extensions 能力、中文汉化等能力恢复出来。

- 主脚本：`patch_claude_3p_v2.py`
- 旧基线：`patch_claude.py`（v6 时代，已被 v2 取代）
- 汉化辅助：`patch_claude_zh_cn.py` + `resources/`（frontend-zh-CN.json 24019 key）
- 翻译管线：`translations/`（批次文件 + `check_and_merge.py`）
- 默认安全流程：`DMG → 临时 App → patch → 验证`，只有显式 `--install` 才替换 `/Applications/Claude.app`
- 当前适配版本：`1.26832.0`（0811 构建，已 patch 并提交）

---

## 2. 历史处理记录（时间线）

### 2.1 v6 全面实战版 — 2026-06-23（commit `47c71a0`）

针对 Claude Desktop **1.14271.0** 的第一次完整补丁，**11 处 patch**，实测通过：

| 层 | 作用 |
|---|---|
| L1 | 3P managed config `safeParse` 伪造成功 |
| L2 / L2b | model picker 白名单 + `.some()` 永远 true |
| L2c | gateway model route validator 绕过（PX 短路） |
| L3b | `@ant/claude-swift` 虚拟化支持劫持 |
| L4 | `disableAutoUpdates` 短路 |
| L5a / L5b | inferenceModels 校验短路 |
| L6 | session title 本地兜底（first 46 chars） |
| L7 | qUA 禁用 `xhigh` effort（3P 模型不兼容） |

实测：`minimax-m3` 在 chat 顶部下拉框可见，发消息不再报 `output_config.effort=xhigh`，ASAR 完整性通过。

**教训（重要）**：本次会话里用户的 `patch_claude.py` 被 macOS 锁死（所有 read/write/cat 均 `EPERM`），不得不在别处重建脚本。见 §5 常见坑。

### 2.2 0703 功能恢复补丁 — 2026-07-03（commit `b6d0eb3`）

Claude Desktop 升级到 **1.18286.0**，新建 `patch_claude_3p_v2.py`（+1061 行），修复：

- **FrA gateway validator 语法错误**：旧 patch 生成非法三元 `return 1!==0?{ok:!0};` 导致启动 `SyntaxError: Unexpected token ';'`。改为等长合法 `if(1)return{ok:!0};`，用 `node --check` + 临时 App 启动验证。
- **0703 语言白名单失效**：语言数组不在 `index-*.js` 而在 `Contents/Resources/ion-dist/assets/v1/c4b350ac1-*.js`。`apply_localization()` 加 fallback 扫描 `assets/v1/*.js`。
- 自动更新修复：旧 `if(0&&...)` 永远不执行 → 改为强制早期返回 `if(1||...)`，可另写 `/Library/Preferences/com.anthropic.claudefordesktop disableAutoUpdates=true`。

### 2.3 SkillHub 移除 — 2026-07-04（commit `f2c7596`）

SkillHub 是一次失败的注入实验（面板有全局显示 bug，且依赖服务端市场），已**完全移除**：

- 删 `DEFAULT_SKILLHUB_URL` 常量、`patch_skillhub_entry()`、`--skillhub-url` / `--embed-skillhub` CLI 参数。
- 功能收敛为：**3P patch + Cowork + 中文汉化 + 本地功能恢复**。
- 清理 README / INSTALL_APPLICATION_PATCH.md。

### 2.4 3P 模式 vs 官方订阅调研 + marketplace 结论 — 2026-07-05（commit `49eba0e`，写入 AGENTS.md）

- 功能差异表（模型访问 / 插件扩展 / 多端云）已整理进 AGENTS.md §「3P 模式 vs 官方订阅」。
- **Marketplace 调研结论：脚本层面已到头。**
  - Plugin Marketplace 的 banner 文案（"你的组织尚未提供插件…"）是**服务端下发**，5 个 JS bundle 里都搜不到 → 客户端删不掉。
  - `allowedPluginMarketplaces` 在 3P 模式下为空列表，官方目录没有内容可渲染。
  - `hasOrgPolicyBackend()` 在 3P 模式恒为 `false`。
  - 要让 UI 真正可用只能走**本地 sideload**（已解锁）或自建 marketplace（官方 URL 未知）。
- 已解锁的本地替代路径：
  - `Settings → Extensions → Install from local file`（`.dxt`）
  - `Settings → Developer → Local MCP`
  - `~/.claude/skills/<skill>/SKILL.md`、`~/.claude/plugins/`、`~/Library/Application Support/Claude/extensions/`、`claude mcp add`

### 2.5 油猴脚本 Agent Reach Cookie Helper — 2026-07-04（不在 git 里！）

代码在 `userscripts/agent-reach-cookie-helper.user.js`（**v4.0.0**，**git 未跟踪**），但**项目文档完全没提过**，仅存在于会话记录。给 Codex 里的 Agent Reach 用，从各平台提取登录 cookie/token。

演进（v1 → v4）：
- **v1** `agent-research-token-extractor.user.js`：Twitter(X)/GitHub 浮动面板，提取 cookie + PAT，纯文本/JSON 切换。
- **v2** 改名 `agent-reach-cookie-helper`：可拖动按钮 + 操作面板，罗列 Agent Reach 支持的全部平台（Twitter/X、雪球、Reddit、小红书、Facebook、Instagram、LinkedIn + API key 类 + 零配置类）。
- **v3** 一键自动采集：`GM_setValue` 跨页状态机（`are_collect_session`：queue / currentIndex / results），轮流跳转提取、汇总复制。
- **v4 根因修复（关键）**：v2/v3 "已登录却提取不到"不是逻辑错，是**认证 cookie（`auth_token`、`reddit_session`、`sessionid`、`li_at` 等）都是 `HttpOnly`，`document.cookie` 永远读不到**。主通道改为 Tampermonkey 的 **`GM_cookie`**（能读 HttpOnly），`document.cookie` 降级为 fallback。用户环境为独立 Chrome + Tampermonkey。

---

## 3. 本地记录都在哪（给未来会话的索引）

| 内容 | 位置 |
|---|---|
| 项目 git 历史（4 个 commit，覆盖所有补丁） | `git log` |
| 技术维护文档：patch 层、offsets、常量、修复记录 | `AGENTS.md` |
| 使用说明 | `README.md`、`INSTALL_APPLICATION_PATCH.md` |
| 本项目会话 transcript | `/Users/junqi/.claude/projects/-Users-junqi-Documents--------03-AI--------Claude-Desktop-3P-Patch/*.jsonl` |
| 油猴脚本会话（完整 251 行，含 3 份 plan） | 同上 `2f6ccbb5-1356-418d-83a9-020ed0fee8db.jsonl` |
| v6 会话（Jun 23，cwd=cowork） | ⚠️ transcript 已被系统清理，**只剩会话搜索索引**，仅能按关键词搜到片段（`d27bbceb-951b-4100-adf8-3490a5b79477`） |
| 项目 memory 目录 | `/Users/junqi/.claude/projects/-Users-junqi-Documents--------03-AI--------Claude-Desktop-3P-Patch/memory/`（当前为空） |
| `~/.claude/plans/` 里现存 3 份 plan | ⚠️ 均属**其他项目**（cursor-patch / cowork review panel），本项目的 plan（`happy-hopping-sundae.md`）已被清理，内容在会话 transcript 里 |

**注意**：项目的会话不都在本项目目录下。Jun 23 的 v6 补丁会话 cwd 是 `/Users/junqi/Documents/cowork`，搜历史时用 `mcp__ccd_session_mgmt__search_session_transcripts`（如搜 `patch_claude_3p_v2`、`minimax-m3`、`1.14271.0`）比翻 JSONL 更可靠。

---

## 4. 当前状态与待办（截至 2026-09-21）

### 2.2553.1 适配（已完成，待提交）

- **版本**：`2.2553.1`（构建日 0918），版本号方案由日期型 `1.44121.4` 改为语义型。
- **本次最重要的发现**：`Contents/Resources/ion-dist/` 在 `app.asar` **之外**，此前所有 patch 层
  只扫 `.vite/build/`，完全漏掉渲染进程。渲染进程带着**独立的一份**模型校验器（`At`/`wt`）和
  语言列表（数组 `Am`），这就是用户遇到的两个问题的根因：

  | 症状 | 根因 | 新增层 |
  |---|---|---|
  | 报 `Doesn't look like an Anthropic model: 需要一个引用 Anthropic 模型的网关模型路由…` | 只补了主进程 `Yo()`，渲染进程 `At()` 仍是旧的 | **L2d** |
  | 语言文件装好了但下拉框没有中文 | `Am` 数组里没有 `zh-CN` | **L9** |

- 逐层结果：L1/L2/L2c/L4/L6 更新特征码；L2b/L5/L7 新版原生已处理；L3b 直接命中；
  新增 L2d/L9。详见 CHANGELOG.md「2026-09-21」。
- 顺带修掉两个既有 bug：
  1. `patch_claude_3p_macos_0921.py` 的汉化桥接仍指向已改名的 `patch_claude_zh_cn.py`，
     导致 `--zh-cn` 直接 `SystemExit`（现已按新名 → 旧名顺序回退查找）。
  2. `patch_claude_zhcn_macos_0921.py` 误以为「0903 起语言列表改为文件系统扫描」，
     实际仍需改 JS 数组（现已在两个脚本里都真正拼接语言）。
- 验证：dry-run 全命中（ASAR 16 处 + renderer 9 处）、`node --check` 全通过、
  `codesign --verify --deep --strict` 通过、幂等重跑无副作用、临时 App 启动无崩溃。
  **用户实测确认汉化与 3P 模型拦截均已正常。**

### 待办 / 观察项

1. **汉化补全（12110 条）**：2.2553 的 `en-US.json` 增至 29442 key（较 0903 新增 6683），
   当前 24019 条翻译覆盖 17332/29442。补齐流程见 `translations/README.md`，
   属新增内容而非回归（0903 时缺 6107）。
2. **Windows 版本未跟进 2.x**：`Windows/patch_claude_3p_windows_0811.py` 仍是 0811 时代，
   且同样只扫 ASAR。适配时**务必一并检查 Windows 的 renderer 目录**。
3. **userscripts/ 未纳入 git**：`agent-reach-cookie-helper.user.js`（v4）是 git 未跟踪的小工具（cookie helper，与本项目无关）。决定是否入库或移除。
4. **下次新版适配**：按 [SOP.md](SOP.md)「流程 2」执行；步骤 4 已补「必须同时扫描 `ion-dist`」。

---

## 5. 常见坑 / 经验（跨版本仍然适用）

1. **JS byte patch 必须等长**，否则破坏 ASAR payload layout；改 ASAR 后必须更新文件级 integrity 和 `Info.plist` 的 `ElectronAsarIntegrity`。
2. **macOS 会锁文件**：`patch_claude.py` 曾整文件 `EPERM`（read/write/cat 全失败），遇到先检查文件 xattr / 权限 / 是否被占用，必要时换路径重建。
3. **新版本先 dry-run**：新 Claude Desktop 版本必须先 `--dry-run` 确认 patch 层命中，再正式打。
4. **启动报 `SyntaxError`**：优先提取 `.vite/build/index.js` 跑 `node --check`（FrA validator 踩过非法三元）。
5. **中文资源注入成功但语言选择器无"简体中文"**：0703 起语言白名单在 `ion-dist/assets/v1/*.js`，不在 `index-*.js`。
6. **官方云端能力本地 patch 不到**：marketplace banner / 订阅内容 / connectors 是服务端 gated，本地只做 UI / flag / validator / updater / local extension 恢复。
7. **油猴脚本读不到 HttpOnly cookie**：`document.cookie` 永远读不到 `auth_token`/`reddit_session` 这类认证 cookie，必须用 `GM_cookie`。
8. **安装到 `/Applications` 是高影响操作**：除非用户明确要求，只 patch 临时 App。
