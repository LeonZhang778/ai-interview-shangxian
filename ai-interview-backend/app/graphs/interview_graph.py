"""
LangGraph 面试流程状态机

将 submit_answer / submit_answer_stream 的逻辑统一为一个图。
四个节点：load_context → evaluate → generate_next → save_results

流式模式通过 asyncio.Queue 实现：evaluate 节点内部的 LLM token
实时推入队列，外层 generator 读取队列并 yield SSE 事件。
"""

import asyncio
import json
import logging
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
# State 定义
# ---------------------------------------------------------------------------

class InterviewState(TypedDict):
    """面试流程状态，所有节点共享"""

    # 输入
    interview_id: int
    user_id: int
    answer: str
    chunk_queue: object  # asyncio.Queue | None，流式输出用

    # 上下文（由 load_context 填充）
    current_question: str
    parsed_resume: dict
    chat_history: list
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

def build_interview_graph() -> StateGraph:
    """构建面试流程图"""
    graph = StateGraph(InterviewState)

    graph.add_node("load_context", load_context_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("generate_next", generate_next_node)
    graph.add_node("save_results", save_results_node)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "evaluate")
    graph.add_edge("evaluate", "generate_next")
    graph.add_edge("generate_next", "save_results")
    graph.add_edge("save_results", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# 流式执行器（SSE 用）
# ---------------------------------------------------------------------------

async def interview_graph_stream(input_data: dict):
    """
    流式执行面试图，实时 yield LLM token + 最终结果。

    事件格式：
      {"type": "chunk", "content": "..."}     ← LLM token（逐字）
      {"type": "done", "score": 7.5, ...}     ← 最终结果
    """
    graph = build_interview_graph()
    queue = asyncio.Queue()

    # 把队列注入 state，evaluate 节点会把 token 推入队列
    input_data["chunk_queue"] = queue

    # 后台任务执行图，完成后往队列放终止信号
    graph_task = asyncio.create_task(graph.ainvoke(input_data))
    graph_task.add_done_callback(lambda _: queue.put_nowait(_SENTINEL))

    # 实时读取队列中的 token 并 yield
    while True:
        chunk = await queue.get()
        if chunk is _SENTINEL:
            break
        yield {"type": "chunk", "content": chunk}

    # 等图执行完成，取最终结果
    graph_result = await graph_task
    result = graph_result.get("result", {})
    yield {"type": "done", **result}
