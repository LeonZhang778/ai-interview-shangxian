"""迁移门禁：断言「从零跑完迁移链后，库里的表与模型定义完全一致」。

为什么需要它：
在此之前没有任何检查能发现「9 张表只有模型、没有迁移」这件事 —— 结果是全新环境
`alembic upgrade head` 直接失败（f7a8b9c0d1e2 要给 interviews 加指向 experiences 的外键，
而 experiences 根本没有迁移），环境完全无法重建，也就谈不上 staging、灾备或本地复现。

用法（在已执行 `alembic upgrade head` 的干净库上运行）：
    python scripts/check_migration_state.py
不一致时以非零退出，作为 CI 门禁。
"""

from __future__ import annotations

import glob
import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.models import Base  # noqa: E402


def import_all_models() -> None:
    """与 migrations/env.py 保持一致：导入 app/models 下全部模块以注册 metadata。"""
    for path in glob.glob(str(ROOT / "app" / "models" / "*.py")):
        stem = pathlib.Path(path).stem
        if stem.startswith("_"):
            continue
        importlib.import_module(f"app.models.{stem}")


def main() -> int:
    import_all_models()

    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname=settings.POSTGRES_DB,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("select tablename from pg_tables where schemaname = 'public'")
            in_db = {row[0] for row in cur.fetchall()} - {"alembic_version"}
    finally:
        conn.close()

    expected = set(Base.metadata.tables)

    missing = sorted(expected - in_db)
    extra = sorted(in_db - expected)
    print(f"迁移门禁: 库中 {len(in_db)} 张表 / 模型 {len(expected)} 张表")

    if missing:
        print("  ❌ 模型有、库中缺失（说明缺少迁移）: " + ", ".join(missing))
    if extra:
        print("  ⚠️ 库中有、模型没有（可能是历史残留）: " + ", ".join(extra))

    if missing:
        print("迁移门禁失败：环境无法从零重建。")
        return 1

    print("迁移门禁通过：库结构与模型一致，环境可重建。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
