import asyncio
import json
import sys
import types
from decimal import Decimal


try:
    from passlib.context import CryptContext as _CryptContext  # noqa: F401
except ModuleNotFoundError:
    passlib_module = types.ModuleType("passlib")
    context_module = types.ModuleType("passlib.context")

    class _CryptContext:
        def __init__(self, *args, **kwargs):
            pass

        def hash(self, password):
            return f"hashed:{password}"

        def verify(self, plain_password, hashed_password):
            return hashed_password == f"hashed:{plain_password}"

    context_module.CryptContext = _CryptContext
    passlib_module.context = context_module
    sys.modules.setdefault("passlib", passlib_module)
    sys.modules.setdefault("passlib.context", context_module)

from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.sql.elements import BindParameter

from app.graphs.nodes.interview_nodes import evaluate_node, save_results_node
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.services.client.ai_service import AIService


def _iter_leaf_criteria(clause):
    """把 WHERE 子句拍平成叶子条件（兼容 and_ 组合与单个条件）。"""
    if clause is None:
        return []
    clauses = getattr(clause, "clauses", None)
    if clauses is None:
        return [clause]
    leaves = []
    for child in clauses:
        leaves.extend(_iter_leaf_criteria(child))
    return leaves


def _extract_row_filters(query):
    """从 select() 的 WHERE 子句提取等值与非空条件。

    假库必须像真实数据库一样按条件过滤：此前它无条件返回全部已评分消息，
    导致幂等守卫（question_index 精确匹配）在测试里从未被真正执行过。
    """
    equals, not_null = {}, set()
    for leaf in _iter_leaf_criteria(getattr(query, "whereclause", None)):
        column = getattr(getattr(leaf, "left", None), "key", None)
        if not column:
            continue
        operator_name = getattr(getattr(leaf, "operator", None), "__name__", "")
        right = getattr(leaf, "right", None)
        if operator_name == "eq" and isinstance(right, BindParameter):
            equals[column] = right.value
        elif operator_name == "is_not" and type(right).__name__ == "Null":
            not_null.add(column)
    return equals, not_null


class _ScalarResult:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class _ExecuteResult:
    def __init__(self, items):
        self._items = list(items)

    def scalars(self):
        return _ScalarResult(self._items)

    def scalar_one_or_none(self):
        # 与 SQLAlchemy 保持一致：多于一行时如实报错，避免假库把错误静默吞掉。
        if len(self._items) > 1:
            raise MultipleResultsFound(
                f"期望 0 或 1 行，实际 {len(self._items)} 行"
            )
        return self._items[0] if self._items else None


class _FakeDb:
    def __init__(self, interview, scored_messages=None):
        self.interview = interview
        self.scored_messages = list(scored_messages or [])
        self.added = []
        self.commits = 0

    async def get(self, model, item_id):
        return self.interview

    async def execute(self, query):
        equals, not_null = _extract_row_filters(query)
        rows = list(self.scored_messages) + [
            item for item in self.added if isinstance(item, InterviewMessage)
        ]
        if "interview_id" in equals:
            rows = [r for r in rows if r.interview_id == equals["interview_id"]]
        if "role" in equals:
            rows = [r for r in rows if r.role == equals["role"]]
        if "question_index" in equals:
            rows = [r for r in rows if r.question_index == equals["question_index"]]
        for column in not_null:
            rows = [r for r in rows if getattr(r, column, None) is not None]
        return _ExecuteResult(rows)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1


def test_evaluate_node_long_answer_with_skip_keyword_still_calls_ai(monkeypatch):
    """正常技术回答里出现「不会」不得被关键词短路，必须交给 AI 评估。

    回归：pre_score 曾对「不会」做任意位置子串匹配，导致 100+ 字的正常回答被
    直接判 4 分且完全不调用 AI（线上 admin/interviews/54 第 1、5 题）。
    """
    called = False

    async def fake_stream(*args, **kwargs):
        nonlocal called
        called = True
        yield "回答准确，覆盖了连接池与事务边界。\n```json\n{\"score\": 8.5}\n```"

    monkeypatch.setattr(AIService, "evaluate_answer_stream", fake_stream)

    answer = (
        "Django ORM 事务基于线程本地，async with session.begin() 开启事务；"
        "session 不会长期持有连接，执行 SQL 时才租借，必须手动关闭 session。"
    )
    result = asyncio.run(evaluate_node({
        "answer": answer,
        "current_question": "SQLAlchemy Async 与 Django ORM 的关键差异？",
        "parsed_resume": {},
        "chat_history": [],
        "chunk_queue": None,
    }))

    assert called is True
    assert result["score"] == 8.5


def test_pre_score_keyword_match_only_applies_to_short_answers():
    long_answer = (
        "命中缓存时不会打印 time.sleep(3.1)，用 RLock 双层校验保证线程安全，"
        "并在淘汰元素时同步清理 timestamp_map。"
    )
    assert len(long_answer) > AIService.MAX_SKIP_KEYWORD_LEN
    assert AIService.pre_score(long_answer) is None

    assert AIService.pre_score("不会") == (3.0, "honest_skip")
    assert AIService.pre_score("") == (1.0, "empty")


def test_fallback_evaluate_does_not_misjudge_long_answers():
    long_answer = (
        "session 不会长期持有连接，执行 SQL 时才租借，必须手动关闭以避免连接泄露，"
        "否则会耗尽数据库连接池。"
    )
    assert len(long_answer) > AIService.MAX_SKIP_KEYWORD_LEN
    long_result = AIService._fallback_evaluate(long_answer)
    assert long_result["score"] == 5.0
    assert long_result["skip_type"] is None

    short_result = AIService._fallback_evaluate("不会")
    assert short_result["score"] == 3.0
    assert short_result["skip_type"] == "honest_skip"


def test_evaluate_node_ai_failure_falls_back_without_fatal_error(monkeypatch):
    async def broken_stream(*args, **kwargs):
        raise RuntimeError("llm unavailable")
        if False:
            yield ""

    monkeypatch.setattr(AIService, "evaluate_answer_stream", broken_stream)

    result = asyncio.run(evaluate_node({
        "answer": "Redis 可以作为缓存、消息队列和分布式锁使用，常见数据结构包括字符串、哈希和集合。",
        "current_question": "Redis 的常见用途是什么？",
        "parsed_resume": {},
        "chat_history": [],
        "chunk_queue": None,
    }))

    assert result["score"] == 5.0
    assert result["evaluation"]["fallback"] is True
    assert result["evaluation"]["error"] == "llm unavailable"
    assert "error" not in result


def test_save_results_generates_report_with_matched_answers_and_scores(monkeypatch):
    captured = {}

    async def fake_generate_report(parsed_resume, target_position, questions_and_scores):
        captured["qa"] = questions_and_scores
        return {
            "summary": "ok",
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
        }

    monkeypatch.setattr(AIService, "generate_report", fake_generate_report)

    interview = Interview(
        id=1,
        user_id=10,
        target_position="后端开发",
        status="in_progress",
        current_question_index=2,
        questions_data=[
            {"question": "Q1"},
            {"question": "Q2"},
            {"question": "Q3"},
        ],
    )
    prior_messages = [
        InterviewMessage(
            interview_id=1,
            role="candidate",
            content="A1",
            question_index=0,
            score=Decimal("6.0"),
            feedback="F1",
        ),
        InterviewMessage(
            interview_id=1,
            role="candidate",
            content="A2",
            question_index=1,
            score=Decimal("7.0"),
            feedback="F2",
        ),
    ]
    db = _FakeDb(interview, prior_messages)

    result = asyncio.run(save_results_node({
        "db": db,
        "interview_id": 1,
        "user_id": 10,
        "current_index": 2,
        "is_finished": True,
        "score": 8.0,
        "feedback": "F3",
        "questions": interview.questions_data,
        "answer": "A3",
        "parsed_resume": {"skills": ["Python"]},
        "target_position": "后端开发",
        "chat_history": [],
        "next_question": None,
    }))

    assert db.commits == 1
    assert interview.status == "completed"
    assert float(interview.overall_score) == 7.0
    assert result["result"]["overall_score"] == 7.0
    assert captured["qa"] == [
        {"question": "Q1", "answer": "A1", "score": 6.0, "feedback": "F1"},
        {"question": "Q2", "answer": "A2", "score": 7.0, "feedback": "F2"},
        {"question": "Q3", "answer": "A3", "score": 8.0, "feedback": "F3"},
    ]

    report = json.loads(interview.report)
    assert report["question_scores"] == [
        {"question": "Q1", "score": 6.0, "feedback": "F1"},
        {"question": "Q2", "score": 7.0, "feedback": "F2"},
        {"question": "Q3", "score": 8.0, "feedback": "F3"},
    ]


def test_save_results_duplicate_answer_does_not_advance_again():
    interview = Interview(
        id=1,
        user_id=10,
        target_position="后端开发",
        status="in_progress",
        current_question_index=1,
        questions_data=[
            {"question": "Q1"},
            {"question": "Q2"},
        ],
    )
    existing_answer = InterviewMessage(
        interview_id=1,
        role="candidate",
        content="A1",
        question_index=0,
        score=Decimal("6.0"),
        feedback="F1",
    )
    db = _FakeDb(interview, [existing_answer])

    result = asyncio.run(save_results_node({
        "db": db,
        "interview_id": 1,
        "user_id": 10,
        "current_index": 0,
        "is_finished": False,
        "score": 6.0,
        "feedback": "new feedback",
        "questions": interview.questions_data,
        "answer": "A1",
        "parsed_resume": {},
        "target_position": "后端开发",
        "chat_history": [],
        "next_question": "Q2",
    }))

    assert db.commits == 0
    assert interview.current_question_index == 1
    assert db.added == []
    assert result["result"]["idempotent"] is True
    assert result["result"]["question_index"] == 0
    assert result["result"]["next_question"] == "Q2"
