# P1 · AI 智能标签

> 优先级：P1 | 预估工时：1 天 | 涉及端：后端

---

## 1. 背景与目标

### 当前问题
- 标签需要用户手动输入，大部分用户嫌麻烦不填
- 标签格式不统一（"Redis" vs "redis" vs "Redis缓存"）
- 标签无法对齐面试知识点体系，不利于后续推荐

### 目标
- 保存/更新笔记时自动分析内容，推荐 3-5 个标签
- 标签对齐标准面试知识点体系（技术栈、中间件、算法、数据库等）
- 标签自动去重、标准化大小写
- 支持用户手动调整 AI 推荐标签
- 使用 LLM 缓存避免重复调用

---

## 2. 技术方案

### 2.1 Prompt 设计

**文件：`app/prompts/learning_note.py`**

```python
NOTE_TAG_PROMPT = """
你是一个面试知识标签专家。请分析以下笔记内容，推荐 3-5 个最相关的技术标签。

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
```

### 2.2 标签标准化工具

```python
# 在 app/utils/utils.py 中新增

TAG_ALIASES = {
    "redis": "Redis",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "pg": "PostgreSQL",
    "mongodb": "MongoDB",
    "elasticsearch": "Elasticsearch",
    "es": "Elasticsearch",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "mq": "RabbitMQ",
    "docker": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "nginx": "Nginx",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "python": "Python",
    "java": "Java",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "cpp": "C++",
    "c++": "C++",
    "react": "React",
    "vue": "Vue",
    "vuejs": "Vue",
    "fastapi": "FastAPI",
    "springboot": "Spring Boot",
    "spring": "Spring Boot",
    "gin": "Gin",
    "django": "Django",
    "flask": "Flask",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "terraform": "Terraform",
    "cicd": "CI/CD",
    "ci/cd": "CI/CD",
}


def normalize_tag(tag: str) -> str:
    """标准化标签名称"""
    tag = tag.strip()
    # 处理别名
    lower = tag.lower().replace(" ", "").replace("-", "").replace("_", "")
    if lower in TAG_ALIASES:
        return TAG_ALIASES[lower]
    # 首字母大写
    return tag[0].upper() + tag[1:] if tag else tag
```

---

## 3. 后端实现

### 3.1 智能标签服务

**文件：`app/services/client/learning_note_service.py`**（新增方法）

```python
@staticmethod
async def suggest_tags(
    db: AsyncSession,
    note_id: int,
    user_id: int
) -> Dict:
    """
    为笔记推荐 AI 标签（自动分析内容）
    """
    note = await db.get(LearningNote, note_id)
    if not note or note.user_id != user_id:
        raise NotFoundError(message="笔记不存在")

    # 检查 LLM 缓存
    cache_key = f"tags:{note.content[:500]}"
    cached = await redis_client.get_llm_cache("note_tags", cache_key)
    if cached:
        return cached

    # 调用 AI
    content = note.content[:2000]
    messages = [
        {"role": "system", "content": NOTE_TAG_PROMPT.format(
            title=note.title, note_type=note.note_type, content=content
        )},
    ]

    try:
        result = await AIService._chat(messages, temperature=0.3)
        parsed = AIService._extract_json(result)

        raw_tags = parsed.get("tags", [])
        reason = parsed.get("reason", "")

        # 标准化标签
        from app.utils.utils import normalize_tag
        tags = list(dict.fromkeys([normalize_tag(t) for t in raw_tags if t.strip()]))
        tags = tags[:5]  # 最多 5 个

        result = {"tags": tags, "reason": reason}

        # 写入缓存（7 天）
        await redis_client.set_llm_cache("note_tags", cache_key, result, ttl=7 * 24 * 3600)

        return result
    except Exception as e:
        logger.error(f"标签推荐失败: {e}")
        return {"tags": [], "reason": "", "error": str(e)}
```

### 3.2 自动打标签（Hook 在保存时）

修改 `create_note` 和 `update_note` 方法，在保存后异步触发标签推荐：

```python
@staticmethod
async def create_note(db, user_id, title, content="", ...):
    # ... 现有创建逻辑 ...

    # 异步触发标签推荐（不阻塞请求）
    asyncio.create_task(
        LearningNoteService._auto_tag_note(db, note.id, user_id)
    )

    return {"id": note.id, "title": note.title}


@staticmethod
async def _auto_tag_note(db: AsyncSession, note_id: int, user_id: int):
    """异步自动打标签（后台任务，失败不影响主流程）"""
    try:
        # 需要在新 session 中执行（因为传入的 db 可能已被关闭）
        async with async_session_factory() as new_db:
            note = await new_db.get(LearningNote, note_id)
            if not note:
                return

            # 如果用户已经手动设置了标签，跳过 AI 推荐
            if note.tags and note.tags.strip():
                return

            result = await LearningNoteService.suggest_tags(
                new_db, note_id, user_id
            )
            if result.get("tags"):
                note.tags = ",".join(result["tags"])
                await new_db.commit()
                logger.info(f"笔记 {note_id} 自动标签: {note.tags}")
    except Exception as e:
        logger.warning(f"自动打标签失败: note_id={note_id}, {e}")
```

### 3.3 新增 API

```python
@router.post("/{note_id}/suggest-tags")
async def suggest_note_tags(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 AI 推荐的标签"""
    result = await learning_note_service.suggest_tags(
        db=db, note_id=note_id, user_id=current_user.id
    )
    return ApiResponse.success(data=result)


@router.post("/{note_id}/apply-tags")
async def apply_suggested_tags(
    note_id: int,
    body: TagApplyBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """应用 AI 推荐的标签（用户确认后保存）"""
    result = await learning_note_service.update_note(
        db=db, user_id=current_user.id, note_id=note_id,
        tags=",".join(body.tags)
    )
    return ApiResponse.success(data=result)


class TagApplyBody(BaseModel):
    tags: list[str]
```

---

## 4. 前端实现

### 4.1 编辑页标签推荐

**文件：`ai-interview-frontend/src/views/LearningNoteEdit.vue`**

```vue
<template>
  <!-- 标签输入区 -->
  <div class="form-group">
    <label>标签</label>
    <div class="tag-input-area">
      <input
        v-model="tagInput"
        placeholder="输入标签后按回车"
        @keyup.enter="addTag"
      />
      <button
        v-if="!aiTagsLoaded"
        class="btn-ai-tag"
        @click="loadAiTags"
        :disabled="loadingTags"
      >
        🤖 AI 推荐标签
      </button>
    </div>
    <!-- 已选标签 -->
    <div class="tag-list">
      <span v-for="(tag, i) in form.tagsArray" :key="i" class="tag">
        {{ tag }}
        <span class="tag-remove" @click="removeTag(i)">✕</span>
      </span>
    </div>
    <!-- AI 推荐标签 -->
    <div v-if="aiTags.length" class="ai-tags">
      <span class="ai-tags-label">AI 推荐：</span>
      <span
        v-for="tag in aiTags"
        :key="tag"
        class="tag tag-suggested"
        :class="{ selected: form.tagsArray.includes(tag) }"
        @click="toggleAiTag(tag)"
      >{{ tag }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { suggestTags } from '../api/learningNote'

const aiTags = ref([])
const aiTagsLoaded = ref(false)
const loadingTags = ref(false)

// 将逗号分隔的 tags 字符串转为数组，方便前端操作
const form = ref({
  tags: '',
  tagsArray: computed({
    get: () => form.value.tags ? form.value.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
    set: (arr) => { form.value.tags = arr.join(',') },
  }),
})

async function loadAiTags() {
  if (!noteId.value) return
  loadingTags.value = true
  try {
    const res = await suggestTags(noteId.value)
    aiTags.value = res.tags || []
    aiTagsLoaded.value = true
  } catch (e) {
    console.error(e)
  } finally {
    loadingTags.value = false
  }
}

function toggleAiTag(tag) {
  const arr = form.value.tagsArray
  if (arr.includes(tag)) {
    arr.splice(arr.indexOf(tag), 1)
  } else {
    arr.push(tag)
  }
  form.value.tagsArray = arr
}

function addTag() {
  if (tagInput.value.trim()) {
    form.value.tagsArray = [...form.value.tagsArray, tagInput.value.trim()]
    tagInput.value = ''
  }
}

function removeTag(idx) {
  const arr = form.value.tagsArray
  arr.splice(idx, 1)
  form.value.tagsArray = arr
}
</script>

<style scoped>
.tag-input-area {
  display: flex;
  gap: 8px;
}
.btn-ai-tag {
  padding: 6px 14px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-ai-tag:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  background: rgba(99,102,241,0.15);
  color: var(--accent-light);
}
.tag-remove {
  cursor: pointer;
  opacity: 0.6;
}
.ai-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
  padding: 8px;
  background: rgba(99,102,241,0.05);
  border-radius: 8px;
}
.ai-tags-label {
  font-size: 12px;
  color: var(--text-muted);
}
.tag-suggested {
  cursor: pointer;
  background: rgba(255,255,255,0.06);
  color: var(--text-muted);
  transition: all 0.2s;
}
.tag-suggested:hover {
  background: rgba(99,102,241,0.2);
}
.tag-suggested.selected {
  background: rgba(99,102,241,0.25);
  color: var(--accent-light);
}
</style>
```

### 4.2 新增 API 封装

```javascript
// 在 ai-interview-frontend/src/api/learningNote.js 中
export function suggestTags(id) {
  return api.post(`/learning-notes/${id}/suggest-tags`)
}

export function applyTags(id, tags) {
  return api.post(`/learning-notes/${id}/apply-tags`, { tags })
}
```

---

## 5. 迁移步骤

### Day 1
1. 编写 `NOTE_TAG_PROMPT` 和 `normalize_tag` 工具函数
2. 实现 `suggest_tags` 方法（含 LLM 缓存）
3. 实现 `_auto_tag_note` 异步任务
4. 修改 `create_note` 和 `update_note`，保存后触发自动打标签
5. 新增 API 端点（推荐标签 + 应用标签）
6. 前端标签组件改造

---

## 6. 验证清单

- [ ] 新建笔记后，自动生成标签（后台异步，不阻塞保存）
- [ ] 用户手动设置标签后，不再覆盖
- [ ] AI 推荐标签标准化（"redis" → "Redis"）
- [ ] 重复内容返回缓存，不消耗 token
- [ ] 前端可点击 AI 推荐标签添加到已选列表
- [ ] 标签编辑器支持手动添加和删除