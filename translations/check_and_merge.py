#!/usr/bin/env python3
"""Validate translated batches (full key coverage + ICU placeholder preservation)
and merge them into resources/frontend-zh-CN.json.
"""
import json, re, sys
from pathlib import Path

BATCH_DIR = Path(__file__).resolve().parent
RESOURCE = Path(__file__).resolve().parent.parent / "resources" / "frontend-zh-CN.json"

PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}|<[^>]*>")


def placeholders(s: str) -> list[str]:
    """Extract placeholders. ICU plural blocks (`{n, plural, one {..} other {..}}`) are
    normalized to `{<var>, plural}` since the inner text is translated; the important
    part is the variable name and the plural keyword.
    """
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "{":
            depth = 0
            j = i
            while j < n:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            block = s[i : j + 1]
            if ", plural," in block or ", select," in block:
                # normalize to `{<var>, plural}` — inner branches are translated
                head = block.split("{", 2)[1].split(",")[0].strip()
                out.append(f"{{{head}, plural}}")
            else:
                out.append(block)
            i = j + 1
        elif c == "<":
            j = s.find(">", i)
            if j == -1:
                j = n - 1
            out.append(s[i : j + 1])
            i = j + 1
        else:
            i += 1
    return out


def validate(batch_n: int) -> tuple[dict, dict, list[str]]:
    src = json.loads((BATCH_DIR / f"batch_{batch_n:03d}.json").read_text(encoding="utf-8"))
    tr = json.loads((BATCH_DIR / f"translated_{batch_n:03d}.json").read_text(encoding="utf-8"))
    missing = [k for k in src if k not in tr]
    extra = [k for k in tr if k not in src]
    problems: list[str] = []
    for k, en in src.items():
        zh = tr.get(k)
        if zh is None:
            continue
        en_phs = set(placeholders(en))
        zh_phs = set(placeholders(zh))
        lost = en_phs - zh_phs
        if lost:
            problems.append(f"{k}: lost placeholders {sorted(lost)} | en={en!r} -> zh={zh!r}")
    return src, tr, missing + problems


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    batches = sorted(
        int(p.stem.split("_")[1])
        for p in BATCH_DIR.glob("batch_*.json")
        if (BATCH_DIR / f"translated_{p.stem.split('_')[1]}.json").exists()
    )
    merged: dict = {}
    total_missing = 0
    total_problems = 0
    for n in batches:
        src, tr, problems = validate(n)
        merged.update(tr)
        total_missing += len([k for k in src if k not in tr])
        total_problems += len(problems)
        if problems:
            print(f"[batch {n}] {len(problems)} problems:")
            for p in problems[:5]:
                print("   ", p)
    print(f"\n== summary ==\nbatches={len(batches)} missing_keys={total_missing} placeholder_problems={total_problems}")
    print(f"translated keys total={len(merged)}")

    if mode == "merge":
        if total_missing or total_problems:
            print("refusing to merge: validation failed", file=sys.stderr)
            sys.exit(1)
        zh = json.loads(RESOURCE.read_text(encoding="utf-8"))
        before = len(zh)
        zh.update(merged)
        RESOURCE.write_text(json.dumps(zh, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"merged: frontend-zh-CN.json {before} -> {len(zh)} keys")


if __name__ == "__main__":
    main()
