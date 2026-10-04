"""迁移门禁：断言「从零跑完迁移链后，库里的表与模型定义完全一致」。

为什么需要它：
在此之前没有任何检查能发现「9 张表只有模型、没有迁移」这件事 —— 结果是全新环境
`alembic upgrade head` 直接失败（f7a8b9c0d1e2 要给 interviews 加指向 experiences 的外键，
而 experiences 根本没有迁移），环境完全无法重建，也就谈不上 staging、灾备或本地复现。

后来补做表级检查后，又暴露了第二类漂移：**列级形状不一致**。
    experiences 这张表在线上是手工 SQL 建的（计数列带 `DEFAULT 0`），而模型里只写了
    Python 层 `default=0`，于是迁移链建出来的表没有默认值、列也可空 —— 同一个仓库
    在不同环境跑出两种结构，直接 INSERT 时一边得 0、一边得 NULL。
表级检查看不见这种差异，所以这里再做列级校验：
    1) 模型声明了 server_default 的列，库里必须真的有默认值；
    2) 模型声明 nullable=False 的列，库里必须真的是 NOT NULL。
改了模型却没配套迁移（或迁移链与模型脱节）时，这一步会在推送阶段就拦下来。

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


def _load_db_columns(cur) -> dict:
    """读出每张表的列形状：是否可空、是否有默认值。"""
    cur.execute(
        """
        select table_name, column_name, is_nullable, column_default
        from information_schema.columns
        where table_schema = 'public'
        """
    )
    columns: dict = {}
    for table, column, is_nullable, column_default in cur.fetchall():
        columns.setdefault(table, {})[column] = {
            "nullable": is_nullable == "YES",
            "has_default": column_default is not None,
        }
    return columns


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
            db_columns = _load_db_columns(cur)
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

    # ---- 列级校验：只在表存在时进行，否则上面的缺失报告已经足够 ----
    missing_default: list[str] = []
    should_be_not_null: list[str] = []
    missing_columns: list[str] = []

    for table_name in sorted(expected & in_db):
        table = Base.metadata.tables[table_name]
        actual = db_columns.get(table_name, {})
        for column in table.columns:
            info = actual.get(column.name)
            if info is None:
                missing_columns.append(f"{table_name}.{column.name}")
                continue
            if column.server_default is not None and not info["has_default"]:
                missing_default.append(f"{table_name}.{column.name}")
            if not column.nullable and info["nullable"]:
                should_be_not_null.append(f"{table_name}.{column.name}")

    if missing_columns:
        print("  ❌ 表中缺列（迁移未跟上模型）: " + ", ".join(missing_columns))
    if missing_default:
        print("  ❌ 模型声明了默认值、库里没有（会造成不同环境行为不一致）: " + ", ".join(missing_default))
    if should_be_not_null:
        print("  ❌ 模型要求 NOT NULL、库里可空: " + ", ".join(should_be_not_null))

    failed = bool(missing or missing_columns or missing_default or should_be_not_null)
    if failed:
        print("迁移门禁失败：环境无法从零重建，或与模型定义不一致。")
        return 1

    print("迁移门禁通过：库结构与模型一致（表、列、默认值、可空性），环境可重建。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

