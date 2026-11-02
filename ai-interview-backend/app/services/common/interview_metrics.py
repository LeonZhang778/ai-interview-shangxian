"""面试链路轻量指标采集。

指标默认保存在当前 API/Worker 进程内，适合本地基准、测试和日志旁路观测。
它不参与业务成功与否，Redis、数据库或日志系统不可用时也不会改变主链路。
生产环境若需要跨 Worker 汇总，应继续把这些事件接入现有日志消费或监控系统。
"""

from __future__ import annotations

import threading
from collections import Counter, defaultdict
from math import ceil
from statistics import mean


class InterviewMetrics:
    """线程安全的计数器和有限耗时样本收集器。"""

    def __init__(self, max_samples: int = 1000) -> None:
        self._lock = threading.Lock()
        self._counters: Counter[str] = Counter()
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._max_samples = max_samples

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            samples = self._timings[name]
            if len(samples) >= self._max_samples:
                samples.pop(0)
            samples.append(float(value))

    def snapshot(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
            timings = {}
            for name, values in self._timings.items():
                if not values:
                    continue
                ordered = sorted(values)
                p95_index = min(len(ordered) - 1, max(0, ceil(len(ordered) * 0.95) - 1))
                timings[name] = {
                    "count": len(ordered),
                    "mean_ms": round(mean(ordered), 3),
                    "p95_ms": round(ordered[p95_index], 3),
                    "max_ms": round(ordered[-1], 3),
                }
            return {"counters": counters, "timings": timings}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timings.clear()


interview_metrics = InterviewMetrics()
