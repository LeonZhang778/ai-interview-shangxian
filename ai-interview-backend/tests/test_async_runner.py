"""回归测试：Celery 任务必须共享进程常驻事件循环。

线上 bug（2026-10 简历解析连续 failed）：任务入口逐个 asyncio.run() 开关循环，
DB 引擎 / AsyncOpenAI / Redis 这些进程级单例的连接在首次使用时绑定到当时的
循环；循环关掉后，下一个任务在新循环里复用旧连接就抛 "Event loop is closed"
/ "attached to a different loop"。

这里的测试用「第一次调用建连接、第二次调用继续用」的最小模型复现该时序，
并验证三个出过问题的任务入口（resume.parse / interview.generate_report /
notification.create）都跑在同一个循环上。
"""

import asyncio

from app.core import async_runner
from app.schedule.jobs import notification_tasks, report_tasks, resume_tasks


def test_run_async_reuses_same_loop_across_calls():
    seen = []

    async def probe():
        seen.append(asyncio.get_running_loop())
        return "ok"

    assert async_runner.run_async(probe()) == "ok"
    assert async_runner.run_async(probe()) == "ok"
    assert len(seen) == 2
    assert seen[0] is seen[1]
    assert not seen[0].is_closed()


def test_run_async_keeps_loop_bound_state_usable_across_calls():
    # 复现线上故障时序：连接（此处以 Future 代替）建在第一次调用的循环上，
    # 第二次调用继续复用。逐任务 asyncio.run 时这里会抛
    # "Future attached to a different loop"，正是 resume.parse 的失败方式。
    holder = {}

    async def create_conn():
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        fut.set_result("pong")
        holder["loop"] = loop
        holder["fut"] = fut

    async def use_conn():
        assert asyncio.get_running_loop() is holder["loop"]
        return await holder["fut"]

    async_runner.run_async(create_conn())
    assert async_runner.run_async(use_conn()) == "pong"


def test_broken_task_entrypoints_share_one_loop(monkeypatch):
    seen = []

    async def fake_parse(resume_id, user_id):
        seen.append(asyncio.get_running_loop())
        return {"resume_id": resume_id, "status": "completed"}

    async def fake_report(interview_id):
        seen.append(asyncio.get_running_loop())
        return {"interview_id": interview_id, "status": "generated"}

    async def fake_notify(user_id, **kwargs):
        seen.append(asyncio.get_running_loop())
        return {"user_id": user_id, "status": "created"}

    monkeypatch.setattr(resume_tasks, "_parse_resume", fake_parse)
    monkeypatch.setattr(report_tasks, "_generate_report", fake_report)
    monkeypatch.setattr(notification_tasks, "_create_notification", fake_notify)

    r1 = resume_tasks.parse_resume_task(1, 2)
    r2 = report_tasks.generate_interview_report_task(3)
    r3 = notification_tasks.create_notification_task(user_id=4, title="t")

    assert r1 == {"resume_id": 1, "status": "completed"}
    assert r2 == {"interview_id": 3, "status": "generated"}
    assert r3 == {"user_id": 4, "status": "created"}
    assert len(seen) == 3
    assert seen[0] is seen[1] is seen[2]


def test_run_async_survives_coroutine_failure():
    async def boom():
        raise RuntimeError("boom")

    async def fine():
        return "recovered"

    try:
        async_runner.run_async(boom())
    except RuntimeError:
        pass
    else:
        raise AssertionError("异常应当向上传递")

    # 失败后循环仍可继续服务后续任务（worker 不应因单次异常报废）
    assert async_runner.run_async(fine()) == "recovered"
