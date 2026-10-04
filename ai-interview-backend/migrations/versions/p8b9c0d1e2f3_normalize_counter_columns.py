"""normalize counter columns to NOT NULL DEFAULT 0

把「计数列」在**所有环境**里收敛到同一种形状：NOT NULL + DEFAULT 0。

背景（一次真实的 schema 漂移）：
    experiences 这张表在线上是手工 SQL 建的，计数列带着 `DEFAULT 0`；
    而模型里只写了 Python 层 `default=0`（无 server_default、列可空）。
    于是同一个仓库在不同环境跑出两种表结构：
      - 线上：`view_count integer DEFAULT 0`（可空）
      - 全新环境：`view_count integer`（可空、无默认）
    直接 INSERT 不带该列时，前者得 0、后者得 NULL，读取路径就被迫到处写
    COALESCE 兜底。约束不写在模型里，漂移就会随每一次重建复发。

本次同时做两件事：
    1) 模型侧补上 `nullable=False, server_default="0"`（根治，见 app/models/*.py）；
    2) 本迁移把**已存在的库**（手工建的、或按旧模型建的）幂等对齐 —— 这是必需的，
       因为迁移链里那条 create_table 早已固化，不会因为模型改动而重新生成 DDL。

安全性：
    - 纯 DDL 收缩，不删除任何数据。
    - 先 `UPDATE ... SET c = 0 WHERE c IS NULL` 再 `SET NOT NULL`，因此库中即使存在
      NULL 也不会让 ALTER 失败（这是 SET NOT NULL 唯一会失败的原因）。
    - 表/列不存在则跳过，因此在任意迁移阶段、任意环境下均可安全执行。

Revision ID: p8b9c0d1e2f3
Revises: n7a8b9c0d1e2
Create Date: 2026-10-04 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p8b9c0d1e2f3'
down_revision: Union[str, None] = 'n7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (表名, 列名) —— 与 app/models 中带 server_default="0" 的计数列一一对应。
# 新增此类列时请同步本列表，否则门禁（check_migration_state）无法发现新的漂移。
_COUNTER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("experiences", "view_count"),
    ("experiences", "like_count"),
    ("experiences", "collect_count"),
    ("experience_comments", "like_count"),
    ("learning_notes", "view_count"),
    ("learning_notes", "like_count"),
    ("learning_notes", "collect_count"),
    ("learning_notes", "comment_count"),
    ("notebooks", "sort_order"),
    ("collection_groups", "sort_order"),
    ("public_note_comments", "like_count"),
    ("interviews", "current_question_index"),
    ("weakness_stats", "count"),
    ("media_tasks", "retry_count"),
)


def _table_columns(bind, table: str) -> set:
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    normalized, skipped = [], []

    for table, column in _COUNTER_COLUMNS:
        if column not in _table_columns(bind, table):
            skipped.append(f"{table}.{column}")
            continue

        # 1) 填 NULL：SET NOT NULL 唯一会失败的原因，先消灭它
        filled = bind.execute(
            sa.text(f'UPDATE "{table}" SET "{column}" = 0 WHERE "{column}" IS NULL')
        ).rowcount
        # 2) 补默认值（重复执行安全）
        bind.execute(
            sa.text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT 0')
        )
        # 3) 收紧为 NOT NULL（重复执行安全）
        bind.execute(
            sa.text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET NOT NULL')
        )
        normalized.append(f"{table}.{column}" + (f"(填 NULL {filled} 行)" if filled else ""))

    print(f"[{revision}] 计数列已收敛为 NOT NULL DEFAULT 0：{', '.join(normalized) or '无'}")
    if skipped:
        print(f"[{revision}] 表/列不存在，已跳过：{', '.join(skipped)}")


def downgrade() -> None:
    # 只回退「默认值」这一半：NOT NULL 回退成可空会重新引入 NULL 语义，
    # 且已把 NULL 填成 0，回退不能还原信息，故保持 NOT NULL。
    bind = op.get_bind()
    for table, column in _COUNTER_COLUMNS:
        if column not in _table_columns(bind, table):
            continue
        bind.execute(
            sa.text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT')
        )
