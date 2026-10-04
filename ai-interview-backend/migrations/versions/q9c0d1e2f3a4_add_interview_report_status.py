"""add interviews.report_status

把「报告是否就绪」从 `status=completed` 里拆出来。

改造前：最后一题的评分、`status=completed`、报告 JSON 三者在**同一个事务**里落库，
所以 SSE 的 done 事件必须等报告生成完（几十秒的 LLM 静默）才能发出去；用户看到的是
「AI 思考中」光标长时间不动。前端的 `GET /messages` 也正是靠 status=completed 兜住
「done 丢失后跳报告页」这一场景的。

改造后：最后一题提交时只写 `status=completed` + `report_status=pending`（同事务，
保证前端永远不会看到「已完成但没有就绪标记」的中间态），报告交给 Celery 生成。
于是 done 事件可以在评分结束的瞬间发出，只有报告的等待被挪到报告页。

因此本列必须与前端轮询**同一次上线**：若后端已改而前端仍以 completed 作为
「报告可读」的信号，用户在报告就绪前进入报告页会看到空白。

默认 ready：历史数据（报告早已生成）与进行中的面试都落在这个值上，
不需要数据回填即可保持原行为。

Revision ID: q9c0d1e2f3a4
Revises: r0d1e2f3a4b5
Create Date: 2026-10-04 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'q9c0d1e2f3a4'
down_revision: Union[str, None] = 'r0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "interviews"
COLUMN_NAME = "report_status"


def _columns(bind) -> set:
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    bind = op.get_bind()
    if COLUMN_NAME in _columns(bind):
        print(f"[{revision}] {TABLE_NAME}.{COLUMN_NAME} 已存在，跳过。")
        return

    # server_default 必须给：这张表已有生产数据，加 NOT NULL 列时没有默认值会直接失败；
    # 而且默认值必须是 ready —— pending 会让所有历史面试在下次打开报告页时被误判为
    # 「生成中」，进而触发一次不必要的重新生成。
    op.add_column(
        TABLE_NAME,
        sa.Column(
            COLUMN_NAME,
            sa.String(length=20),
            nullable=False,
            server_default="ready",
        ),
    )
    print(f"[{revision}] 已新增 {TABLE_NAME}.{COLUMN_NAME}（默认 ready，历史数据无需回填）。")


def downgrade() -> None:
    bind = op.get_bind()
    if COLUMN_NAME in _columns(bind):
        op.drop_column(TABLE_NAME, COLUMN_NAME)
