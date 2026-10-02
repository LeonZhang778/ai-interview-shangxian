# AI-Interview（智面）项目架构分析

> 文档目的：基于当前代码库（截至 2026-10 版本）梳理业务场景、功能模块与项目结构，并重点分析 **RAG / LangGraph 编排 / 文档解析 / 性能与应对** 四大技术模块。
> 标注说明：为便于阅读，文中对**现状**（代码中已实现）与**规划/建议**（设计目标或待补齐项）做了区分；凡属"补全的关键名词"均以「▍补」标记。

---

## 1. 业务场景说明

### 1.1 核心痛点：大学生面试成本高
- **真实面试机会稀缺**：校招/实习岗位竞争激烈，学生能拿到的真实面试轮次有限，缺少"练手"环境。
- **反馈闭环缺失**：真实面试后往往只有"过/不过"，缺乏按知识点拆解的评分、评语与改进建议。
- **个性化不足**：通用题库与求职者自身简历、目标岗位脱节，练非所考。
- **辅导资源贵且不可规模化**：1 对 1 模拟面试人力成本高，难以覆盖一个班级/院系全体学生。

### 1.2 目标用户与初始规模
- **首批受众**：面向 **20–30 名同学**（如一个就业指导班、社团或院系试点），由管理员/教师通过"等待名单（waitlist）"限额放量。
- **使用形态**：学生上传简历 → 系统解析 → 生成与简历/目标岗位匹配的题目 → 进行多轮 AI 模拟面试 → 实时评分与逐题反馈 → 产出综合报告 → 自动回流为学习笔记、薄弱点、闪卡。

### 1.3 规模演进预期
- **试点期（当前）**：20–30 并发面试，每场约 8–12 题，全程约 200–300 次 LLM 调用；单机 `FastAPI + PostgreSQL + Redis + Celery` 即可承载。
- **扩展期（后续）**：从单一班级 → 全校 → 多校 → 公开发布（SaaS）。诉求是**在不重写主流程的前提下横向扩展**，尤其是"面经/知识库检索""向量召回""并发面试"三块。

### 1.4 由此衍生的技术诉求
| 诉求 | 对应设计 |
|------|----------|
| 低成本、可灰度 | 等待名单限额 + 预判断跳过低质量回答省 token + Redis 缓存 |
| 高并发可控 | 全异步栈（FastAPI + asyncpg）+ Celery 削峰 + 限流 |
| 可扩展（扩规模） | 向量库 Milvus 水平扩展、无状态 API、检查点持久化 |
| 体验流畅 | SSE 流式评分、加载/空/错误/成功四态 |

---

## 2. 功能介绍（一句话技术亮点）

### 2.1 用户端（ai-interview-frontend）
| 功能 | 一句话技术亮点 |
|------|----------------|
| 简历上传与智能解析 | `pdfplumber` 抽取文本 + LLM 结构化（简历字段 JSON 化）并带 Redis 缓存 |
| AI 模拟面试（核心） | LangGraph 状态机编排四节点 + `asyncio.Queue` 驱动 SSE 逐字流式评分 |
| 综合评估报告 | 加权平均分 + 优劣势/建议，由 LLM 基于逐题 QA 生成 |
| 面经库与同岗刷题 | 基于面经内容 `generate_questions_from_experience` 生成同公司同岗题目 |
| 学习笔记 / 笔记本 | 笔记本层级组织 + 全文搜索，面试报告可一键回流为复盘笔记 |
| 闪卡间隔重复 | Spaced Repetition 算法驱动错题重温 |
| 薄弱点仪表盘 | 从面试报告自动抽取薄弱点并聚合统计 |
| 错题本 | 与面试评分联动，沉淀为可复习条目 |
| 面试分享 | 生成 `share_token` 公开只读报告链接，无需登录 |
| 通知中心 | 面试完成等事件经 `notification_service` 推送 |
| 等待名单 | 灰度限额入场，管理员放量 |
| 公告 / 反馈 / Demo | 内容运营与产品引导闭环 |
| 媒体工具箱 | FFmpeg 驱动的转码/压缩/裁剪/水印/合并/提取音频/GIF 等（Celery 异步） |
| 图片工坊（ImageStudio） | 图像类轻处理工具 |
| 活跃度/PV 统计 | 前端埋点 `tracker` + 后端 `page_view` 聚合 |

### 2.2 管理端（ai-interview-admin）
| 功能 | 一句话技术亮点 |
|------|----------------|
| 用户 / 管理员管理 | 角色分离，复用后端 `get_current_user` 认证 |
| 面经管理 | 含图文编辑、封面与内容持久化 |
| 公告 / 反馈 / 审核日志 | 操作可追溯（`audit_log`） |
| 系统设置 | `setting_service` 统一读取，更新即失效 Redis 缓存 |
| 数据分析看板 | ECharts 可视化面试/用户/活跃度指标 |
| 面试记录查看 | 管理端可查看/删除面试及其消息 |

### 2.3 平台能力（跨端）
- **统一响应与鉴权**：`ApiResponse.success/failed/paginate` + `APIException` 体系；Client/Backoffice 共用 Service 层。
- **异步任务**：Celery + Redis 处理简历解析、报告、媒体转码。
- **邮件/通知**：SMTP / Brevo 双通道，等待名单通知模板化。

---

## 3. 项目结构树

```
ai-interview/
├── ai-interview-backend/                # 后端：FastAPI 0.115 + SQLAlchemy 2.0(async) + PostgreSQL 16
│   ├── app/
│   │   ├── api/                         # 接口层（仅做参数接收/依赖注入/响应封装）
│   │   │   ├── client/v1/               # 用户端接口：auth, resume, interview, experience,
│   │   │   │                            #   feedback, flashcard, learning_note, notebook,
│   │   │   │                            #   notification, waiting_list, image, media, tracking,
│   │   │   │                            #   config, demo, announcement, shared, weakness
│   │   │   ├── backoffice/v1/           # 管理端接口：admin, analytics, announcement, audit_log,
│   │   │   │                            #   auth, aws, experience, feedback, interviews,
│   │   │   │                            #   media_tasks, setting, users, waiting_list
│   │   │   ├── rate_limit.py            # 限流（防 API 配额打满/429）
│   │   │   └── docs_export.py           # 文档导出
│   │   ├── core/                        # 配置/安全/ celery / 日志
│   │   │   ├── config.py                # 环境变量统一读取
│   │   │   ├── security.py              # JWT/密码哈希
│   │   │   ├── celery_app.py            # Celery 实例
│   │   │   └── log_config.py            # 日志格式
│   │   ├── db/                          # ORM 层：base, models, session（async）
│   │   ├── models/                      # 19+ 张表：user, resume, interview, interview_message,
│   │   │                               #   experience, feedback, flashcard, learning_note,
│   │   │                               #   notebook, note_interaction, notification, announcement,
│   │   │                               #   admin, audit_log, waiting_list, weakness_stat,
│   │   │                               #   media_tool, image_task, token, page_view, setting
│   │   ├── graphs/                      # ▍LangGraph 编排层（见 §4.2）
│   │   │   ├── interview_graph.py       # StateGraph 构建 + 流式执行器（SSE）
│   │   │   └── nodes/interview_nodes.py # 四个节点：load_context/evaluate/generate_next/save_results
│   │   ├── services/                    # 业务层（三层架构核心）
│   │   │   ├── client/                  # ai_service(核心LLM), interview_service, resume_service,
│   │   │   │                            #   experience_service, learning_note_service,
│   │   │   │                            #   flashcard_service, weakness_service,
│   │   │   │                            #   notification_service, notebook_service,
│   │   │   │                            #   note_recommend_service, image_service,
│   │   │   │                            #   document_export_service, waiting_list
│   │   │   ├── common/                  # redis(缓存/限流), setting_service, email(模板/SMTP/Brevo), thread_pool
│   │   │   └── media/                   # repository, probe(ffprobe), format_config, observability
│   │   ├── schemas/                     # Pydantic 校验
│   │   ├── prompts/                     # 提示词：interview.py, learning_note.py
│   │   ├── schedule/                    # Celery 定时/异步任务（media_tasks 等）
│   │   ├── exceptions/                  # 业务异常（APIException 体系）
│   │   ├── common/                      # audit 审计, language, log_consumer, release
│   │   ├── route/                       # router_registry 路由注册中心（RouteConfig）
│   │   ├── configs/                     # Swagger / docs 配置
│   │   └── utils/                       # safe_parse_json 等工具
│   ├── migrations/                      # Alembic 迁移（含 guest 字段、媒体工具箱等）
│   ├── scripts/                         # seed_settings.py, deploy.sh
│   ├── tests/                           # pytest 测试
│   └── requirements.txt                 # langgraph, langchain-core, openai, pdfplumber, ...
│
├── ai-interview-frontend/               # 用户端：Vue3 + Vite5 + Pinia + Vue Router
│   └── src/
│       ├── views/                       # 39 个页面（面试/简历/报告/面经/笔记/闪卡/错题/媒体/...)
│       ├── components/                  # 公告条、主题切换、媒体子组件等
│       ├── stores/                      # auth.js, media.js（Pinia）
│       ├── composables/                 # useTheme
│       ├── router/                      # 路由
│       ├── api/                         # axios 封装
│       └── utils/                       # tracker 埋点、experienceContent 等
│
├── ai-interview-admin/                  # 管理端：Vue3 + Vite + Pinia + Vue Router
│   └── src/views/                       # 12 个管理页面（用户/面经/公告/审核/设置/分析/面试...）
│
├── docs/
│   ├── spec/media-tools/                # 媒体工具箱 12 篇规格（PRD/数据模型/API/状态机/...)
│   └── 开发文档/                         # 学习笔记模块等设计文档
│
├── scripts/codepus-agent/               # 面经内容生成 Agent（数据生产，非在线 RAG）
├── AGENTS.md                            # 项目级 Codex 记忆与开发铁律
└── 部署/交接文档 .md                     # 部署流程、交接日志、BugFix 规范
```

---

## 4. 重点模块分析

### 4.1 RAG（检索增强生成）

> **现状对照**：当前生产路径中，"面试上下文"采用 **DB/LLM 直注式**——简历解析结果、面经正文直接拼入 prompt（`AIService.generate_questions / evaluate_answer`），并未走向量检索。Milvus 当前为**知识库/面经检索的规划向量层**（用于后续扩规模时做语义召回，见 §4.4）。下方按"应落地的 RAG 架构"补全关键名词，作为设计与演进基线。

#### 4.1.1 整体链路
```
Query ──► [Query 拓展] ──► [混合索引检索] ──► [候选召回] ──► [Rerank 重排] ──► [Top-K 上下文] ──► [LLM 生成] ──► [两类评估]
```

#### 4.1.2 混合索引（Hybrid Index）
- **稠密向量（Dense）+ 稀疏向量（Sparse/BM25）混合检索**：Milvus 原生支持 dense + sparse 双向量字段，兼顾语义召回与关键词精确匹配。
- **索引类型**：`HNSW`（近邻，低延迟）、`IVF_FLAT/PQ`（可量化压缩，省内存）；大规模下面向十亿级向量的分布式分片。
- **▍补 元数据过滤（Metadata Filtering）**：按 `user_id / 岗位 / 学校 / 标签` 做预过滤，降低无关召回。
- **▍补 分块策略（Chunking）**：语义分块（Semantic Chunking）/ 递归字符分块 / 按标题层级切分 / 滑动窗口；避免"切碎语义"。
- **▍补 Embedding 模型选型**：多语言场景优先 `bge-m3 / multilingual-e5`，支持 dense+sparse+ColBERT 三路。
- **▍补 Late Interaction（ColBERT）**：先粗排再逐 token 交互精排，兼顾效果与成本。

#### 4.1.3 Query 多角度拓展（Query Expansion）
- **Multi-Query / RAG-Fusion**：一个意图生成多个改写 query，融合召回提升覆盖。
- **▍补 Hypothetical Document Embeddings（HyDE）**：先让 LLM 假设"理想答案文档"，用其向量去检索，缓解词汇鸿沟。
- **▍补 Step-back Prompting（退一步提问）**：先问更抽象的上位问题，拓宽召回。
- **▍补 Sub-query / Question Decomposition（问题分解）**：复杂问题拆为子问题分别检索再聚合。
- **▍补 Query 路由 / 分类（Query Routing）**：判断走向量库、走关键词、走工具（计算器/代码）还是直答。

#### 4.1.4 Query → 候选答案（Retrieval → Candidates）
- 检索器（Retriever）返回候选块集合；结合元数据过滤与相似度阈值初筛。
- **▍补 召回率指标**：`Recall@K`、`MRR`、`NDCG`、`Hit Rate`，用于量化"该召回的是否召回"。

#### 4.1.5 Rerank 重排
- **Cross-Encoder Reranker**（如 `bge-reranker-v2`、Cohere Rerank）：对 `(query, candidate)` 联合打分，显著优于 bi-encoder 初排。
- **▍补 Reciprocal Rank Fusion（RRF）**：将稠密与稀疏两路排序融合，无需归一化即可合并。
- **▍补 重排融合位置**：通常在"向量召回 Top-N（如 50）→ Rerank → Top-K（如 5–8）"之间。

#### 4.1.6 打分机制与**两类评估**（核心补全）
RAG 的"打分"分两层，恰好对应你提到的**检索召回内容准确性**与**模型生成内容准确性**：

**A) 检索质量评估（检索召回内容准确性）**
- **▍补 Context Recall（上下文召回率）**：标准答案所需信息是否都被召回——衡量"漏没漏"。
- **▍补 Context Precision / Context Relevance（上下文精确率/相关性）**：召回块是否相关、有无噪声——衡量"杂没杂"。
- 检索侧指标：`Recall@K / MRR / NDCG`。

**B) 生成质量评估（模型生成内容准确性）**
- **▍补 Faithfulness / 忠实度 / 事实一致性（幻觉检测）**：答案是否严格基于检索上下文、**有无编造**——这是 RAG 最关键的"防幻觉"指标。
- **▍补 Answer Relevance / 答案相关性**：答案是否切题、有用，而非答非所问。
- **▍补 Groundedness / 溯源准确性（Citation / Attribution Accuracy）**：答案中的引用是否**正确指向**上下文对应片段（用于高亮溯源）。

**▍补 评估框架与裁判**：
- **RAGAS**：把上述 Context Recall / Faithfulness / Answer Relevance 等封装为可跑分指标。
- **▍补 LLM-as-Judge（大模型裁判）**：用强模型对"相关性/忠实度"打分，适合无标准答案场景。
- **▍补 在线评估闭环**：用面试真实评分/用户反馈回流，持续监控 Faithfulness 漂移。
- 缓存侧"打分"：语义缓存（Semantic Cache）命中即复用，降低调用与成本。

---

### 4.2 LangGraph 编排

> **现状**：已实现 `StateGraph` 四节点 + 条件边 + 流式 + 三级容错（见 `app/graphs/`）。下方在现状基础上**补全遗漏项**，区分"已实现 / 待补"。

#### 4.2.1 已实现（基于 interview_graph.py / interview_nodes.py）
- **状态定义（State Schema）**：`InterviewState(TypedDict)` 声明全部共享字段（输入/上下文/评估/后续/错误/输出）。
- **节点编排**：`load_context → evaluate → generate_next → save_results`。
- **条件边（Conditional Edges，分支）**：`_route_after_evaluate` 按 `error` 路由 `success / fallback` 两个分支。
- **流式（Streaming）**：`asyncio.Queue` 在 `evaluate` 节点内把 LLM token 实时推给外层 SSE 生成器（`interview_graph_stream`）。
- **三级容错降级（已实现）**：
  - Level 0：`pre_score` 预判断（诚实跳过/空洞回答）直接给基础分，避免浪费 LLM 调用；
  - Level 1：AI 流式评估（带 `tenacity` 重试 + `asyncio.wait_for` 30s 超时）；
  - Level 2–3：`_fallback_evaluate` 预判断降级 → 兜底分数 5.0，**面试不中断**。
- **关键分支日志**：`logger.warning("[evaluate_node] AI 评估失败")`、`logger.warning("[Level 3] 所有评估方案失败")` 等落点清晰。

#### 4.2.2 遗漏项落地状态（✅ 已实现 / ⬜ 待补）

> 2026-10-02 已按用户指令补齐 LangGraph 不足（RAG 暂不引入），涉及文件：`app/graphs/checkpoint.py`(新增)、`interview_graph.py`、`nodes/interview_nodes.py`、`services/client/ai_service.py`、`interview_service.py`、`core/config.py`。

- ✅ **Checkpointer 检查点持久化（断点续传核心）**：图编译时挂载 `MemorySaver`，以 `thread_id = iv:{interview_id}:{question_index}` 持久化每步状态。预留 `RedisSaver / PostgresSaver` 切换分支（装对应依赖后改 `app/graphs/checkpoint.py` 一行即可，无需动业务代码）。
- ⬜ **Human-in-the-loop（人在环）**：尚未实现中断等待人工。建议补充 `interrupt() / __interrupt__ / interrupt_before|after`，在报告发布前、敏感判定处暂停交人工确认。
- ✅ **会话记忆分离**：
  - 短期工作记忆（`InterviewState`，本轮）+ 长期记忆（聊天历史由 `load_context_node` 从 DB `InterviewMessage` 按归属加载，外部化于 DB）；
  - ✅ **记忆压缩（Summarization）**：历史超过 `AI_MEMORY_SUMMARY_THRESHOLD`(默认 8) 条时，较早部分经 `AIService.summarize_history` 摘要，仅保留近期 4 轮原文，压缩后摘要随 prompt 注入（标记 `[历史摘要]`）；
  - ✅ **记忆外部化**：聊天历史与检查点分别存于 DB / 检查点，不耦合业务 State。
- ⬜ **并行分支（Parallel Branches）**：当前仍为线性链。复杂场景可用 `Send` API 并行跑"评分 + 弱点抽取 + 报告草稿"。
- ⬜ **子图（Subgraphs）**：可将"面试 / 复盘 / 报告"封装为可复用子图。
- ✅ **幂等性（Idempotency）**：`thread_id + checkpoint` 保证续跑只跑未完成节点；`save_results_node` 增加同题（interview_id + question_index）已评分守卫，网络重试不会重复存分 / 重复生成报告。
- **超时与重试（已实现 tenacity/asyncio.wait_for）**：建议后续加熔断（Circuit Breaker）防雪崩。
- ✅ **可观测性（节点级）**：`trace_node` 包装四节点，记录进入/完成/耗时(ms)/异常；条件路由 `_route_after_evaluate` 打印 `success / fallback` 分支走向。LangSmith / OpenTelemetry 接入为可选增强（需外部服务与密钥），当前用既有 logging 零依赖实现。
- ⬜ **Tool Calling / Agent 化**：可把"检索、计算器、代码执行"封装为工具节点。
- ⬜ **Guardrails 安全护栏**：建议加敏感词/越狱/越权拦截（尤其面试内容合规）。
- ✅ **动态路由 / 模型降级**：`AI_MODEL_FALLBACK` 配置备用模型；`AIService._chat / _chat_stream` 在主模型失败且配置了备用模型时自动切换，与现有三级容错呼应。

---

### 4.3 文档解析（Document Parsing）

> **现状（已补齐）**：原 `resume_service._extract_pdf_text` 仅用 `pdfplumber` 抽纯文本，仅支持文本型 PDF，无版面/表格/OCR，扫描件与多栏会解析失败。现已落地 `app/services/client/document_parser.py`，在**零新增依赖**（pdfplumber / python-docx / PIL 已在 requirements）前提下补齐多栏重排、表格转 Markdown、标题检测、扫描件检测与多模态 OCR 兜底。

#### 4.3.1 当前链路
```
文件 ──► parse_document() 按扩展名分发
  ├─ PDF  ─► 多栏阅读顺序重排 + 表格(Markdown) + 标题检测 + 扫描件检测
  ├─ DOCX ─► python-docx 正文 + 表格
  └─ TXT/MD
       │
       ├─ 扫描件且 AI_OCR_ENABLED ─► 渲染页面 ─► VLM(Qwen-VL) OCR 兜底
       ▼
  resume_text(含 [表格]/##标题 标记) ──► LLM(RESUME_PARSE_PROMPT) ──► 结构化 JSON
```

#### 4.3.2 复杂文件与结构分块 ✅ 已落地
- **多格式接入** ✅：PDF / DOCX / TXT / MD，路由层 `resume.py` 校验扩展名已同步放开。
- **按文章结构分块（Layout-aware）** ✅（轻量版）：`document_parser` 通过**字号中位数 × 1.22** 与**关键词/全大写短词**检测章节标题，输出 `## 标题` 标记与 `sections` 列表，使 LLM 获得结构感知上下文；`build` 后可演进为"先分块再逐块解析+合并"。

#### 4.3.3 扫描件处理（OCR / 多模态）⬜→✅ 兜底已接，引擎按环境启用
- **扫描件检测** ✅：含图片且抽取文本 < `DOC_PARSER_MIN_TEXT_CHARS`(默认30) 即标记 `is_scanned` 并给出清晰错误提示。
- **多模态模型兜底（VLM OCR）** ✅（代码路径已接）：`ocr_pdf_with_vlm()` 渲染页面 → `AIService.ocr_image()` 以视觉消息调用 `AI_VISION_MODEL`（如 qwen-vl-plus）。**能力检测降级**：仅在 `AI_OCR_ENABLED=True` 且环境安装 `PyMuPDF(fitz)` 或 `pdf2image+poppler` 时启用，否则自动降级为明确错误提示，不引入新依赖。
- **传统 OCR 引擎（PaddleOCR/Tesseract/EasyOCR）**：⬜ 未引入（遵循"不新增第三方库"铁律）；VLM 兜底已覆盖主要场景，如需更高精度/离线可后续接入。

#### 4.3.4 多栏表格处理 ✅ 已落地（基于 pdfplumber，无重模型）
- **阅读顺序还原（Reading Order）** ✅：`_detect_column_divider()` 用词的**水平投影**找贯穿页面的竖向空白带作为分栏线，左栏整体读完再读右栏，解决双栏简历文字错乱。
- **表格结构识别** ✅：`page.extract_tables()` 还原多栏/跨单元格表格并转 Markdown，注入正文 `[表格 Pn]`，LLM 可直接理解技能表等结构。
- **公式识别 / 图表理解（Nougat / 图表 caption）**：⬜ 未做（仅文本/表格型简历影响小，留作后续）。

#### 4.3.5 工程化补全 ⬜→部分
- **去噪清洗（页眉页脚/页码/水印）**：⬜ 未专门处理；pdfplumber 抽取已天然忽略多数装饰。
- **bbox 坐标保留**：⬜ 当前输出为纯文本+Markdown，未保留像素坐标；如需答案溯源高亮（呼应 §4.1.6 Groundedness）可后续补 `chars/rects` 坐标。
- **解析质量评估（表格还原率/字段准确率）**：⬜ 建议作为回归指标纳入测试。

> **小结**：文档解析的"能用"部分（多格式、多栏、表格、扫描件兜底）已落地且零新增依赖；重模型方案（LayoutLM/PP-Structure/Nougat/传统 OCR）按最小改动铁律暂缓，已由 VLM 兜底覆盖核心场景。

---

### 4.4 性能与应对（按实际场景，不堆技术）

> 原则：先满足 20–30 人试点的真实负载，再为扩规模预留扩展点；不为"看起来高级"而引入不对症的技术。

#### 4.4.1 规模画像与承载判断
- 试点期：≈ 20–30 并发面试 × 8–12 题 ≈ **200–300 次/场 LLM 调用**；单机 `FastAPI(async) + PostgreSQL + Redis + Celery` 充足，**无需分布式**。
- 扩展期：面经/知识库语义检索、并发面试数随用户线性增长——瓶颈在**向量召回**与**LLM 配额**，而非业务服务。

#### 4.4.2 已落地的性能手段
- **全异步栈**：FastAPI + asyncpg，I/O 不阻塞，单机即可高并发承接面试请求。
- **流式首字低时延**：SSE + `asyncio.Queue`，评分/评语逐字出，体验不卡。
- **Redis 多级缓存**：
  - LLM 结果缓存：parse / questions / evaluate / report 分别缓存（TTL 1h / 30m），**同一简历、同题、同答直接命中**，省 token 又提速；
  - 系统设置缓存（`setting_service`，更新即失效）；
  - 语义缓存（Semantic Cache）可进一步命中"近似问题"。
- **Celery 异步削峰**：简历解析、报告生成、媒体转码放入队列，前端轮询/通知，避免长请求占用 API 进程。
- **限流（rate_limit）**：防止单用户/全局打满 LLM 配额（429），保障 20–30 人公平。
- **预判断跳过低质量回答**：`pre_score` 识别"不知道/空泛"直接基础分，**省掉一次 AI 调用**，降成本。

#### 4.4.3 扩规模的关键扩展点
- **向量库 Milvus（不影响规模扩展的核心）**：
  - 分布式架构、十亿级向量、分片 + 副本，**水平扩展无需改主流程**；
  - 支持 dense + sparse 混合索引（见 §4.1.2），面经/知识库语义检索扩容时仅需加节点；
  - 与"面试上下文直注"解耦：检索层独立伸缩，业务 API 保持无状态。
- **无状态 API + 外部化状态**：检查点/记忆/缓存外置（Redis/Postgres/Milvus），API 可水平副本。
- **连接池**：DB / Redis / HTTP client 连接复用，避免握手开销。

#### 4.4.4 容错与成本（与 LangGraph 三级容错呼应）
- **LLM 不可用 → 不中断面试**：预判断评分 / 兜底分数（§4.2.1），用户无感。
- **媒体任务失败清理半成品**：FFmpeg 失败即清理、任务不伪装成功（见媒体工具箱规格）。
- **成本优化三板斧**：缓存命中 + 预判断跳过低质回答 + 小模型兜底。
- **可观测性**：日志/埋点/审计（audit_log）+ PV 统计，瓶颈可定位。

#### 4.4.5 灰度与放量
- **等待名单（waitlist）**：先放 20–30 人，按负载与质量指标（Faithfulness / 时延 / 错误率）逐步扩量，出现风险即回收缩容。

---

## 5. 风险与后续建议（仅列出，供人工复核）

1. **RAG 尚未落地**：当前面试上下文为直注式，Milvus 仅规划中；若要做"面经/知识库语义检索"，需补齐检索→重排→评估链路与 §4.1.6 指标。
2. **检查点与记忆分离缺失**：长面试/异常重启会丢失中间态，建议接入 Checkpointer 与记忆压缩（§4.2.2）。
3. **文档解析已补齐（见 §4.3）**：多格式(PDF/DOCX/TXT)、多栏重排、表格转 Markdown、标题检测、扫描件 VLM OCR 兜底均已落地且零新增依赖；重模型方案（LayoutLM/Nougat/传统 OCR/bbox）按最小改动铁律暂缓，公式识别与 bbox 溯源仍为缺口。
4. **人工审核（Human-in-the-loop）缺口**：报告发布、敏感判定建议加 `interrupt` 人工确认。
5. **评估指标闭环缺失**：建议引入 RAGAS / LLM-as-Judge 监控 Faithfulness 漂移。
6. **依赖锁定**：新增向量库/解析库需走 `requirements.txt` 与迁移流程，遵守项目最小改动铁律。

---

*生成依据：读取 `app/graphs/*`、`app/services/client/ai_service.py`、`resume_service.py`、`interview_service.py`、`AGENTS.md`、前端/管理端 `src/views` 及 `requirements.txt`。凡标注「▍补」者为基于你提供的关键词补全的技术名词与建议项，非当前代码已实现。*
