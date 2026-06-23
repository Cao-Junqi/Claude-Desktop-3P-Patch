# Claude Desktop 3P Model Patch

> **🎉 [2026-06-23] 0623 v6 全面适配发布！**
> 完整 11 处 patch 全部命中并实测验证：
> - 模型下拉框过滤（L2b/L2c）
> - session 标题自动摘要兜底（L6）
> - 3P 模型 `effort=xhigh` 兼容（L7）
> - 第三方模型（minimax-m3、doubao-seed 等）已在 chat 下拉框可见
> 详见下方 [🛡️ 0623 适配要点](#-0623-适配要点) 与 [更新日志](#-更新日志-changelog)。

> **🎉 [2026-06-23] 0623 基础适配版发布！**
> 针对 Claude Desktop 0623 (app.asar ~35.7 MB) 的反混淆重写，已实测 5 层 patch 全部命中并验证落盘。

> **🎉 [2026-06-04] 终极完美版发布！**
> 本次更新彻底攻破了最新版 Claude Desktop 带来的终极底层防御，真正实现了 **无痛完美修补**！
> 1. **原生 ASAR 完整性深度修复**：破解了 Electron 核心 4MB 分块哈希算法（SHA-256 Block Hashing）。我们不再需要暴力修改 Electron C++ 底层文件，而是完美伪造官方签名格式，动态生成绝对匹配的 JSON 头 `integrity` 哈希链，彻底终结 `FATAL Crash` 闪退！
> 2. **Swift 原生 Cowork 权限接管**：无视重签名丢失官方证书导致的 `@ant/claude-swift` 原生检测拦截 (Invalid installation)。通过直接劫持底层桥接接口，无条件向应用宣告虚拟化 (Virtualization) 完美支持，让最新的 Cowork 功能毫无障碍地运行！
> 3. **无残留动态清洗**：在重签名的最后防线，动态脱壳提取应用安全凭证，并在内存中智能清洗剔除所有会导致沙盒崩溃的企业专属字段，为你打造真正的纯净客户端。
>
> 详情请见下方 [🛡️ 官方的 5 层防御及破解思路](#-官方的-5-层防御及破解思路) 及 [更新日志](#-更新日志-changelog)。

此仓库包含了对 macOS 版本 Claude Desktop 引入的严格“第三方网关模型 (Gateway 3P)”白名单校验机制的完整逆向分析与一键修补脚本，并且**已整合支持中文汉化**。

## 🎯 目标与背景

Claude Desktop 最近一次更新大幅收紧了企业网关配置（Cowork Gateway）的限制。系统只允许下拉选择官方白名单内以 `claude-` 或 `anthropic/` 开头的模型。如果你使用任何第三方模型（例如 `minimax-latest`、`doubao-seed` 等），应用会直接报错或在前端隐藏这些模型。

为了绕过这些限制，使其能够接入任意第三方大模型，我们剥开了官方设置的 **5 层严密的防御体系**。

## 🛡️ 0623 适配要点

0623 版本与 0604 在 5 层防御机制上保持一致，但每一层的代码都做了反混淆重写，因此**特征码必须全量更新**：

| 层 | 0604 旧特征码 | 0623 新特征码 | 替换目标 |
|---|---|---|---|
| L1 3P safeParse | `const l=Ewi.safeParse(E);` | `const a=b$i.safeParse(s);` | `var a={data:s,success:1};` |
| L2 PVt 过滤 | `if(A.length===0)return!1;` | `if(A.startsWith("claude-"))return!0;if(e.length===0)return!1;` | `e.length>=0` → `return!0` |
| L3a isVirtualizationSupported | 主进程 `require(...)` 调用 | 不再 patch（改走 L3b） | — |
| L3b claude-swift 劫持 | 注释行替换 | 注释行替换（未变） | `this.vm.isVirtualizationSupported = () => "supported";` |
| L4 D$t 自动更新 | 无 | `if(A.disableAutoUpdates){D.info("...disabled..."),Ye("...");return}` | `if(0&&A.disableAutoUpda){...}` |
| L4 _$t 手动检查 | 无 | `if(fi().disableAutoUpdates){D.info("...disabled...");return}` | `if(0&&fi().disableAutoUpda){...}` |

> **L4 的特别说明**：0623 把自动更新检查从 ESM 顶层判断（`if(e.disableAutoUpdates)`）改成了封装在 `D$t` / `_$t` 两个函数里。一次性启动检查走 `D$t`，用户主动「检查更新」走 `_$t`，因此两个函数体都要短路。

## 🛡️ 官方的 5 层防御及破解思路

### 第一层：配置加载层的抛错校验 (JS 层)
- **机制**：在 `app.asar` 中的 `index.js`，`bZt.safeParse` 对解析到的模型和 `_Zt` 强行校验，如果不符合规范会抛出 `Invalid custom3p enterprise config`。
- **破解**：利用脚本将 `const o=bZt.safeParse(n);` 修改为强制成功的伪造对象 `var o={data:n,success:1};`，并将抛出 Error 的分支改为 `if(0)`。

### 第二层：前端 UI 下拉框的强过滤 (JS 层)
- **机制**：即使配置被解析，UI 代码在构建模型选择器下拉框时，依然使用了 `filter(c=>!bbA||LbA(c.id))`、`Ert` 甚至 `UbA` 函数。其中 `UbA` 和 `Ert` 内置了 `startsWith("claude-")` 和 `Lxe.test` 正则匹配，导致第三方模型直接“隐身”。
- **破解**：直接对这些过滤器函数进行硬编码跳过：
  - `Ert`: 将 `if(A.length===0)return!1;` 修改为 `if(A.length>=0)return !0;`
  - 数组过滤: `!bbA||LbA(c.id)` 修改为 `!bbA||1||c.id`
  - `UbA`: 修改 `if(!bbA)` 为 `if(1   )`，使非官方模型强行获得 `{ok:!0}`。

### 第三层：虚拟化权限导致的 "Invalid installation" 弹窗验证 (Swift 原生插件)
- **机制**：我们在拆包、修改并重新签名后，丢失了系统自动关联到官方 TeamID 的隐藏 Entitlements（如 `keychain-access-groups` 等）。启动时，内置的 `@ant/claude-swift` 原生插件会调用 `isVirtualizationSupported()` 检查权限，若发现状态不符，将返回 `"entitlement_missing"`。前端捕获后会直接拦截启动，并显示 "Claude's installation appears to be corrupted. Reinstall Claude to use Cowork."。
- **破解**：我们在重新封包时，直接拦截 `@ant/claude-swift` 模块的 JS 接口暴露点。将原本的虚拟化支持检测接口强行覆写为 `this.vm.isVirtualizationSupported = () => "supported"`。无视任何底层原生安全验证，强行使客户端允许启用 Cowork 功能。

### 第四层：ASAR 文件结构级别的哈希分块校验 (Electron Integrity 机制)
- **机制**：最新版的 Electron 启用了内置的 ASAR Integrity 校验。它不但会验证整体 Hash，还会将文件切分为 4MB 连续区块，并在每次读取文件时验证区块的 SHA-256 Hash。一旦发现被修改的 JS 文件区块 Hash 不匹配，Electron 的 C++ 层 (`archive.cc:150`) 会直接触发底层断言崩溃 (FATAL Crash)。
- **破解**：放弃强制擦除 `integrity` 字段的暴力方案。我们在 Python 脚本中完整复刻了 Electron 的哈希分块算法。每次给 JS 注入补丁后，自动按照 4MB 步长重新计算所有被篡改文件的 SHA-256 分块哈希链，并精确对齐 ASAR Payload 的 4 字节边界偏移量，将合法的哈希块完美重写回 `app.asar` 头部 JSON 的 `integrity` 字段。使其在 Electron 看来依然是官方“原封不动”的有效签名文件。

### 第五层：终极防御 - 动态防护屏障与应用签名重置
- **机制**：在突破 ASAR 限制后，应用会被 macOS 系统的 Gatekeeper 及原生校验阻挡，如果签名与 Entitlements 不规范，会在启动时立即崩溃。
- **破解**：采用无残留深度重签名。脚本会动态提取原生官方应用内的安全配置文件（Entitlements），并在内存中实时过滤清洗掉专属的受限字段（如 `com.apple.application-identifier` 和 `keychain-access-groups` 等），注入自签名需要的 `disable-library-validation` 权限。最后通过清理附加属性（`xattr -cr`）并执行 `codesign --deep` 完美重构沙盒授权。

## 🔄 更新日志 (Changelog)

- **[2026-06-23] 0623 v6 全面实战版（实测 Claude Desktop 1.14271.0）**：
  - **真实版本验证**：0623 启动后 `_version=1.14271.0`（electron 42.4.0），实测跑通完整流程：
    - 第三方模型 `minimax-m3` 在 chat 顶部下拉框可见 ✓
    - 模型发消息不再报 `output_config.effort=xhigh` 错误 ✓
    - session 标题有本地兜底（minimax-m3 spawn 失败时也能显示）✓
  - **11 处 patch 全部就位**（v3 → v6 增量）：
    - **L2b**（35B，等长）：`return e.some(i=>i===A||$d(i)===t)}` → `return e.some(i=>!0);/*padpadpad*/}` —— PVt 终态过滤，第三方 model 直接通过
    - **L2c**（36B，等长）：`function v4i(A){return PX(A)?{ok:!0}` → `function v4i(A){return 1!==0?{ok:!0}` —— `mcr` 调 `YX(provider, id)` → `v4i(gateway)` → `PX`（黑名单+白名单）；短路后所有 model 通过
    - **L5a**（25B）：`const c=O$i(A);if(c)throw` → `const c=O$i(A);if(0)throw` —— `O$i` 校验 `inferenceModels` 字段必须 Anthropic catalog 模型
    - **L5b**（53B）：`const g=C$i(...);if(g)throw` → `const g=C$i(...);if(0)throw` —— `C$i` 校验 provider/models 列表
    - **L6**（62B ×2 处）：`.catch(Q=>(D.warn("[title-gen] failed",{error:String(Q)}),""))` → `.catch(()=>d.first_session_message.slice(0,46)/*aaaaaaaaaaa*/)` —— session 标题生成（generate_session_title + generate_title_and_branch）失败时返回 first_message 前 46 字符
    - **L7**（52B，等长）：`function qUA(A){return A!=null&&wQr.has(A)?A:void 0}` → `function qUA(A){return A!=null&&mQr.has(A)?A:void 0}` —— `qUA` 校验 `effortByModel` 字典值；`wQr` 含 `xhigh`（3P 不识别），`mQr` 只 4 个合法值，禁用 xhigh 透传
  - **结构性改进**：
    - `patch_index_js` 拆成 6 个分层循环（L1 / L2-L2b / L2c / L4 / L5 / L6 / L7），每处独立 label
    - `patch_bytes` 改用更严格的多处命中处理（>1 处只 patch 第一处并 warn）
    - 新增 `CLAUDE_APP_PATH` 环境变量支持（不用 sudo 也能跑）

- **[2026-06-23] 0623 基础适配 (v2.0 / v1 基础 5 层)**：
  - **特征码全量重抓**：0623 重写了 3P 校验栈，所有特征码同步更新 —
    - L1: `const l=Ewi.safeParse(E);` → `const a=b$i.safeParse(s);`
    - L2: `if(A.length===0)return!1;` → 完整 `if(A.startsWith("claude-"))return!0;if(e.length===0)return!1;`（用 startsWith 前缀做唯一识别）
    - L4: 老的 `if(e.disableAutoUpdates)` / `if(ki().disableAutoUpdates)` 不再存在，新版更新检查已迁入 `D$t` / `_$t` 两个函数，patch 改为短路 `if(0&&A.disableAutoUpda)` / `if(0&&fi().disableAutoUpda)`
  - **claude-swift 劫持点保持稳定**：0604 / 0623 共同的注释行 `// ComputerUse bindings live in a separate SPM product (ComputerUseSwift)` 依然存在，L3b 双保险机制未变。
  - **重签名更鲁棒**：DMG 挂载点不再写死 `/Volumes/Claude0604/`，改为动态扫描 `/Volumes/Claude*` 找到带 Claude.app 的那个。Entitlements 默认列表补齐 `cs.allow-unsigned-executable-memory` 和 `network.client/server` 等 0623 实测需要的能力。
  - **结构性改进**：把 5 层 patch 拆成独立函数 + 长特征码 + 命中数校验，杜绝 `e.length===0` 这种通用模式误伤第三方库；`patch_bytes()` 在 0 命中时直接 raise（不再静默 skip）。

- **[2026-06-23] ASAR 完整性等长 byte 修复**：
  - 0623 启动会触发 `ASAR Integrity Violation: got a hash mismatch`，根因是 v1 旧 patch 用 `e.length>=0`（3 字节）替代 `e.length===0`（4 字节），**asar 整体缩短 1 字节** 触发 Electron 4MB 分块 SHA-256 校验。
  - 修复：所有 patch 改用等长 byte 替换（如 `e.length===0` → `e.length===0` + 改 `return!1` 为 `return!0`）。

- **[2026-06-23] Entitlements 字段脱壳清洗**：
  - 0623 启动时报 `Touch ID authenticator unavailable: keychain-access-group entitlement is missing or incorrect. Expected value: Q6L2SF6YDW.com.anthropic.claude.webauthn`
  - 修复：ad-hoc 重签后 `xattr -cr` 清理 + `codesign --entitlements` 注入清洗后的 Entitlements（去除 `com.apple.application-identifier` / `team-identifier` / `keychain-access-groups`），保留 `disable-library-validation` 让原生 `.node` 加载。

- **[2026-06-04] 0604 终极完美版（Cowork / 完整性保护突破）**：
  - **原生 ASAR 完整性深度修复**：彻底摒弃了修改 Electron C++ Fuse (保险丝) 的暴力破解方式。通过逆向分析 Electron 底层的 4MB 分块哈希验证算法（SHA-256 Block Hashing），在重组 `app.asar` 压缩包时，利用脚本动态计算并重新生成精准合法的 JSON 头部 `integrity` 区块。修复了 ASAR 封装过程中 Payload 偏移量对齐 Bug，实现了对底层校验机制的完美"瞒天过海"，彻底终结运行时 FATAL 闪退。
  - **Swift 原生权限校验绕过**：修复了因脱离官方签名导致内置原生插件 `@ant/claude-swift` 拦截启动并提示 "Invalid installation" (应用损坏) 的问题。直接切入底层 JS 桥接接口，强制设定虚拟化支持 `this.vm.isVirtualizationSupported = () => "supported"`，确保最新的 Cowork 功能能够完美运行。
  - **重签名字段清洗**：重写了签名流水线，实现实时脱壳提取 Entitlements 列表并智能清洗企业私有凭证字段（如 `keychain-access-groups` 等），防止重签后引起授权组件连环崩溃。
- **[之前版本] 动态兼容性升级**：
  - 更新了前端 JS 层全新的压缩混淆变量名匹配规则。
  - 支持了动态特征码搜索机制。
- **[2026-06-04] 完美适配 Claude 0604 版（Cowork / 完整性保护突破）**：
  - **原生 ASAR 完整性深度修复**：彻底摒弃了修改 Electron C++ Fuse (保险丝) 的暴力破解方式。通过逆向分析 Electron 底层的 4MB 分块哈希验证算法（SHA-256 Block Hashing），在重组 `app.asar` 压缩包时，利用脚本动态计算并重新生成精准合法的 JSON 头部 `integrity` 区块。修复了 ASAR 封装过程中 Payload 偏移量对齐 Bug，实现了对底层校验机制的完美“瞒天过海”，彻底终结运行时 FATAL 闪退。
  - **Swift 原生权限校验绕过**：修复了因脱离官方签名导致内置原生插件 `@ant/claude-swift` 拦截启动并提示 "Invalid installation" (应用损坏) 的问题。直接切入底层 JS 桥接接口，强制设定虚拟化支持 `this.vm.isVirtualizationSupported = () => "supported"`，确保最新的 Cowork 功能能够完美运行。
  - **重签名字段清洗**：重写了签名流水线，实现实时脱壳提取 Entitlements 列表并智能清洗企业私有凭证字段（如 `keychain-access-groups` 等），防止重签后引起授权组件连环崩溃。
- **[之前版本] 动态兼容性升级**：
  - 更新了前端 JS 层全新的压缩混淆变量名匹配规则。
  - 支持了动态特征码搜索机制。

## 🚀 使用方法

本项目提供了两个一键化脚本：
- `patch_claude.py`：用于解除官方第三方模型 (3P) 的严格限制。
- `patch_claude_zh_cn.py`：用于为 Claude Desktop 安装中文汉化资源。

### 执行步骤
1. 确保 Claude Desktop 已经安装在 `/Applications/Claude.app`。
2. 彻底退出正在运行的 Claude。
3. **解除第三方网关限制**：打开终端，进入本仓库目录，执行以下命令：
   ```bash
   sudo python3 patch_claude.py
   ```
   此脚本会自动备份原始文件，修改 `index.js`，物理断开 Electron 完整性校验，并重新签名。

4. **安装中文汉化（可选）**：如果您需要使用中文界面，请继续执行汉化脚本：
   ```bash
   sudo /usr/bin/python3 patch_claude_zh_cn.py --user-home "$HOME"
   ```
   此脚本会将社区汉化资源注入到应用内，并将当前用户的偏好语言设置为中文。

5. 运行完毕后，重新打开 Claude Desktop。如果您执行了汉化脚本，应用界面将完全显示为中文；同时在自定义网关配置中填入诸如 `minimax-latest`，它也会立刻在下拉框中显示可用！

## ⚠️ 维护注意事项
- 脚本中包含了禁用应用自动更新 (`disableAutoUpdates`) 的补丁，以防止客户端偷偷升级覆盖掉我们的修改。
- 如果你之后手动覆盖升级了 Claude Desktop 新版本，只需重新执行一次本脚本即可。
- **关于版本兼容**：由于本工具底层采用了**动态特征匹配**（而不是死板的物理地址），只要官方未来更新没有推翻重写整个安全验证机制（比如只是微调了代码、增加了功能导致文件偏移变化），本脚本大概率依然可以自动找准位置并一键破解！

## ⚖️ 免责声明与风险提示 (Disclaimer & Risk Warning)

本项目仅作学习与技术交流之用（逆向工程与 Electron 安全研究）。请在评估以下风险后谨慎使用：

1. **服务条款违规 (TOS Violation)**：本脚本修改了 Claude Desktop 的官方二进制文件、底层框架及安全校验机制。此行为**严格违反了 Anthropic 的服务条款 (Terms of Service)**。
2. **账号封禁风险 (Account Ban)**：使用非官方修改版客户端可能会触发服务端的异常检测，进而导致您的 Anthropic 账号被**限制或永久封禁**。
3. **系统安全风险 (System Security)**：执行此补丁需要 `sudo` (Root) 权限来修改 `/Applications` 系统目录下的文件，并重新签名应用。**在运行任何需要 Root 权限的第三方脚本前，强烈建议您自行审查源码。** 修改应用的签名和 Entitlements 可能会改变应用原有的沙盒隔离机制。
4. **无担保 (No Warranty)**：**作者不对任何因使用本脚本（包括但不限于账号封禁、数据丢失、系统崩溃、应用损坏或任何法律纠纷）承担任何直接或间接责任。使用本工具产生的任何后果由使用者完全自负。**

## 🙏 致谢 (Acknowledgments)

本项目中整合的**中文汉化 (i18n)** 资源主要来源于开源社区的无私贡献，特别感谢以下项目及原作者：
- [javaht/claude-desktop-zh-cn](https://github.com/javaht/claude-desktop-zh-cn) - 感谢其提供的全面且优质的 Claude Desktop 汉化资源文件（涵盖前端 UI、客户端菜单及各项提示信息的完整翻译）。

## 📄 开源协议 (License)

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

> **The MIT License (MIT)**
> 
> 本软件按“原样”提供，不带有任何明示或暗示的担保，包括但不限于对适销性、特定用途的适用性和非侵权性的担保。在任何情况下，作者或版权持有人均不对因软件或软件的使用或其他交易而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权诉讼或其他诉讼中。
