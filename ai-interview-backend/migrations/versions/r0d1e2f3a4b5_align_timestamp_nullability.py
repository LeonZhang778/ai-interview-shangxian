"""align timestamp / status column nullability with models

第二类列级漂移：**模型要求 NOT NULL，库里却可空**。

这 4 张表（collection_groups / learning_notes / notebooks / notifications）的建表迁移
只写了 `server_default=sa.text('now()')`，漏了 `nullable=False`。而它们的模型继承自
BaseModel，声明的是 `nullable=False`。于是：

    - 迁移链建出来的表：created_at / updated_at 可空（有默认值，所以平时看不出问题）；
    - 由 `Base.metadata.create_all` 建出来的表（线上早期就是这样建表的）：NOT NULL。

两种环境形状不同，且可空的那一侧是**真风险** —— 任何显式写入 NULL 的路径都能成功，
之后所有依赖 created_at 的排序、统计、序列化都会踩到 None。
这个差异是迁移门禁的列级校验（scripts/check_migration_state.py）发现的。

顺带修 interviews.status：模型声明了 server_default='in_progress'，但建表迁移没给默认值。
status 可空且无默认值时，任何绕过 ORM 的 INSERT 都会写进 NULL，
而代码里到处是 `status == 'completed'` 这类比较 —— NULL 会让面试永远「无法结束」。
这里只补默认值，不收紧可空性（模型里它仍是可空的）。

安全性：先 `UPDATE ... SET = now() WHERE IS NULL` 再 `SET NOT NULL`，因此即使库里
存在 NULL 也不会让 ALTER 失败；表/列不存在则跳过，可在任意环境安全执行。

Revision ID: r0d1e2f3a4b5
Revises: p8b9c0d1e2f3
Create Date: 2026-10-04 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'r0d1e2f3a4b5'
down_revision: Union[str, None] = 'p8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 需要补成 NOT NULL 的时间戳列（模型里由 BaseModel 声明 nullable=False）
_NOT_NULL_TIMESTAMPS: tuple[tuple[str, ...], ...] = (
    ("collection_groups", "created_at", "updated_at"),
    ("learning_notes", "created_at", "updated_at"),
    ("notebooks", "created_at", "updated_at"),
    ("notifications", "created_at", "updated_at"),
)

# 需要补默认值的字符串列：(表, 列, 默认值)
_STRING_DEFAULTS: tuple[tuple[str, str, str], ...] = (
    ("interviews", "status", "in_progress"),
)


def _table_columns(bind, table: str) -> set:
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    tightened: list[str] = []
    defaulted: list[str] = []
    skipped: list[str] = []

    for table, *columns in _NOT_NULL_TIMESTAMPS:
        available = _table_columns(bind, table)
        for column in columns:
            if column not in available:
                skipped.append(f"{table}.{column}")
                continue
            filled = bind.execute(
                sa.text(
                    f'UPDATE "{table}" SET "{column}" = now() WHERE "{column}" IS NULL'
                )
            ).rowcount
            bind.execute(
                sa.text(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                    "SET DEFAULT now(), ALTER COLUMN "
                    f'"{column}" SET NOT NULL'
                )
            )
            tightened.append(
                f"{table}.{column}" + (f"(填 NULL {filled} 行)" if filled else "")
            )

    for table, column, value in _STRING_DEFAULTS:
        available = _table_columns(bind, table)
        if column not in available:
            skipped.append(f"{table}.{column}")
            continue
        # 只补默认值，不收紧可空性 —— 模型里这一列本来就是可空的
        bind.execute(
            sa.text(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT \'{value}\''
            )
        )
        defaulted.append(f"{table}.{column}")

    print(f"[{revision}] 时间戳列已收紧为 NOT NULL：{', '.join(tightened) or '无'}")
    print(f"[{revision}] 字符串列已补默认值：{', '.join(defaulted) or '无'}")
    if skipped:
        print(f"[{revision}] 表/列不存在，已跳过：{', '.join(skipped)}")


def downgrade() -> None:
    # 只回退「可空性」这一半：把列改回可空会重新引入 NULL 风险，
    # 且已把 NULL 填成 now()，回退不能还原信息，故保留 NOT NULL。
    bind = op.get_bind()
    for table, *columns in _NOT_NULL_TIMESTAMPS:
        available = _table_columns(bind, table)
        for column in columns:
            if column in available:
                bind.execute(
                    sa.text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP NOT NULL')
                )
