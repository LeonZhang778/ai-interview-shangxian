"""unique interview_message per (interview, role, question)

把「每场面试的每一题、同一角色只有一条消息」从应用层约定升级为数据库不变量。

背景：幂等此前只靠应用层「先查后写」（save_results_node 的守卫 +
_get_duplicate_submission_result）。并发下两个请求可以同时查不到已存在的记录，
于是同一题被写入两次，current_question_index 也被推进两次 —— 用户会莫名少答一题，
面试报告里还可能出现重复题目气泡。SSE 断线重连时前端重发同一答案即可触发。

生产库可能已经存在这类重复行，直接建唯一约束会失败。因此先按
(interview_id, role, question_index) 分组，只保留 id 最大的一条（即最后一次写入，
语义上等于应用当前的行为：读历史时取 id 最大、报告按题号覆盖），并打印删除数量，
便于事后核对。

Revision ID: n7a8b9c0d1e2
Revises: m6f7g8h9i0j1
Create Date: 2026-10-04 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n7a8b9c0d1e2'
down_revision: Union[str, None] = 'm6f7g8h9i0j1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "uq_interview_message_question"
TABLE_NAME = "interview_messages"

# 「有更新的同组记录」的判定：同一 (interview_id, role, question_index) 下 id 更小。
# question_index IS NOT NULL 是显式保护 —— 现存的历史 NULL 行不参与该约束，
# Postgres 的唯一约束本身也视 NULL 互不相等。
_DUPLICATE_PREDICATE = f"""
    interview_id IS NOT NULL
    AND role IS NOT NULL
    AND question_index IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM {TABLE_NAME} newer
        WHERE newer.interview_id = {TABLE_NAME}.interview_id
          AND newer.role = {TABLE_NAME}.role
          AND newer.question_index = {TABLE_NAME}.question_index
          AND newer.id > {TABLE_NAME}.id
    )
"""


def _existing_unique_names(bind) -> set:
    return {c["name"] for c in sa.inspect(bind).get_unique_constraints(TABLE_NAME)}


def upgrade() -> None:
    bind = op.get_bind()

    duplicates = bind.execute(
        sa.text(f"SELECT count(*) FROM {TABLE_NAME} WHERE {_DUPLICATE_PREDICATE}")
    ).scalar_one()
    if duplicates:
        affected = bind.execute(
            sa.text(
                f"SELECT count(DISTINCT interview_id) FROM {TABLE_NAME} WHERE {_DUPLICATE_PREDICATE}"
            )
        ).scalar_one()
        print(
            f"[{revision}] 发现 {duplicates} 条重复面试消息（涉及 {affected} 场面试），"
            "保留每题每角色 id 最大的那条，其余删除。"
        )
        bind.execute(sa.text(f"DELETE FROM {TABLE_NAME} WHERE {_DUPLICATE_PREDICATE}"))
    else:
        print(f"[{revision}] 无重复面试消息，直接建唯一约束。")

    if CONSTRAINT_NAME in _existing_unique_names(bind):
        print(f"[{revision}] 唯一约束已存在，跳过。")
        return

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        ["interview_id", "role", "question_index"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if CONSTRAINT_NAME in _existing_unique_names(bind):
        op.drop_constraint(CONSTRAINT_NAME, TABLE_NAME, type_="unique")
