"""Celery worker 进程内的协程执行器。

背景（2026-10 线上简历解析连续失败排查）：
resume.parse / interview.generate_report / notification.create 等任务此前直接用
``asyncio.run()`` 执行协程 —— 每个任务新建一个事件循环并在结束时关闭。而
DB 引擎（app.db.base 全局 asyncpg 连接池）、AsyncOpenAI 客户端
（app.services.client.ai_service 模块级单例）、Redis 客户端
（app.services.common.redis 模块级单例）都是进程级单例，连接在首次使用时
绑定到「当时的」事件循环。上一个任务的循环一关，下一个任务在新循环里再拿到
这些旧连接就会抛 ``Event loop is closed`` / ``Future attached to a different
loop``，落到业务上就是简历解析偶发 failed（生产 celery-worker 日志
2026-10-12/17/21 反复出现）。

修复方式：worker 进程内复用同一个常驻事件循环执行所有协程，让单例连接池始终
绑定在同一个循环上，跨任务不再失效。prefork 池下每个子进程各自持有独立循环，
互不影响；线程池下用锁保证同一时刻只有一个任务在跑（与 prefork 的单任务语义
一致）。
"""

import asyncio
import threading
from typing import Any, Coroutine, Optional, TypeVar

T = TypeVar("T")

_loop: Optional[asyncio.AbstractEventLoop] = None
_lock = threading.Lock()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """在进程级常驻事件循环上执行协程（替代任务入口处的 ``asyncio.run``）。

    注意：不支持在协程内部再次调用本函数（嵌套会死锁/报 loop 已在运行）。
    """
    global _loop
    with _lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
        return _loop.run_until_complete(coro)


def shutdown() -> None:
    """关闭常驻事件循环（供 worker 退出时调用；不调用也会随进程回收）。"""
    global _loop
    with _lock:
        if _loop is not None and not _loop.is_closed():
            try:
                _loop.run_until_complete(_loop.shutdown_asyncgens())
            finally:
                _loop.close()
        _loop = None
