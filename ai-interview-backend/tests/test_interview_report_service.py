"""面试报告后台生成服务的用例。

覆盖三件容易出错、且直接影响用户体验的事：
    1) 报告的数据组装（题目与回答必须按题号对齐，未作答要占位）；
    2) 幂等（重复投递不得重复调用 LLM、不得覆盖已生成的报告）；
    3) 调度（入队失败要同步降级、节流命中不得重复入队）。
"""

import asyncio
import json
from decimal import Decimal

from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.services.client import interview_report_service as report_module
from app.services.client.ai_service import AIService
from app.services.client.interview_report_service import interview_report_service


class _ScalarResult:
    def __init__(self, items):
        self._items = list(items)

    def scalars(self):
        return self

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class _ClaimResult:
    """模拟 UPDATE ... RETURNING 的结果：命中返回一行，未命中返回空。"""

    def __init__(self, claimed: bool):
        self._claimed = claimed

    def first(self):
        return (1,) if self._claimed else None


class _FakeDb:
    def __init__(self, interview, messages=None, claim_succeeds=True):
        self.interview = interview
        self.messages = list(messages or [])
        self.claim_succeeds = claim_succeeds
        self.commits = 0
        self.update_statements = []

    async def get(self, model, item_id):
        return self.interview

    async def execute(self, statement):
        if getattr(statement, "is_update", False):
            self.update_statements.append(statement)
            return _ClaimResult(self.claim_succeeds)
        return _ScalarResult(self.messages)

    async def commit(self):
        self.commits += 1


def _stub_side_effects(monkeypatch):
    """报告生成后的两个回流副作用：这里不做断言，只避免它们真的读写数据库。"""
    from app.services.client import learning_note_service as note_module
    from app.services.client import weakness_service as weakness_module

    calls = []

    async def _note(*args, **kwargs):
        calls.append("note")

    async def _weakness(*args, **kwargs):
        calls.append("weakness")

    monkeypatch.setattr(note_module.learning_note_service, "generate_from_interview", _note)
    monkeypatch.setattr(weakness_module.weakness_service, "record_from_interview", _weakness)
    return calls


def _completed_interview(**overrides):
    defaults = dict(
        id=7,
        user_id=42,
        target_position="后端开发",
        status="completed",
        report_status="pending",
        report=None,
        resume_id=None,
        experience_id=None,
        questions_data=[{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}],
    )
    defaults.update(overrides)
    return Interview(**defaults)


def _messages():
    return [
        InterviewMessage(
            interview_id=7, role="interviewer", content="Q1", question_index=0
        ),
        InterviewMessage(
            interview_id=7, role="candidate", content="A1",
            question_index=0, score=Decimal("6.0"), feedback="F1",
        ),
        InterviewMessage(
            interview_id=7, role="candidate", content="A2",
            question_index=1, score=Decimal("7.0"), feedback="F2",
        ),
    ]


def test_build_qa_data_aligns_answers_by_question_index():
    """按题号对齐，未作答的题保留占位（而不是被丢掉，导致报告缺题）。"""
    interview = _completed_interview()
    db = _FakeDb(interview, _messages())

    qa_data = asyncio.run(
        interview_report_service.build_qa_data(db, interview)
    )

    assert qa_data == [
        {"question": "Q1", "answer": "A1", "score": 6.0, "feedback": "F1"},
        {"question": "Q2", "answer": "A2", "score": 7.0, "feedback": "F2"},
        {"question": "Q3", "answer": "未回答", "score": 0, "feedback": ""},
    ]


def test_generate_for_interview_persists_report_and_question_scores(monkeypatch):
    calls = _stub_side_effects(monkeypatch)
    captured = {}

    async def fake_generate_report(parsed_resume, target_position, questions_and_scores):
        captured["qa"] = questions_and_scores
        captured["position"] = target_position
        return {"summary": "ok", "strengths": [], "weaknesses": [], "suggestions": []}

    monkeypatch.setattr(AIService, "generate_report", fake_generate_report)

    interview = _completed_interview()
    db = _FakeDb(interview, _messages())

    result = asyncio.run(
        interview_report_service.generate_for_interview(db, interview.id)
    )

    assert result["status"] == "generated"
    assert captured["position"] == "后端开发"
    assert captured["qa"] == [
        {"question": "Q1", "answer": "A1", "score": 6.0, "feedback": "F1"},
        {"question": "Q2", "answer": "A2", "score": 7.0, "feedback": "F2"},
        {"question": "Q3", "answer": "未回答", "score": 0, "feedback": ""},
    ]
    assert interview.report_status == "ready"
    report = json.loads(interview.report)
    assert report["question_scores"] == [
        {"question": "Q1", "score": 6.0, "feedback": "F1"},
        {"question": "Q2", "score": 7.0, "feedback": "F2"},
        {"question": "Q3", "score": 0, "feedback": ""},
    ]
    # 报告落库后才跑回流副作用
    assert calls == ["note", "weakness"]


def test_generate_for_interview_is_idempotent_when_report_ready(monkeypatch):
    """重复投递（Celery 重试 / 用户手动重试 / 入队降级）不得重复烧 LLM。"""
    called = False

    async def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(AIService, "generate_report", forbidden)

    interview = _completed_interview(report_status="ready", report='{"summary": "已有"}')
    db = _FakeDb(interview, _messages())

    result = asyncio.run(
        interview_report_service.generate_for_interview(db, interview.id)
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "already_ready"
    assert called is False
    assert db.commits == 0


def test_generate_for_interview_skips_unfinished_interview(monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("面试未完成时不应生成报告")

    monkeypatch.setattr(AIService, "generate_report", forbidden)

    interview = _completed_interview(status="in_progress")
    db = _FakeDb(interview, _messages())

    result = asyncio.run(
        interview_report_service.generate_for_interview(db, interview.id)
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "not_completed"


def test_dispatch_falls_back_to_inline_generation_when_enqueue_fails(monkeypatch):
    """broker 不可用时必须同步生成：用户不能因为 Redis 抖动就拿不到报告。"""
    monkeypatch.setattr(
        report_module.InterviewReportService, "enqueue", staticmethod(lambda interview_id: False)
    )

    generated = []

    async def fake_generate(db, interview_id):
        generated.append(interview_id)
        return {"status": "generated"}

    monkeypatch.setattr(
        report_module.InterviewReportService, "generate_for_interview", staticmethod(fake_generate)
    )

    ok = asyncio.run(interview_report_service.dispatch(object(), 7))

    assert ok is True
    assert generated == [7]


def test_dispatch_does_not_generate_inline_when_enqueue_succeeds(monkeypatch):
    monkeypatch.setattr(
        report_module.InterviewReportService, "enqueue", staticmethod(lambda interview_id: True)
    )

    async def forbidden(*args, **kwargs):
        raise AssertionError("入队成功时不应同步生成（会把请求又拖慢几十秒）")

    monkeypatch.setattr(
        report_module.InterviewReportService, "generate_for_interview", staticmethod(forbidden)
    )

    ok = asyncio.run(interview_report_service.dispatch(object(), 7))

    assert ok is True


def test_request_regeneration_enqueues_when_claim_succeeds(monkeypatch):
    enqueued = []
    monkeypatch.setattr(
        report_module.InterviewReportService,
        "enqueue",
        staticmethod(lambda interview_id: enqueued.append(interview_id) or True),
    )

    interview = _completed_interview(report_status="failed")
    db = _FakeDb(interview, _messages(), claim_succeeds=True)

    status = asyncio.run(
        interview_report_service.request_regeneration(db, interview)
    )

    assert status == "pending"
    assert enqueued == [7]
    assert db.commits == 1


def test_request_regeneration_does_not_enqueue_when_throttled(monkeypatch):
    """节流命中（刚被请求过 / 已有请求抢先）时不得重复投递。"""
    enqueued = []
    monkeypatch.setattr(
        report_module.InterviewReportService,
        "enqueue",
        staticmethod(lambda interview_id: enqueued.append(interview_id) or True),
    )

    interview = _completed_interview(report_status="pending")
    db = _FakeDb(interview, _messages(), claim_succeeds=False)

    status = asyncio.run(
        interview_report_service.request_regeneration(db, interview)
    )

    assert status == "pending"
    assert enqueued == []


def test_module_exposes_constants_used_by_callers():
    """调用方（interview_service）依赖这两个常量，避免各自硬编码魔法数字。"""
    assert report_module.STATUS_READY == "ready"
    assert report_module.STATUS_PENDING == "pending"
    assert report_module.STATUS_FAILED == "failed"
    assert interview_report_service.MANUAL_MIN_INTERVAL_SECONDS < report_module.STALE_SECONDS
