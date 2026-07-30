# P1 · AI 智能摘要

> 优先级：P1 | 预估工时：1.5 天 | 涉及端：后端 + 前端

---

## 1. 背景与目标

### 当前问题
- 面试回流生成的笔记内容较长，用户需要快速回顾时找不到重点
- 笔记列表页只显示标题，没有内容摘要，用户需要点开才知道是否值得看
- 公开广场的笔记没有预览，降低浏览效率

### 目标
- 为每篇笔记自动生成 AI 一句话摘要（展示在列表卡片 + 详情页顶部）
- 长笔记支持三级要点提炼（适合快速复习）
- 摘要存储在数据库，避免每次读取时重新生成
- 使用 LLM 缓存（已有 `RedisClient.get_llm_cache`）避免重复调用

---

## 2. 数据库设计

### 2.1 新增字段

```python
# 在 LearningNote 模型中新增
summary = Column(String(300), nullable=True)   # AI 一句话摘要，≤300 字
key_points = Column(Text, nullable=True)        # JSON 格式的三级要点列表
```

### 2.2 Alembic 迁移

```python
"""add summary and key_points to learning_notes

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column('learning_notes', sa.Column('summary', sa.String(300), nullable=True))
    op.add_column('learning_notes', sa.Column('key_points', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('learning_notes', 'key_points')
    op.drop_column('learning_notes', 'summary')
```

---

## 3. Prompt 设计

**文件：`app/prompts/learning_note.py`**（新增）

```python
NOTE_SUMMARIZE_PROMPT = """
你是一个面试学习笔记的智能助手。请为以下笔记内容生成：

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
```

---

## 4. 后端实现

### 4.1 摘要生成服务

**文件：`app/services/client/learning_note_service.py`**（新增方法）

```python
import json
from app.services.client.ai_service import AIService
from app.services.common.redis import redis_client
from app.prompts.learning_note import NOTE_SUMMARIZE_PROMPT


@staticmethod
async def generate_summary(
    db: AsyncSession,
    note_id: int,
    user_id: int,
    force: bool = False
) -> Dict:
    """
    为笔记生成 AI 摘要（含缓存）

    Args:
        force: 是否强制重新生成（覆盖已有摘要）
    """
    note = await db.get(LearningNote, note_id)
    if not note or note.user_id != user_id:
        raise NotFoundError(message="笔记不存在")

    # 已有摘要且不强制重新生成，直接返回
    if note.summary and not force:
        return {
            "summary": note.summary,
            "key_points": json.loads(note.key_points) if note.key_points else [],
        }

    # 检查 LLM 缓存（防止完全相同的笔记内容重复调用 AI）
    cache_key = f"summary:{note.content[:500]}"
    cached = await redis_client.get_llm_cache("note_summary", cache_key)
    if cached:
        note.summary = cached["summary"]
        note.key_points = json.dumps(cached["key_points"], ensure_ascii=False)
        await db.commit()
        return cached

    # 调用 AI 生成摘要
    content = note.content[:3000]  # 截取前 3000 字，控制 token 用量
    messages = [
        {"role": "system", "content": NOTE_SUMMARIZE_PROMPT.format(
            title=note.title, note_type=note.note_type, content=content
        )},
    ]

    try:
        result = await AIService._chat(messages, temperature=0.3)
        parsed = AIService._extract_json(result)

        summary = parsed.get("summary", "")[:300]
        key_points = parsed.get("key_points", [])

        # 保存到数据库
        note.summary = summary
        note.key_points = json.dumps(key_points, ensure_ascii=False)
        await db.commit()

        # 写入 LLM 缓存（TTL 7 天，笔记内容不变时无需重新生成）
        await redis_client.set_llm_cache(
            "note_summary", cache_key,
            {"summary": summary, "key_points": key_points},
            ttl=7 * 24 * 3600
        )

        return {"summary": summary, "key_points": key_points}
    except Exception as e:
        logger.error(f"笔记摘要生成失败: {e}")
        return {"summary": "", "key_points": [], "error": str(e)}
```

### 4.2 新增 API

**文件：`app/api/client/v1/learning_note.py`**

```python
@router.post("/{note_id}/summary")
async def generate_note_summary(
    note_id: int,
    force: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成或获取笔记的 AI 摘要"""
    result = await learning_note_service.generate_summary(
        db=db, note_id=note_id, user_id=current_user.id, force=force
    )
    return ApiResponse.success(data=result)
```

### 4.3 批量生成摘要（后台任务）

**文件：`app/schedule/jobs/note_tasks.py`**（新增）

```python
import logging
from celery import shared_task
from app.db.session import async_session_factory
from app.services.client.learning_note_service import learning_note_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def batch_generate_summaries(self, user_id: int = None):
    """
    批量生成笔记摘要（后台任务）
    用户打开笔记列表时触发，或定时任务每晚执行
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        async with async_session_factory() as db:
            from sqlalchemy import select
            from app.models.learning_note import LearningNote

            conditions = [LearningNote.summary.is_(None)]
            if user_id:
                conditions.append(LearningNote.user_id == user_id)

            query = select(LearningNote).where(*conditions).limit(50)
            result = await db.execute(query)
            notes = result.scalars().all()

            for note in notes:
                try:
                    await learning_note_service.generate_summary(
                        db=db, note_id=note.id, user_id=note.user_id
                    )
                except Exception as e:
                    logger.warning(f"生成摘要失败: note_id={note.id}, {e}")
                    continue

            return len(notes)

    return loop.run_until_complete(_run())
```

---

## 5. 前端实现

### 5.1 列表卡片显示摘要

**文件：`ai-interview-frontend/src/views/LearningNotes.vue`**

```vue
<template>
  <div class="note-card" @click="goDetail(note.id)">
    <!-- 标题 -->
    <div class="card-title">{{ note.title }}</div>
    <!-- AI 摘要（新增） -->
    <div v-if="note.summary" class="card-summary">{{ note.summary }}</div>
    <!-- 类型标签 -->
    <div class="card-meta">...</div>
  </div>
</template>

<style scoped>
.card-summary {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 6px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
```

### 5.2 详情页顶部显示摘要 + 要点

**文件：`ai-interview-frontend/src/views/LearningNoteDetail.vue`**

```vue
<template>
  <!-- 在标题下方 -->
  <div v-if="summary" class="summary-block">
    <div class="summary-text">{{ summary }}</div>
    <div v-if="keyPoints.length" class="key-points">
      <div class="key-points-title">📌 要点速览</div>
      <ul>
        <li v-for="(point, i) in keyPoints" :key="i">{{ point }}</li>
      </ul>
    </div>
    <button
      v-if="isOwner"
      class="btn-regenerate"
      @click="regenerateSummary"
    >🔄 重新生成摘要</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { generateSummary } from '../api/learningNote'

const summary = ref('')
const keyPoints = ref([])

async function loadSummary() {
  if (!note.value?.id) return
  try {
    const res = await generateSummary(note.value.id)
    summary.value = res.summary || ''
    keyPoints.value = res.key_points || []
  } catch (e) {
    // 静默失败，不影响页面渲染
    console.warn('摘要加载失败:', e)
  }
}

async function regenerateSummary() {
  try {
    const res = await generateSummary(note.value.id, true)
    summary.value = res.summary || ''
    keyPoints.value = res.key_points || []
  } catch (e) {
    console.error(e)
  }
}

onMounted(loadSummary)
</script>
```

### 5.3 新增 API 封装

```javascript
// 在 ai-interview-frontend/src/api/learningNote.js 中
export function generateSummary(id, force = false) {
  return api.post(`/learning-notes/${id}/summary`, null, { params: { force } })
}
```

---

## 6. 迁移步骤

### Day 1
1. 执行 Alembic 迁移（新增 `summary` / `key_points` 字段）
2. 新建 `app/prompts/learning_note.py` 写入 prompt
3. 实现 `generate_summary` 方法
4. 新增 API 端点
5. 编写后台批量任务

### Day 2（半天）
1. 前端列表卡片显示摘要
2. 详情页显示摘要 + 要点速览
3. 测试生成和缓存逻辑

---

## 7. 验证清单

- [ ] 对有内容的笔记调用摘要 API，返回格式正确的 JSON
- [ ] 摘要 ≤50 字，要点 3-5 条
- [ ] 不修改笔记内容时，重复调用返回缓存（不消耗 AI token）
- [ ] 列表卡片正确显示摘要
- [ ] 详情页正确显示摘要 + 要点速览
- [ ] 强制重新生成按钮覆盖缓存
- [ ] 空笔记返回空摘要，不报错