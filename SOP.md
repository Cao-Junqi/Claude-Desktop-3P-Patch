# SOP — 标准操作流程

本文档定义 Claude-Desktop-3P-Patch 项目的标准操作流程（Standard Operating Procedure）。配套文件：[AGENTS.md](AGENTS.md)（维护状态）、[HANDOFF.md](HANDOFF.md)（交接）、[CHANGELOG.md](CHANGELOG.md)（变更日志）。

---

## 流程总览

| # | 流程 | 触发条件 | 产出 | 责任 |
|---|---|---|---|---|
| 1 | 首次安装 / 升级 Claude | 手动下载新版 DMG | 已 patch 的 `/Applications/Claude.app` | 用户 |
| 2 | **脚本更新流程** | 新版 Claude 导致 patch 层失效 | 更新后的 `patch_claude_3p_v2.py` | AI + 人工 |
| 3 | 文档与发布 | 脚本更新完成 | README + CHANGELOG + git 提交 | AI + 人工 |

---

## 流程 1：安装 / 升级 Claude

用户手动从 [claude.ai/download](https://claude.ai/download) 下载新版 DMG 后，安装并打补丁。详见 [INSTALL_APPLICATION_PATCH.md](INSTALL_APPLICATION_PATCH.md)。

**最小正式命令**：

```bash
cd "/Users/junqi/Documents/本地代码项目/03-AI与应用定制项目/Claude-Desktop-3P-Patch"

# 1. 退出正在运行的 Claude
osascript -e 'quit app "Claude"' 2>/dev/null || true

# 2. 安装新版到 /Applications（先备份旧版）
hdiutil attach Claude-XXXX.dmg
mv /Applications/Claude.app /Applications/Claude-backup.app
cp -R "/Volumes/Claude/Claude.app" /Applications/
xattr -cr /Applications/Claude.app
hdiutil detach /Volumes/Claude

# 3. 打补丁（汉化 + 解除 3P/本地限制 + 禁用自动更新）
sudo python3 patch_claude_3p_v2.py \
  --app /Applications/Claude.app \
  --provider gateway \
  --feature-recovery \
  --zh-cn \
  --write-policy \
  --launch \
  --report-json /tmp/claude-3p-installed.json
```

> ⚠️ 每次升级后都要重跑 patch。官方升级会覆盖本地改动。

---

## 流程 2：脚本更新流程（核心）

**触发条件**：新版 Claude Desktop 发布，`--dry-run` 出现 patch 层 `missing`。

**目标**：让 `patch_claude_3p_v2.py` 适配新版，全层命中，验证无误后发布。

### 步骤 0 · 环境准备

```bash
cd "/Users/junqi/Documents/本地代码项目/03-AI与应用定制项目/Claude-Desktop-3P-Patch"
# 确认是主脚本、配套脚本、资源都在
ls patch_claude_3p_v2.py patch_claude_zh_cn.py resources/
```

### 步骤 1 · 挂载 DMG 并读版本号

```bash
hdiutil attach Claude-XXXX.dmg -nobrowse -readonly
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" \
  "/Volumes/Claude/Claude.app/Contents/Info.plist"
```

记录版本号（如 `1.26832.0`），后续写进 README / CHANGELOG。

### 步骤 2 · 提取 App 到 /tmp 并跑 dry-run

> **先做文件操作，最后再启动临时 App**。启动 /tmp 的临时 App 会触发 macOS TCC 撤销终端对 ~/Documents 的访问（见 AGENTS.md「TCC 注意事项」）。

```bash
# 提取到 /tmp（不碰 /Applications）
rm -rf /tmp/claude-new && mkdir -p /tmp/claude-new
cp -R "/Volumes/Claude/Claude.app" /tmp/claude-new/
hdiutil detach /Volumes/Claude   # 用完即卸

# dry-run，输出每层命中情况
python3 patch_claude_3p_v2.py \
  --app /tmp/claude-new/Claude.app \
  --provider gateway --feature-recovery --zh-cn --dry-run \
  --report-json /tmp/claude-new-dryrun.json
```

**判读**：逐层看 `applied` / `missing` / `ambiguous`。`missing` 的层就是需要补新特征码的。

### 步骤 3 · 提取新版 bundle 定位新特征码

新版若代码分割（0811 起），`.vite/build/` 会有大量 `index.chunk-*.js`。用脚本遍历 asar header 提取所有 `index*.js`：

```bash
python3 - <<'EOF'
import json, struct
asar = "/tmp/claude-new/Claude.app/Contents/Resources/app.asar"
data = open(asar,'rb').read()
hsize = struct.unpack('<I', data[12:16])[0]
hdr = json.loads(data[16:16+hsize])
base = 16 + hsize
out = []
def flat(node, path=''):
    if isinstance(node, dict) and 'offset' in node:
        o=node['offset']; s=node['size']
        if isinstance(o,dict): o=o['offset']
        if isinstance(s,dict): s=s['size']
        out.append((path, int(o), int(s)))
    elif isinstance(node, dict) and 'files' in node:
        for k,v in node['files'].items(): flat(v, path+'/'+k)
for k,v in hdr['files'].items(): flat(v, k)
import os
os.makedirs('/tmp/claude-new-build', exist_ok=True)
for p,o,s in out:
    if '.vite/build/' in p and p.endswith('.js') and 'worker' not in p and s < 3_000_000:
        dest = '/tmp/claude-new-build/' + p.split('.vite/build/')[1].replace('/','__')
        open(dest,'wb').write(data[base+o:base+o+s])
print('extracted', sum(1 for p,_,_ in out if '.vite/build/' in p and p.endswith('.js')), 'build js files')
EOF
```

### 步骤 4 · grep 定位每层新特征码

在 `/tmp/claude-new-build/` 里用现有特征串的关键片段反向搜索：

```bash
cd /tmp/claude-new-build
grep -rl 'safeParse' . | head                        # L1
grep -rl 'return{ok:!0}' . | head                    # L2c / L2
grep -rl 'Auto-updates disabled' . | head            # L4
grep -rl 'is not an Anthropic model' . | head        # L5
grep -rl 'title-gen' . | head                        # L6
grep -rl 'xhigh' . | head                            # L7
```

**要点**：
- 每层新特征码要求**等长**（JS byte offset 不能变），用 `pad_bytes()` 补齐。
- 同名 validator 可能同时出现在 chunk 和 `index.pre.js`，两处都要 p。
- 找唯一前缀避免 ambiguous（如 `function me(e){return ce(e)?{ok:!0}:{ok:!1,reason:` 而非裸 `{ok:!1`）。
- 若某层在新版已不存在/被原生处理，注释掉并记录「新版不再需要」（0811 的 L2b / L7 即如此）。

### 步骤 5 · 更新 `build_index_patch_specs()`

在 `patch_claude_3p_v2.py` 的 `build_index_patch_specs()` 中，为失效层**追加**新版 alternatives（`original, replacement, allow_multi`），保留旧版作 fallback。

```python
# 示例：L2c 追加 0811 gateway validator（等长替换）
(b'function me(e){return ce(e)?{ok:!0}:{ok:!1,reason:',
 b'function me(e){return ce(e)?{ok:!0}:{ok:!0,reason:', False),
```

### 步骤 6 · AI 自动验证

```bash
# 语法
python3 -c "import ast; ast.parse(open('patch_claude_3p_v2.py').read())"

# dry-run 全命中
python3 patch_claude_3p_v2.py \
  --app /tmp/claude-new/Claude.app \
  --provider gateway --feature-recovery --zh-cn --dry-run \
  --report-json /tmp/claude-new-dryrun2.json

# 读 JSON 报告，确认无 missing / ambiguous
python3 -c "
import json
r=json.load(open('/tmp/claude-new-dryrun2.json'))
for s in ['applied','missing','ambiguous']:
    ps=[p for p in r['asar']['patches'] if p['status']==s]
    print(s, len(ps))
"

# 正式 patch 临时 App（写 /tmp，不装 /Applications）
rm -rf /tmp/claude-new-test && mkdir -p /tmp/claude-new-test
cp -R /tmp/claude-new/Claude.app /tmp/claude-new-test/
python3 patch_claude_3p_v2.py \
  --app /tmp/claude-new-test/Claude.app \
  --provider gateway --feature-recovery --zh-cn \
  --report-json /tmp/claude-new-patched.json

# 对被 patch 的文件跑 CJS 语法检查（✦ 关键，App 按 CJS 加载）
# 提取被 patch 的 index*.js 后：
node --check <提取的-bundle>.js
```

**AI 验证通过标准**：dry-run 全层 `applied`、JSON 报告无 `missing`/`ambiguous`、所有被 patch 文件 `node --check` 通过（CJS 模式）、`codesign --verify` OK。

### 步骤 7 · 人工验证

```bash
open /tmp/claude-new-test/Claude.app
```

人工逐项确认：

- [ ] App 稳定启动（≥10 秒不崩溃、无 launch-failure 报错）
- [ ] 界面中文覆盖正常
- [ ] 3P 模型在下拉框可见
- [ ] 选 3P 模型发消息不报 `effort=xhigh` / `Invalid custom3p managed config`
- [ ] 新会话标题有本地兜底
- [ ] 自动更新被禁用（设置里）

> 人工验证**这步会再次触发 TCC 锁**（启动 /tmp App）。故放在所有文件操作之后。

### 步骤 8 · 更新 README + CHANGELOG + 提交

```bash
# 更新 README.md 版本号（0703→0811 等所有引用）
# 更新 CHANGELOG.md 加新条目（日期-主题，最新在上）

git add -A
git commit -m "适配 XXXX (版本号) + 变更摘要"
git push origin main
```

---

## 流程 3：文档与发布清单

每次脚本更新发布前，逐项核对：

- [ ] `patch_claude_3p_v2.py` 特征码已更新，dry-run 全命中
- [ ] `node --check` + `codesign` 通过
- [ ] 人工验证通过（见流程 2 步骤 7）
- [ ] README.md 版本号已更新
- [ ] CHANGELOG.md 新增条目
- [ ] AGENTS.md / HANDOFF.md 若涉及维护状态则同步
- [ ] `git commit` + `git push origin main`

---

## 术语

| 术语 | 含义 |
|---|---|
| dry-run | 只报告 patch 命中情况，不写 App |
| missing | patch 层特征码未命中（需适配新版） |
| applied | patch 层命中并应用 |
| ambiguous | 特征码出现多次且未 allow_multi（需加唯一前缀） |
| 等长 patch | replacement 与 original 字节长度一致，避免破坏 ASAR 布局 |
| TCC | macOS 隐私权限，启动 /tmp 临时 App 会撤销 ~/Documents 访问 |