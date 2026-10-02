"""
LangGraph 检查点（Checkpointer）工厂。

作用：以 thread_id 为单位持久化图的每一步状态，是「断点续传与连接」的底层机制。
- 当前默认使用内置 MemorySaver（进程内，零额外依赖），满足单进程内部恢复与幂等。
- 若后续需要跨进程 / 跨重启持久化，安装对应依赖后在此切换即可（仅改本函数）：
    - RedisSaver    -> pip install langgraph-checkpoint-redis
    - PostgresSaver -> pip install langgraph-checkpoint-postgres
  二者均复用项目既有的 Redis / PostgreSQL，无需改动业务代码。
"""

from langgraph.checkpoint.memory import MemorySaver

# 预留：未来接入 Redis/Postgres 检查点时在此实例化（注意需要对应依赖）。
# from langgraph.checkpoint.redis import RedisSaver
# from langgraph.checkpoint.postgres import PostgresSaver


def get_checkpointer() -> MemorySaver:
    """返回图编译所需的检查点实例。

    返回类型标注为 MemorySaver 以匹配当前可用依赖；
    接入 Redis/Postgres 时此处改为返回对应 Saver 即可，调用方无需变动。
    """
    # 单例：同一进程内复用，保证 thread_id 状态可被同进程后续请求读取。
    if not hasattr(get_checkpointer, "_instance"):
        get_checkpointer._instance = MemorySaver()
    return get_checkpointer._instance
