"""学习笔记模块的 AI Prompt 定义。"""

NOTE_SUMMARIZE_PROMPT = """你是一个面试学习笔记的智能助手。请为以下笔记内容生成：

1. **一句话摘要**（≤50 字）：用一句话概括笔记的核心内容
2. **三级要点**（3-5 条）：用 Markdown 列表列出笔记最重要的知识点

要求：
- 摘要必须 ≤50 字，适合展示在卡片列表
- 要点每条 ≤30 字，突出重点
- 如果是面试复盘类笔记，突出薄弱点和改进建议
- 使用中文输出

笔记标题：{title}
笔记类型：{note_type}

笔记内容：
{content}

请严格按照以下 JSON 格式输出，不要添加其他内容：
{{
    "summary": "一句话摘要",
    "key_points": ["要点1", "要点2", "要点3"]
}}
"""

NOTE_TAG_SUGGEST_PROMPT = """你是一个面试知识标签专家。请分析以下笔记内容，推荐 3-5 个最相关的技术标签。

标签应从以下分类中选择（不限于此列表）：
- 编程语言：Python, Java, Go, Rust, C++, JavaScript, TypeScript, SQL
- 数据库：MySQL, PostgreSQL, Redis, MongoDB, Elasticsearch, ClickHouse
- 中间件：Kafka, RabbitMQ, Nginx, Docker, Kubernetes
- 框架：Spring Boot, FastAPI, Gin, Vue, React, Django, Flask
- 云原生：AWS, GCP, Docker, Kubernetes, Terraform, CI/CD
- 计算机基础：数据结构, 算法, 操作系统, 网络, 设计模式
- 面试专项：系统设计, 行为面试, 项目经验, 简历优化

要求：
1. 标签使用标准名称（首字母大写，如 "Redis" 而非 "redis"）
2. 每个标签 ≤10 个字符
3. 如果内容不在已知分类中，可以提炼新标签，但必须符合技术命名规范
4. 不超过 5 个标签
5. 从笔记的标题、正文、类型中综合判断

笔记标题：{title}
笔记类型：{note_type}

笔记内容（前 2000 字）：
{content}

请严格按照以下 JSON 格式输出，不要添加其他内容：
{{
    "tags": ["标签1", "标签2", "标签3"],
    "reason": "简要说明推荐理由"
}}
"""
