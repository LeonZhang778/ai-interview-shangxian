"""纯静态校验 alembic 迁移链（不连库）。

直接用 alembic.script.ScriptDirectory 读取 versions 目录，
通过 alembic 自身的解析逻辑校验 head / 分叉 / 断链，
避免触发 env.py 里的数据库连接逻辑。

用法: python scripts/codepus-agent/alembic_verify.py
"""
import os
import sys

from alembic.script import ScriptDirectory

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT_LOC = os.path.join(PROJECT_ROOT, "migrations")


def main() -> int:
    script = ScriptDirectory.from_config  # noqa
    # 直接用 from_config 不行（需要 Config 对象），改为构造 ScriptDirectory
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", SCRIPT_LOC)
    script = ScriptDirectory.from_config(cfg)

    exit_code = 0

    heads = script.get_heads()
    print(f"=== HEADS ({len(heads)}) ===")
    for h in heads:
        rev = script.get_revision(h)
        print(f"  {h}  ({rev.path})")
    if len(heads) != 1:
        print(f"!! ERROR: 期望唯一 head，实际有 {len(heads)} 个 -> 分叉/多分支")
        exit_code = 1

    print()
    # 遍历所有 revision，检查 down_revision 指向是否都存在
    print("=== WALK REVISIONS ===")
    # get_revisions 返回所有 revision（按链）
    all_revs = {}
    for rev in script.walk_revisions():
        all_revs[rev.revision] = rev

    rev_ids = set(all_revs.keys())
    broken = []
    for rid, rev in all_revs.items():
        downs = rev.down_revision  # None | str | Tuple[str, ...]
        if downs is None:
            continue  # 链头 root revision
        if isinstance(downs, str):
            downs = (downs,)
        for d in downs:
            if d not in rev_ids:
                broken.append((rid, d))
                print(f"!! BROKEN: {rid} -> down_revision '{d}' 不存在")
    if broken:
        exit_code = 1
    else:
        print(f"  OK: 所有 down_revision 指向均有效 (共 {len(all_revs)} 个 revision, 含 1 个 root)")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
