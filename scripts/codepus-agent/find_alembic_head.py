"""Find the current Alembic head revision by parsing migration files."""
import os
import re
import glob


def find_head(migrations_dir: str) -> str:
    revs = {}
    for f in glob.glob(os.path.join(migrations_dir, "*.py")):
        if os.path.basename(f) == "__init__.py":
            continue
        if "__pycache__" in f:
            continue
        content = open(f, encoding="utf-8").read()
        rev_match = re.search(r"revision:\s*str\s*=\s*'([^']+)'", content)
        if not rev_match:
            continue
        rev = rev_match.group(1)
        down_match = re.search(r"down_revision.*'([^']+)'", content)
        down = down_match.group(1) if down_match else None
        revs[rev] = down
    all_revs = set(revs.keys())
    all_downs = {v for v in revs.values() if v}
    heads = [r for r in all_revs if r not in all_downs]
    return heads[0] if heads else None


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mig = os.path.join(base, "ai-interview-backend", "migrations", "versions")
    print("MIGRATIONS_DIR:", mig)
    print("HEAD:", find_head(mig))
