import asyncio
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

from sqlalchemy.exc import IntegrityError, MultipleResultsFound
from sqlalchemy.sql.elements import BindParameter

from app.graphs.nodes.interview_nodes import evaluate_node, save_results_node
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.services.client.ai_service import AIService
from app.services.client.interview_report_service import interview_report_service


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


def _stub_notification(monkeypatch, calls=None):
    """隔离「面试完成通知」这个 commit 后的旁路。

    它入队失败时会**降级为同步创建并额外 commit 一次**，因此不禁用的话，
    断言 db.commits 就变成在测「这台机器有没有 Redis」：本地有 Redis 走 Celery
    （1 次提交）会通过，CI 没有 Redis 走降级路径（2 次提交）就失败。
    CI 与本地都要能跑，所以这是必须的隔离，不是可选的优化。
    """
    from app.services.client import notification_service as notification_module

    async def _noop(*args, **kwargs):
        if calls is not None:
            calls.append("notification")

    monkeypatch.setattr(notification_module.notification_service, "enqueue_notification", _noop)


def _stub_post_commit_side_effects(monkeypatch):
    """把 save_results_node 提交后的两个副作用替换成空操作。

    注：学习笔记草稿与薄弱点统计已随报告一起搬到后台任务（见
    interview_report_service），因此不再需要在这里 stub；报告投递本身必须 stub，
    否则会真的去连 broker。
    """
    from app.services.client import interview_report_service as report_module

    async def _noop(*args, **kwargs):
        return None

    _stub_notification(monkeypatch)
    monkeypatch.setattr(report_module.interview_report_service, "dispatch", _noop)


def test_save_results_finishes_without_generating_report_inline(monkeypatch):
    """最后一题只落「completed + report_status=pending」，报告不在请求内生成。

    回归：报告生成原先与评分写入挤在同一个事务里，于是 SSE 的 done 事件必须等
    LLM 写完报告（几十秒静默）才能发出；报告生成失败还会连累整个提交。
    现在请求内只标记就绪状态并把生成投递出去。
    """
    dispatched = []

    async def fake_dispatch(db, interview_id):
        dispatched.append(interview_id)
        return True

    async def forbidden_generate_report(*args, **kwargs):
        raise AssertionError("报告不应在请求路径内生成（应交给后台任务）")

    _stub_notification(monkeypatch)
    monkeypatch.setattr(interview_report_service, "dispatch", fake_dispatch)
    monkeypatch.setattr(AIService, "generate_report", forbidden_generate_report)

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

    # 核心写入必须只提交一次：回答、面试状态、就绪标记三者在同一事务里落库，
    # 前端看到 completed 时必定同时看到 pending，不存在「已完成但没有就绪标记」的中间态。
    assert db.commits == 1
    assert interview.status == "completed"
    assert interview.report_status == "pending"
    assert interview.report is None  # 报告由后台任务写
    assert float(interview.overall_score) == 7.0
    assert result["result"]["overall_score"] == 7.0
    assert result["result"]["is_finished"] is True
    assert dispatched == [1]


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


def _stub_report_generation(monkeypatch):
    """替换真实的报告生成调用（防御性护栏）。

    报告生成已搬到后台任务，save_results_node 本身不再调用它 —— 本用例通过
    _stub_post_commit_side_effects 把「报告投递」也 stub 了，所以正常情况下压根走不到这里。
    保留它是为了防止将来有人改坏投递路径后，用例意外发起真实 LLM 请求：
    测试环境连不上，框架会重试并把整条用例拖到 20 秒以上，让纯逻辑用例变成依赖网络的慢用例。
    """
    async def _fake_generate_report(parsed_resume, target_position, questions_and_scores):
        return {"summary": "ok", "strengths": [], "weaknesses": [], "suggestions": []}

    monkeypatch.setattr(AIService, "generate_report", _fake_generate_report)


class _ConflictDb(_FakeDb):
    """模拟「并发重复提交被唯一约束拦下」。

    真实时序：两个请求先各自跑完幂等守卫（都没查到记录），其中一个先提交成功，
    另一个提交时撞上 uq_interview_message_question 约束。因此 fake 需要在**冲突发生时**
    才让抢先生成的那条记录变得可见 —— 提前可见会让守卫提前返回，根本走不到 commit。
    """

    def __init__(self, interview, existing_rows, late_row=None):
        super().__init__(interview, existing_rows)
        self._late_row = late_row
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1
        if self.commits == 1:
            if self._late_row is not None:
                self.scored_messages.append(self._late_row)
            raise IntegrityError(
                "INSERT INTO interview_messages ...", {},
                Exception("duplicate key value violates unique constraint"),
            )

    async def rollback(self):
        self.rollbacks += 1
        # 真实会话回滚会丢弃未提交的新增对象，这里同样清掉，
        # 避免「插入失败的那条」留在结果里干扰后续查询
        self.added.clear()


def _finished_state(db, interview):
    return {
        "db": db,
        "interview_id": interview.id,
        "user_id": interview.user_id,
        "current_index": 2,
        "is_finished": True,
        "score": 8.0,
        "feedback": "F3",
        "questions": interview.questions_data,
        "answer": "A3",
        "parsed_resume": {},
        "target_position": "后端开发",
        "chat_history": [],
        "next_question": None,
    }


def _conflict_interview_and_rows():
    interview = Interview(
        id=1,
        user_id=10,
        target_position="后端开发",
        status="in_progress",
        current_question_index=2,
        questions_data=[{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}],
    )
    prior = [
        InterviewMessage(
            interview_id=1, role="candidate", content="A1",
            question_index=0, score=Decimal("6.0"), feedback="F1",
        ),
        InterviewMessage(
            interview_id=1, role="candidate", content="A2",
            question_index=1, score=Decimal("7.0"), feedback="F2",
        ),
    ]
    late = InterviewMessage(
        interview_id=1, role="candidate", content="A3",
        question_index=2, score=Decimal("9.0"), feedback="对方先写入的评语",
    )
    return interview, prior, late


def test_save_results_unique_violation_returns_idempotent_result(monkeypatch):
    """唯一约束拦下并发重复提交时，必须回滚并按幂等返回，而不是把 500 抛给前端。"""
    _stub_post_commit_side_effects(monkeypatch)
    _stub_report_generation(monkeypatch)
    interview, prior, late = _conflict_interview_and_rows()
    db = _ConflictDb(interview, prior, late_row=late)

    result = asyncio.run(save_results_node(_finished_state(db, interview)))

    assert db.rollbacks == 1
    assert result["result"]["idempotent"] is True
    assert result["result"]["score"] == 9.0
    assert result["result"]["feedback"] == "对方先写入的评语"
    assert result["result"]["question_index"] == 2
    # 本次请求算出的综合分（22/3）不得外泄：它对应的写入已经被回滚了
    assert result["overall_score"] == 0.0


def test_save_results_unique_violation_without_existing_row_reraises(monkeypatch):
    """冲突后却查不到记录（例如约束来自别处）时，必须把异常抛出去，不能伪造成功。"""
    _stub_post_commit_side_effects(monkeypatch)
    _stub_report_generation(monkeypatch)
    interview, prior, _ = _conflict_interview_and_rows()
    db = _ConflictDb(interview, prior, late_row=None)

    try:
        asyncio.run(save_results_node(_finished_state(db, interview)))
    except IntegrityError:
        pass
    else:
        raise AssertionError("期望抛出 IntegrityError，实际静默返回")
