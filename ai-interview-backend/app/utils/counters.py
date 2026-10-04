"""计数列的数据库端原子自增 / 自减。

项目里多处用「ORM 读出来 ± 1 再写回」维护计数（点赞数、收藏数、阅读量）。
这种写法有两个问题：

1. **并发丢失更新**：两个请求同时读到 5，各自算成 6 再写回，最终只 +1；
2. **NULL 直接崩**：计数列可空（老数据、手工 SQL 插入未带该列），
   Python 侧 `None - 1` 会抛 TypeError，接口 500。

改为一条 UPDATE 在数据库端完成，用 COALESCE 兜住 NULL，用 GREATEST 保证不出现负数。
"""
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession


async def bump_counter(db: AsyncSession, model, pk_value: int, column, delta: int) -> int:
    """原子地把 ``model.column`` 加 ``delta``（可为负），返回更新后的值。

    只适用于「单列整数计数」这种场景：真实业务字段仍应走 ORM 读改写以便校验。
    """
    expression = func.coalesce(column, 0) + delta
    if delta < 0:
        # 与原先 Python 侧 max(0, ...) 的语义保持一致，避免计数被减成负数
        expression = func.greatest(expression, 0)
    updated = await db.scalar(
        update(model)
        .where(model.id == pk_value)
        .values({column.key: expression})
        .returning(column)
        .execution_options(synchronize_session=False)
    )
    return int(updated or 0)
