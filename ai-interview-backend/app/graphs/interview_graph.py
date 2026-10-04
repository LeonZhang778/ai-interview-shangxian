"""
LangGraph 面试流程状态机

将 submit_answer / submit_answer_stream 的逻辑统一为一个图。
四个节点：load_context → evaluate → generate_next → save_results

流式模式通过 asyncio.Queue 实现：evaluate 节点内部的 LLM token
实时推入队列，外层 generator 读取队列并 yield SSE 事件。

本次增强（补齐 LangGraph 不足）：
- 可观测性：trace_node 包装四个节点，记录进入/完成/耗时/异常；条件路由打印分支走向。
- 会话记忆分离：聊天历史由 load_context 从 DB 加载（长期记忆外部化），State 仅承载本轮工作记忆。

注：曾挂载进程内 MemorySaver 作为 checkpointer，现已移除，原因见 build_interview_graph。
"""

import asyncio
import functools
import logging
import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.graphs.nodes.interview_nodes import (
    evaluate_node,
    generate_next_node,
    load_context_node,
    save_results_node,
)

logger = logging.getLogger(__name__)

_SENTINEL = object()  # 队列终止信号


# ---------------------------------------------------------------------------
# 可观测性：节点耗时 / 分支日志
# ---------------------------------------------------------------------------

def trace_node(name: str):
    """节点装饰器：记录进入、完成、耗时与异常，便于按节点埋点。

    说明：LangSmith / OpenTelemetry 接入为可选增强（需外部服务与密钥），
    此处用项目既有 logging 实现轻量、零依赖的可观测性。
    """

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(state):
            start = time.perf_counter()
            logger.info(f"[graph][node={name}] ▶ 进入")
            try:
                result = await fn(state)
                dur_ms = (time.perf_counter() - start) * 1000
                logger.info(f"[graph][node={name}] ✔ 完成 耗时={dur_ms:.1f}ms")
                return result
            except Exception as e:
                dur_ms = (time.perf_counter() - start) * 1000
                logger.error(f"[graph][node={name}] ✘ 异常 耗时={dur_ms:.1f}ms err={e}")
                raise

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# State 定义
# ---------------------------------------------------------------------------

class InterviewState(TypedDict):
    """面试流程状态，所有节点共享"""

    # 输入
    interview_id: int
    user_id: int
    answer: str
    db: object  # AsyncSession，数据库连接
    chunk_queue: object  # asyncio.Queue | None，流式输出用

    # 上下文（由 load_context 填充）
    current_question: str
    parsed_resume: dict
    chat_history: list
    history_summary: str | None  # 记忆压缩后的较早历史摘要
    questions: list
    current_index: int
    target_position: str
    resume_id: int | None
    experience_id: int | None

    # 评估结果（由 evaluate 填充）
    evaluation: dict
    score: float
    feedback: str
    skip_type: str | None

    # 后续（由 generate_next 填充）
    next_question: str | None
    is_finished: bool
    overall_score: float

    # 错误
    error: str | None

    # 输出（由 save_results 填充）
    result: dict


# ---------------------------------------------------------------------------
# 图构建
# ---------------------------------------------------------------------------

def _route_after_evaluate(state: dict) -> str:
    """评估后的路由：成功走 success，降级/失败走 fallback"""
    if state.get("error"):
        logger.warning("[graph] 路由分支=fallback（上游 error，启用容错降级）")
        return "fallback"
    logger.info("[graph] 路由分支=success")
    return "success"


def build_interview_graph():
    """构建面试流程图（带条件边路由 + 检查点）"""
    graph = StateGraph(InterviewState)

    # 用 trace_node 包装，注入节点级可观测性
    graph.add_node("load_context", trace_node("load_context")(load_context_node))
    graph.add_node("evaluate", trace_node("evaluate")(evaluate_node))
    graph.add_node("generate_next", trace_node("generate_next")(generate_next_node))
    graph.add_node("save_results", trace_node("save_results")(save_results_node))

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "success": "generate_next",
            "fallback": "generate_next",
        },
    )
    graph.add_edge("generate_next", "save_results")
    graph.add_edge("save_results", END)

    # 刻意不挂 checkpointer（原来是进程内 MemorySaver）。三个原因：
    #   1) 生产是 2 个 uvicorn worker，MemorySaver 是进程内的，thread_id 不跨进程共享，
    #      所谓「断点续传」名不副实 —— 同一题重试落到另一个 worker 就从头跑；
    #   2) 它没有 TTL / 容量上限，每个 iv:{interview_id}:{index} 的完整 state（含简历
    #      解析结果、聊天历史）会永久驻留内存 —— 在 1.6Gi 内存的机器上是持续增长；
    #   3) 换成 Redis/Postgres 持久化同样不成立：state 里带着 db(AsyncSession) 与
    #      chunk_queue(asyncio.Queue)，二者都无法序列化。
    # 幂等不受影响：它由 DB 层的 _get_duplicate_submission_result 独立保证，
    # submit_answer 与 submit_answer_stream 两条路径都在入口先查一次。
    # 因此调用方传的 configurable.thread_id 现在是惰性的（已验证：无 checkpointer 时无害）。
    return graph.compile()


# 模块级单例：submit 与 stream 共用同一编译图（检查点状态按 thread_id 隔离）
interview_graph = build_interview_graph()


# ---------------------------------------------------------------------------
# 流式执行器（SSE 用）
# ---------------------------------------------------------------------------

async def interview_graph_stream(input_data: dict, thread_id: str = "default"):
    """
    流式执行面试图，实时 yield LLM token + 最终结果。

    Args:
        input_data: 图输入状态
        thread_id:  断点续传/幂等用的会话标识（默认 iv:{interview_id}:{question_index}）

    事件格式：
      {"type": "chunk", "content": "..."}     ← LLM token（逐字）
      {"type": "done", "score": 7.5, ...}     ← 最终结果
    """
    queue = asyncio.Queue()

    # 把队列注入 state，evaluate 节点会把 token 推入队列
    input_data["chunk_queue"] = queue

    # 后台任务执行图，完成后往队列放终止信号
    graph_task = asyncio.create_task(
        interview_graph.ainvoke(input_data, config={"configurable": {"thread_id": thread_id}})
    )
    graph_task.add_done_callback(lambda _: queue.put_nowait(_SENTINEL))

    # 实时读取队列中的 token 并 yield
    while True:
        chunk = await queue.get()
        if chunk is _SENTINEL:
            break
        yield {"type": "chunk", "content": chunk}

    # 等图执行完成，取最终结果。
    # 关键兜底：图执行过程中任何异常（上游 LLM 断连/超时/节点报错）都不能让 SSE 静默中断，
    # 否则前端收不到 done 事件，会永久停留在“光标闪烁”的 think 态。
    # 此处把异常转换为显式 error 事件，保证流一定有终态。
    try:
        graph_result = await graph_task
    except Exception as e:
        logger.error(f"[graph] 图执行异常，转为 error 事件返回: {e}", exc_info=True)
        yield {"type": "error", "content": f"评估中断，请重试：{e}"}
        return

    result = graph_result.get("result", {}) or {}
    if result.get("error"):
        logger.error(f"[graph] 图返回错误结果: {result['error']}")
        yield {"type": "error", "content": result["error"]}
        return

    yield {"type": "done", **result}
