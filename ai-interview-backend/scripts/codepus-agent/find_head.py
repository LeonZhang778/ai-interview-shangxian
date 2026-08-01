"""快速分析 alembic 迁移链，找出 head revision 与断裂点。

用法: python scripts/codepus-agent/find_head.py
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
VERSIONS_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "migrations", "versions"))

REV_RE = re.compile(r"^revision(?:\s*:\s*\w+)?\s*=\s*[\"']([^\"']+)[\"']", re.M)
DOWN_RE = re.compile(
    r"^down_revision(?:\s*:\s*[^=]+?)?\s*=\s*(None|[\"'][^\"']+[\"'])", re.M
)


def main() -> None:
    revs = {}
    downs = {}
    for path in sorted(glob.glob(os.path.join(VERSIONS_DIR, "*.py"))):
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        rev_m = REV_RE.search(content)
        down_m = DOWN_RE.search(content)
        if not rev_m:
            print(f"!! no revision: {os.path.basename(path)}")
            continue
        rev = rev_m.group(1)
        down = None
        if down_m:
            raw = down_m.group(1)
            if raw == "None":
                down = None
            else:
                down = raw.strip("'\"")
        revs[rev] = os.path.basename(path)
        downs[rev] = down

    all_downs = {d for d in downs.values() if d}
    heads = [r for r in revs if r not in all_downs]
    missing = [d for d in all_downs if d not in revs]

    print("=== HEADS (no one points to them) ===")
    for h in heads:
        print(f"  {h}  ({revs[h]})")
    print()
    print("=== BROKEN down_revision (not a valid revision) ===")
    for m in missing:
        owner = next((r for r, d in downs.items() if d == m), "?")
        print(f"  {m}  referenced by {owner} ({revs.get(owner, '?')})")
    print()
    print("=== chain order (by revision) ===")
    for rev in sorted(revs):
        print(f"  {rev}  down={downs[rev]}  ({revs[rev]})")


if __name__ == "__main__":
    main()
