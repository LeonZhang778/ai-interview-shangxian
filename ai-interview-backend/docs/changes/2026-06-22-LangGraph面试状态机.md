# LangGraph 面试状态机重构

> 日期：2026-06-22
> 类型：核心架构重构
> 状态：已完成

---

## 1. 功能说明

将 `interview_service.py` 中 `submit_answer` 和 `submit_answer_stream` 的重复逻辑重构为 LangGraph 状态机。

**解决的问题：**
- 两个方法有 ~200 行重复代码（加载上下文、评估、保存结果、生成报告）
- 流式路径和同步路径各自维护一套逻辑，改一处容易漏另一处
- 错误处理分散在各处，不统一

**重构后的架构：**
- 统一的四节点图：`load_context → evaluate → generate_next → save_results`
- 同步路径（`submit_answer`）：`graph.ainvoke()` 一次性返回
- 流式路径（`submit_answer_stream`）：通过 `asyncio.Queue` 桥接，LLM token 实时推送到前端
- 前端 SSE 格式不变（`chunk` + `done`），用户体验无变化

---

## 2. 涉及路由

本次改动不涉及 API 路由变更。现有接口行为不变：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/interviews/{id}/answer` | 同步提交回答（内部走 LangGraph） |
| POST | `/api/v1/interviews/{id}/answer/stream` | 流式提交回答（LangGraph + Queue） |

---

## 3. 核心实现逻辑

### 3.1 图结构

```
START → load_context → evaluate → generate_next → save_results → END
```

每个节点返回部分状态更新，LangGraph 自动合并到全局状态。

### 3.2 流式输出机制

```
submit_answer_stream (service)
  └── interview_graph_stream()
       ├── 创建 asyncio.Queue，注入 state["chunk_queue"]
       ├── asyncio.create_task(graph.ainvoke())  ← 后台执行图
       ├── graph_task.add_done_callback → queue.put(_SENTINEL)
       │
       ├── evaluate_node 内部：
       │    └── AIService.evaluate_answer_stream()
       │         └── LLM token → queue.put(chunk)  ← 实时推送
       │
       └── 主协程：
            └── queue.get() → yield {"type": "chunk"}  ← 实时读取
                └── 收到 _SENTINEL → yield {"type": "done"}
```

关键点：`asyncio.Queue` 是无界的（`maxsize=0`），`put()` 永不阻塞，避免死锁。

### 3.3 evaluate_node 三级容错

```
Level 0: AIService.evaluate_answer_stream() (流式 LLM)
   ↓ 失败
Level 2: AIService.pre_score() (关键词预判断)
   ↓ 不适用
Level 3: 兜底 5.0 分
```

### 3.4 错误短路

如果 `load_context_node` 返回 `error`，后续节点检查 `state["error"]` 并短路跳过，避免在无效状态上执行。

---

## 4. 数据库设计

本次改动不涉及数据库表结构变化。

---

## 5. 涉及文件

```
ai-interview-backend/
├── app/
│   ├── graphs/                              # 新增：LangGraph 工作流
│   │   ├── __init__.py                      # 新增：包导出
│   │   ├── interview_graph.py               # 新增：StateGraph 定义 + 流式执行器
│   │   └── nodes/
│   │       ├── __init__.py                  # 新增：包初始化
│   │       └── interview_nodes.py           # 新增：4 个图节点实现
│   └── services/
│       └── client/
│           └── interview_service.py         # 修改：submit_answer/submit_answer_stream 改为调用图
├── requirements.txt                         # 修改：新增 langgraph、langchain-core
└── docs/
    └── changes/
        └── 2026-06-22-LangGraph面试状态机.md  # 新增：本文档
```

---

## 6. 测试情况

### 静态检查

- [x] `app/graphs/__init__.py` 语法检查通过
- [x] `app/graphs/interview_graph.py` 语法检查通过
- [x] `app/graphs/nodes/__init__.py` 语法检查通过
- [x] `app/graphs/nodes/interview_nodes.py` 语法检查通过
- [x] `app/services/client/interview_service.py` 语法检查通过
- [x] 前端文件 `interview.js`、`Interview.vue` 无改动（git diff 为空）

### 依赖检查

- [x] `langgraph==1.2.4` 已安装
- [x] `langchain-core` 已安装（langgraph 依赖）

### 未实测

由于本地环境无法连接服务器数据库，无法实际运行面试流程验证。建议部署后验证：

```bash
# 1. 健康检查
curl http://8.166.120.119/api/v1/config/health

# 2. 同步接口测试
curl -X POST http://8.166.120.119/api/v1/interviews/1/answer \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"answer": "测试回答"}'

# 3. 流式接口测试（观察是否逐字输出）
curl -N -X POST http://8.166.120.119/api/v1/interviews/1/answer/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"answer": "测试回答"}'
```
