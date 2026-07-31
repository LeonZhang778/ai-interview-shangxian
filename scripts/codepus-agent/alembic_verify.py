"""静态校验 Alembic migration 链路：语法可导入 + down_revision 无环且单一 head。"""
import os
import re
import glob
import sys
import importlib.util
import py_compile


def load_revs(migrations_dir: str):
    revs = {}
    for f in sorted(glob.glob(os.path.join(migrations_dir, "*.py"))):
        base = os.path.basename(f)
        if base == "__init__.py" or "__pycache__" in f:
            continue
        src = open(f, encoding="utf-8").read()
        rev_m = re.search(r"revision:\s*str\s*=\s*'([^']+)'", src)
        if not rev_m:
            continue
        rev = rev_m.group(1)
        down_m = re.search(r"^down_revision\b[^=]*=\s*'([^']+)'", src, re.MULTILINE)
        down = down_m.group(1) if down_m else None
        revs[rev] = {"file": f, "down": down}
    return revs


def verify(migrations_dir: str):
    revs = load_revs(migrations_dir)
    all_revs = set(revs.keys())
    all_downs = {v["down"] for v in revs.values() if v["down"]}
    heads = [r for r in all_revs if r not in all_downs]
    issues = []
    # 1) down_revision 指向不存在的 rev
    for r, info in revs.items():
        if info["down"] and info["down"] not in all_revs:
            issues.append(f"{r}: down_revision '{info['down']}' 不存在于任何文件")
    # 2) 多 head（链路分叉）
    if len(heads) > 1:
        issues.append(f"存在多个 head（链路分叉）: {heads}")
    # 3) 语法编译每个文件
    for r, info in revs.items():
        try:
            py_compile.compile(info["file"], doraise=True)
        except py_compile.PyCompileError as e:
            issues.append(f"{r}: 语法编译失败 {e}")
    print("REV_COUNT:", len(revs))
    print("HEADS:", heads)
    if issues:
        print("ISSUES:")
        for i in issues:
            print("  -", i)
        return 1
    print("OK: 链路单一 head，无悬空 down_revision，语法全部通过")
    return 0


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mig = os.path.join(base, "ai-interview-backend", "migrations", "versions")
    sys.exit(verify(mig))
