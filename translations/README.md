# 汉化翻译管线（2026-08-11）

本次把 Claude Desktop 0811（1.26832.0）缺译的 **11664 条**英文字符串机翻补齐，全部并入 `resources/frontend-zh-CN.json`（12355 → 24019 key，重打补丁后 `20436 translated / 0 fallback`）。

## 目录内容

| 文件 | 说明 |
|---|---|
| `batch_001~024.json` | 英文源串，按长度排序分 24 批（`key → 英文原文`），取自 App `en-US.json` 与 `frontend-zh-CN.json` 的差集 |
| `translated_001~024.json` | 对应批次的机翻结果（`key → 中文`） |
| `check_and_merge.py` | 校验 + 合并工具 |
| 最终产物 | `../resources/frontend-zh-CN.json` |

## 翻译规则

- 保留 ICU 格式：`{占位符}`、`{n, plural, one {..} other {..}}`、`<link>` 等标签原样保留。
- 专有名词保留英文：Claude / MCP / Cowork / 模型名（Opus、Sonnet、Haiku、Fable）/ API 术语等。
- 官方 Anthropic 中文包本就只覆盖 44%（9057/20721），本补全**超出官方范围**，属本项目自定义增强（用户确认全部保留）。

## 如何复现 / 续翻

校验（检查各批是否全覆盖、占位符是否丢失）：

```bash
python3 translations/check_and_merge.py check
```

合并（把 translated_*.json 并入 `resources/frontend-zh-CN.json`）：

```bash
python3 translations/check_and_merge.py merge
```

若后续版本出现新的缺译，可复用同一流程：

```bash
# 1. 从新版本 en-US.json 与现有 frontend-zh-CN.json 算出差集并分批
python3 - <<'EOF'
import json, os
en = json.load(open('<新版>/ion-dist/i18n/en-US.json'))
zh = json.load(open('resources/frontend-zh-CN.json'))
missing = {k: en[k] for k in en if k not in zh}
items = sorted(missing.items(), key=lambda kv: (len(kv[1]), kv[0]))
os.makedirs('translations/new_batches', exist_ok=True)
for i in range(0, len(items), 500):
    with open(f'translations/new_batches/batch_{(i//500)+1:03d}.json', 'w') as f:
        json.dump(dict(items[i:i+500]), f, ensure_ascii=False, indent=1)
print('新缺译', len(items), '条')
EOF
# 2. 翻译后把 translated_*.json 放入 translations/，运行 check + merge
```
