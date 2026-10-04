"""并发面试上限的行为锁定。

背景：start_interview 与 start_practice_from_experience 都是「先调 AI 出题、再建记录」。
此前没有任何并发上限 —— 反复点「开始面试」既刷掉 AI 额度，又会堆出一批永远不完成的
僵尸会话（它们会一直停在 in_progress，反过来把后续请求也堵住）。
"""

import asyncio

import pytest
from sqlalchemy.sql.elements import BindParameter

from app.core.config import settings
from app.exceptions.http_exceptions import ValidationError
from app.models.interview import Interview
from app.services.client.interview_service import InterviewService


def _iter_leaf_criteria(clause):
    """把 WHERE 子句拍平成叶子条件（兼容 and_ 组合与单个条件）。"""
    if clause is None:
        return []
    children = getattr(clause, "clauses", None)
    if children is None:
        return [clause]
    leaves = []
    for child in children:
        leaves.extend(_iter_leaf_criteria(child))
    return leaves


def _eq_filters(query):
    """提取 WHERE 中的等值条件。"""
    filters = {}
    for leaf in _iter_leaf_criteria(getattr(query, "whereclause", None)):
        column = getattr(getattr(leaf, "left", None), "key", None)
        right = getattr(leaf, "right", None)
        if column and isinstance(right, BindParameter):
            filters[column] = right.value
    return filters


class _InterviewDb:
    """按 WHERE 条件真实过滤的最小替身。

    不解析条件的话，「只统计本人 in_progress」这条规则在测试里就等于没被验证。
    """

    def __init__(self, interviews):
        self.interviews = list(interviews)

    async def scalar(self, query):
        filters = _eq_filters(query)
        return sum(
            1
            for item in self.interviews
            if all(getattr(item, key, None) == value for key, value in filters.items())
        )


def _interview(user_id=1, status="in_progress"):
    return Interview(id=1, user_id=user_id, status=status)


def test_allows_below_limit():
    db = _InterviewDb([_interview() for _ in range(settings.MAX_CONCURRENT_INTERVIEWS - 1)])
    asyncio.run(InterviewService._assert_concurrent_limit(db, 1))


def test_blocks_at_limit():
    db = _InterviewDb([_interview() for _ in range(settings.MAX_CONCURRENT_INTERVIEWS)])
    with pytest.raises(ValidationError):
        asyncio.run(InterviewService._assert_concurrent_limit(db, 1))


def test_ignores_completed_interviews():
    """已完成的面试不该占用额度。"""
    db = _InterviewDb(
        [_interview(status="in_progress") for _ in range(settings.MAX_CONCURRENT_INTERVIEWS - 1)]
        + [_interview(status="completed") for _ in range(5)]
    )
    asyncio.run(InterviewService._assert_concurrent_limit(db, 1))


def test_ignores_other_users():
    """别人进行中的面试不该算到当前用户头上。"""
    db = _InterviewDb([_interview(user_id=999) for _ in range(settings.MAX_CONCURRENT_INTERVIEWS + 5)])
    asyncio.run(InterviewService._assert_concurrent_limit(db, 1))
