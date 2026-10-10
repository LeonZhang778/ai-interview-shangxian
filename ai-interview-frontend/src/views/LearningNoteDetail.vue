<template>
  <StarryBackground />
  <div class="note-detail-page">
    <div v-if="loading" class="loading-state">加载中...</div>

    <div v-else-if="!note" class="empty-state">
      <p>笔记不存在或无权查看</p>
      <router-link to="/learning-notes" class="btn-back">返回笔记列表</router-link>
    </div>

    <div v-else class="main-container">
      <button class="back-btn" @click="goBack"><BaseIcon name="chevron-left" :size="16" /> 返回</button>

      <div class="note-layout">
        <!-- 正文 -->
        <div class="note-content-col">
          <!-- 标题区 -->
          <div class="note-header">
        <h1>{{ note.title }}</h1>
        <div class="note-meta">
          <span class="meta-tag" :class="`type-${note.note_type}`">{{ typeLabel(note.note_type) }}</span>
          <span v-if="note.source === 'interview'" class="meta-source">面试回流</span>
          <span v-if="note.status === 'draft'" class="meta-draft">草稿</span>
          <span class="meta-visibility">
            <template v-if="note.visibility === 'private'"><BaseIcon name="lock" :size="13" /> 仅自己</template>
            <template v-else><BaseIcon name="globe" :size="13" /> 公开</template>
          </span>
          <span class="meta-time">{{ formatTime(note.updated_at) }}</span>
        </div>
        <div class="note-tags" v-if="note.tags">
          <span v-for="(tag, i) in note.tags.split(',')" :key="i" class="tag">{{ tag.trim() }}</span>
        </div>
      </div>

      <!-- 游客提示 -->
      <div v-if="!note.is_owner && note.visibility === 'public'" class="guest-notice">
        <BaseIcon name="globe" :size="14" /> 公开笔记 · 无需登录即可阅读
      </div>

<!-- 面试回流关联入口 -->
      <div v-if="note.interview_id && note.is_owner" class="interview-link">
        <router-link :to="`/interview/${note.interview_id}/report`" class="link-text">
          <BaseIcon name="clipboard" :size="14" /> 查看关联的 AI 面试报告 <BaseIcon name="arrow-right" :size="14" />
        </router-link>
      </div>

<!-- AI 摘要 + 要点速览（所有人可见，但仅所有者可操作） -->
      <div class="summary-block">
        <div v-if="summaryLoading" class="summary-loading">AI 摘要生成中...</div>
        <template v-else>
          <div v-if="summary || keyPoints.length" class="summary-card">
            <div v-if="summary" class="summary-text">{{ summary }}</div>
            <div v-if="keyPoints.length" class="key-points">
              <div class="key-points-title"><BaseIcon name="pin" :size="14" /> 要点速览</div>
              <ul>
                <li v-for="(point, i) in keyPoints" :key="i">{{ point }}</li>
              </ul>
            </div>
          </div>
          <button
            v-if="note.is_owner"
            class="btn-regenerate"
            @click="regenerateSummary"
          >
            {{ summary || keyPoints.length ? '重新生成摘要' : '生成 AI 摘要' }}
          </button>
        </template>
      </div>

<!-- 正文 -->
      <div class="note-body">
        <Viewer :value="note.content" :plugins="plugins" />
      </div>

      <!-- 底部统计 -->
      <div class="note-footer">
        <div class="footer-stats">
          <span><BaseIcon name="eye" :size="14" /> {{ note.view_count || 0 }}</span>
          <span><BaseIcon name="thumbs-up" :size="14" /> {{ note.like_count || 0 }}</span>
          <span><BaseIcon name="star-fill" :size="14" /> {{ note.collect_count || 0 }}</span>
          <span><BaseIcon name="message" :size="14" /> {{ note.comment_count || 0 }}</span>
        </div>
        <div v-if="note.is_owner" class="footer-actions">
          <button class="btn-edit" :disabled="flashcardLoading" @click="handleGenerateFlashcards">
            {{ flashcardLoading ? '生成中...' : '生成闪卡' }}
          </button>
          <button class="btn-edit" @click="handlePrintPdf">打印/PDF</button>
          <button class="btn-export-word" :disabled="exportStatus === 'loading'" @click="handleExportWord">
            {{ exportStatus === 'loading' ? '导出中...' : '导出 Word' }}
          </button>
          <button class="btn-edit" @click="goEdit"><BaseIcon name="pencil" :size="14" /> 编辑</button>
          <button class="btn-delete" @click="handleDelete"><BaseIcon name="trash" :size="14" /> 删除</button>
        </div>
      </div>
      <p v-if="flashcardMessage" class="action-tip">{{ flashcardMessage }}</p>
      <p v-if="exportMessage" :class="['action-tip', exportMessageType]">{{ exportMessage }}</p>

      <!-- 公开互动 -->
      <section v-if="note.visibility === 'public' && note.status === 'published'" class="interaction-panel">
        <div class="interaction-actions">
          <button
            type="button"
            class="interaction-btn"
            :class="{ active: interaction.liked }"
            :disabled="!authStore.isLoggedIn || interactionLoading"
            @click="handleLike"
          >
            {{ interaction.liked ? '已点赞' : '点赞' }}
          </button>
          <button
            type="button"
            class="interaction-btn"
            :class="{ active: interaction.collected }"
            :disabled="!authStore.isLoggedIn || interactionLoading"
            @click="handleCollect"
          >
            {{ interaction.collected ? '已收藏' : '收藏' }}
          </button>
          <router-link v-if="!authStore.isLoggedIn" to="/login" class="login-tip">登录后参与互动</router-link>
        </div>

        <div class="comment-box">
          <div class="section-title">评论</div>
          <div v-if="commentsLoading" class="sub-loading">评论加载中...</div>
          <div v-else-if="comments.length === 0" class="sub-empty">还没有评论，来写第一条吧。</div>
          <div v-else class="comment-list">
            <div v-for="comment in comments" :key="comment.id" class="comment-item">
              <div class="comment-main">
                <span class="comment-author">{{ comment.user?.first_name || '用户' }}</span>
                <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
              </div>
              <p>{{ comment.content }}</p>
              <button
                v-if="Number(authStore.userId) === comment.user?.id"
                type="button"
                class="comment-delete"
                @click="handleDeleteComment(comment.id)"
              >
                删除
              </button>
              <div v-if="comment.replies?.length" class="reply-list">
                <div v-for="reply in comment.replies" :key="reply.id" class="reply-item">
                  <span>{{ reply.user?.first_name || '用户' }}：</span>{{ reply.content }}
                </div>
              </div>
            </div>
          </div>

          <div v-if="authStore.isLoggedIn" class="comment-form">
            <textarea
              v-model="commentContent"
              maxlength="500"
              placeholder="写下你的看法..."
              :disabled="commentSubmitting"
            ></textarea>
            <button
              type="button"
              class="interaction-btn active"
              :disabled="commentSubmitting || !commentContent.trim()"
              @click="handleCreateComment"
            >
              {{ commentSubmitting ? '发布中...' : '发布评论' }}
            </button>
          </div>
        </div>
      </section>

      <!-- 相关推荐 -->
      <section v-if="relatedNotes.length" class="related-panel">
        <div class="section-title">相关笔记</div>
        <div class="related-list">
          <button
            v-for="item in relatedNotes"
            :key="item.id"
            type="button"
            class="related-item"
            @click="goRelated(item.id)"
          >
            <span class="related-title">{{ item.title }}</span>
            <span class="related-meta">{{ typeLabel(item.note_type) }} · {{ Math.round((item.similarity || 0) * 100) }}% 相关</span>
          </button>
        </div>
      </section>
        </div>
        <!-- 目录侧栏 -->
        <aside v-if="tocList.length > 1" class="note-toc">
          <div class="toc-title"><BaseIcon name="list" :size="14" /> 目录</div>
          <ul>
            <li
              v-for="item in tocList"
              :key="item.id"
              :class="[`toc-lvl-${item.level}`, { active: activeTocId === item.id }]"
              @click="scrollToHeading(item.id)"
            >{{ item.text }}</li>
          </ul>
        </aside>
        <!-- 移动端浮动目录按钮 + 抽屉 -->
        <button
          v-if="tocList.length > 1"
          class="toc-fab"
          @click="showTocDrawer = !showTocDrawer"
          aria-label="目录"
        ><BaseIcon name="list" :size="18" /></button>
        <transition name="toc-drawer">
          <div v-if="showTocDrawer && tocList.length > 1" class="toc-drawer">
            <div class="toc-drawer-header">
              <span><BaseIcon name="list" :size="14" /> 目录</span>
              <button class="toc-drawer-close" aria-label="关闭目录" @click="showTocDrawer = false"><BaseIcon name="x" :size="16" /></button>
            </div>
            <ul>
              <li
                v-for="item in tocList"
                :key="item.id"
                :class="[`toc-lvl-${item.level}`, { active: activeTocId === item.id }]"
                @click="scrollToHeading(item.id)"
              >{{ item.text }}</li>
            </ul>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'
import { Viewer } from '@bytemd/vue-next'
import gfm from '@bytemd/plugin-gfm'
import highlight from '@bytemd/plugin-highlight'
import 'bytemd/dist/index.css'
import 'highlight.js/styles/github-dark.css'
import { useAuthStore } from '../stores/auth'
import {
  collectNote,
  createNoteComment,
  deleteNote,
  deleteNoteComment,
  exportNoteDocx,
  generateFlashcards,
  generateSummary,
  getNoteComments,
  getNoteDetail,
  getNoteInteractionStatus,
  getRelatedNotes,
  likeNote,
} from '../api/learningNote'

const plugins = [
  gfm(),
  highlight(),
]

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const note = ref(null)
const loading = ref(true)
const summary = ref('')
const keyPoints = ref([])
const summaryLoading = ref(false)
const tocList = ref([])
const activeTocId = ref('')
const showTocDrawer = ref(false)
const interaction = ref({ liked: false, collected: false })
const interactionLoading = ref(false)
const comments = ref([])
const commentsLoading = ref(false)
const commentContent = ref('')
const commentSubmitting = ref(false)
const relatedNotes = ref([])
const flashcardLoading = ref(false)
const flashcardMessage = ref('')
const exportStatus = ref('idle')
const exportMessage = ref('')
const exportMessageType = ref('')

const typeOptions = [
  { value: 'note', label: '笔记' },
  { value: 'review', label: '复盘' },
  { value: 'mistake', label: '错题' },
  { value: 'experience', label: '面经' },
  { value: 'material', label: '资料' },
]

function typeLabel(t) {
  const opt = typeOptions.find(o => o.value === t)
  return opt ? opt.label : t
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
}

function goBack() {
  router.push('/learning-notes')
}

function goEdit() {
  router.push(`/learning-notes/edit/${note.value.id}`)
}

function goRelated(id) {
  router.push(`/learning-notes/${id}`)
}

function handlePrintPdf() {
  window.print()
}

async function handleExportWord() {
  if (!note.value?.id || exportStatus.value === 'loading') return
  exportStatus.value = 'loading'
  exportMessage.value = ''
  try {
    await exportNoteDocx(note.value.id)
    exportMessage.value = 'Word 笔记已开始下载'
    exportMessageType.value = 'success'
  } catch (e) {
    exportMessage.value = e.message || '导出失败，请稍后重试'
    exportMessageType.value = 'error'
  } finally {
    exportStatus.value = 'idle'
  }
}

async function handleDelete() {
  if (!confirm('确定删除这篇笔记？此操作不可撤销。')) return
  try {
    await deleteNote(note.value.id)
    router.push('/learning-notes')
  } catch (e) {
    console.error(e)
    alert('删除失败，请重试')
  }
}

async function loadData() {
  loading.value = true
  try {
    const data = await getNoteDetail(route.params.id)
    note.value = data
    // 用详情接口已返回的摘要初始化，避免重复调用 AI
    summary.value = data.summary || ''
    keyPoints.value = data.key_points || []
    // 先结束加载状态，让正文 DOM 挂载后再构建目录
    loading.value = false
    // bytemd Viewer 异步渲染，双重等待确保 DOM 就绪
    await nextTick()
    await buildTocWithRetry()
    await Promise.all([
      loadRelatedNotes(),
      loadCommentsIfPublic(),
      loadInteractionIfLoggedIn(),
    ])
    // 如果笔记有内容但无摘要，且是所有者，自动触发 AI 摘要生成
    if (data.is_owner && data.content && data.content.trim() && !data.summary) {
      regenerateSummary()
    }
  } catch (e) {
    console.error(e)
    note.value = null
  } finally {
    loading.value = false
  }
}

async function loadInteractionIfLoggedIn() {
  if (!authStore.isLoggedIn || !note.value?.id || note.value.visibility !== 'public') return
  try {
    interaction.value = await getNoteInteractionStatus(note.value.id)
  } catch (e) {
    console.error('加载互动状态失败:', e)
  }
}

async function loadCommentsIfPublic() {
  if (!note.value?.id || note.value.visibility !== 'public' || note.value.status !== 'published') return
  commentsLoading.value = true
  try {
    const res = await getNoteComments(note.value.id, { page: 1, size: 20 })
    comments.value = res.items || []
  } catch (e) {
    console.error('加载评论失败:', e)
  } finally {
    commentsLoading.value = false
  }
}

async function loadRelatedNotes() {
  if (!note.value?.id) return
  try {
    const res = await getRelatedNotes(note.value.id, 5)
    relatedNotes.value = res.items || []
  } catch (e) {
    console.error('加载相关推荐失败:', e)
    relatedNotes.value = []
  }
}

async function handleLike() {
  if (!authStore.isLoggedIn || interactionLoading.value) return
  interactionLoading.value = true
  try {
    const res = await likeNote(note.value.id)
    interaction.value.liked = res.liked
    note.value.like_count = res.like_count
  } catch (e) {
    console.error('点赞失败:', e)
  } finally {
    interactionLoading.value = false
  }
}

async function handleCollect() {
  if (!authStore.isLoggedIn || interactionLoading.value) return
  interactionLoading.value = true
  try {
    const res = await collectNote(note.value.id)
    interaction.value.collected = res.collected
    note.value.collect_count = res.collect_count
  } catch (e) {
    console.error('收藏失败:', e)
  } finally {
    interactionLoading.value = false
  }
}

async function handleCreateComment() {
  const content = commentContent.value.trim()
  if (!content || commentSubmitting.value) return
  commentSubmitting.value = true
  try {
    await createNoteComment(note.value.id, { content })
    commentContent.value = ''
    note.value.comment_count = (note.value.comment_count || 0) + 1
    await loadCommentsIfPublic()
  } catch (e) {
    console.error('发布评论失败:', e)
  } finally {
    commentSubmitting.value = false
  }
}

async function handleDeleteComment(commentId) {
  if (!confirm('确定删除这条评论？')) return
  try {
    await deleteNoteComment(commentId)
    note.value.comment_count = Math.max(0, (note.value.comment_count || 0) - 1)
    await loadCommentsIfPublic()
  } catch (e) {
    console.error('删除评论失败:', e)
  }
}

async function handleGenerateFlashcards() {
  if (!note.value?.is_owner || flashcardLoading.value) return
  flashcardLoading.value = true
  flashcardMessage.value = ''
  try {
    const res = await generateFlashcards(note.value.id)
    flashcardMessage.value = res.message || '闪卡生成完成'
  } catch (e) {
    flashcardMessage.value = e?.message || '生成闪卡失败'
  } finally {
    flashcardLoading.value = false
  }
}

// 生成或重新生成 AI 摘要（force=true 覆盖缓存）
async function regenerateSummary() {
  if (!note.value?.id) return
  summaryLoading.value = true
  try {
    const res = await generateSummary(note.value.id, true)
    summary.value = res.summary || ''
    keyPoints.value = res.key_points || []
  } catch (e) {
    console.error('摘要生成失败:', e)
  } finally {
    summaryLoading.value = false
  }
}

// 从渲染后的 DOM 读取标题生成目录
// bytemd 默认不给标题加 id，这里手动补上 id 以便锚点跳转
function slugify(text) {
  return (text || '')
    .trim()
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function buildToc() {
  tocList.value = []
  activeTocId.value = ''
  const body = document.querySelector('.note-body')
  if (!body) return
  const headings = body.querySelectorAll('h1, h2, h3, h4')
  if (headings.length <= 1) return
  const usedIds = new Set()
  const list = []
  headings.forEach((h) => {
    if (!h.id) {
      const base = slugify(h.textContent || `heading-${list.length}`)
      let id = base || `heading-${list.length}`
      let i = 1
      while (usedIds.has(id)) {
        id = `${base}-${i++}`
      }
      h.id = id
    }
    usedIds.add(h.id)
    list.push({
      id: h.id,
      text: h.textContent || '',
      level: Number(h.tagName.slice(1)),
    })
  })
  tocList.value = list
  if (list.length) activeTocId.value = list[0].id
  window.addEventListener('scroll', onScroll, { passive: true })
}

async function buildTocWithRetry(tries = 10, interval = 200) {
  for (let i = 0; i < tries; i += 1) {
    await nextTick()
    const body = document.querySelector('.note-body')
    if (body && body.querySelectorAll('h1, h2, h3, h4').length > 1) {
      buildToc()
      return
    }
    await new Promise(resolve => setTimeout(resolve, interval))
  }
}

function scrollToHeading(id) {
  const el = document.getElementById(id)
  if (el) {
    const top = el.getBoundingClientRect().top + window.scrollY - 80
    window.scrollTo({ top, behavior: 'smooth' })
    activeTocId.value = id
  }
  showTocDrawer.value = false
}

function onScroll() {
  if (!tocList.value.length) return
  const scrollY = window.scrollY + 120
  let current = tocList.value[0].id
  for (const item of tocList.value) {
    const el = document.getElementById(item.id)
    if (el && el.getBoundingClientRect().top + window.scrollY <= scrollY) {
      current = item.id
    }
  }
  activeTocId.value = current
}

onMounted(loadData)
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.note-detail-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.loading-state {
  text-align: center;
  padding: 80px;
  color: var(--text-muted);
}
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
}
.btn-back {
  display: inline-block;
  margin-top: 16px;
  padding: 10px 24px;
  background: var(--accent-primary); color: var(--bg-base);
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
}
.main-container {
  max-width: 1040px;
  margin: 0 auto;
  padding: 30px 20px;
}
.back-btn {
  background: none;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 6px 14px;
  cursor: pointer;
  margin-bottom: 24px;
  transition: all 0.2s;
}
.back-btn:hover {
  background: rgba(128, 128, 128,0.1);
  border-color: rgba(128, 128, 128,0.3);
}

/* 标题区 */
.note-header {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.note-header h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
  line-height: 1.4;
}
.note-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 10px;
}
.meta-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(128, 128, 128,0.15);
  color: var(--accent-light);
}
.meta-source {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(128, 128, 128,0.15);
  color: #A3A3A3;
}
.meta-draft {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(128, 128, 128,0.15);
  color: #A3A3A3;
}
.meta-visibility {
  font-size: 13px;
  color: var(--text-muted);
}
.meta-time {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
}
.note-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  color: var(--text-muted);
}

/* 面试回流关联 */
.guest-notice {
  margin-bottom: 20px;
  padding: 10px 16px;
  background: rgba(128, 128, 128,0.08);
  border: 1px solid rgba(128, 128, 128,0.2);
  border-radius: 8px;
  color: #A3A3A3;
  font-size: 13px;
}
.interview-link {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(128, 128, 128,0.08);
  border: 1px solid rgba(128, 128, 128,0.2);
  border-radius: 8px;
}
.link-text {
  color: var(--accent-light);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
}
.link-text:hover {
  text-decoration: underline;
}

/* AI 摘要块 */
.summary-block {
  margin-bottom: 20px;
  padding: 16px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
}
.summary-loading {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}
.summary-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.summary-text {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  font-weight: 500;
}
.key-points {
  padding-top: 8px;
  border-top: 1px dashed rgba(255,255,255,0.08);
}
.key-points-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-light);
  margin-bottom: 6px;
}
.key-points ul {
  margin: 0;
  padding-left: 20px;
}
.key-points li {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
}
.btn-regenerate {
  margin-top: 12px;
  padding: 6px 14px;
  background: rgba(128, 128, 128,0.12);
  border: 1px solid rgba(128, 128, 128,0.25);
  border-radius: 8px;
  color: var(--accent-light);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-regenerate:hover {
  background: rgba(128, 128, 128,0.2);
}
.btn-regenerate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 正文 */
.note-body {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-secondary);
}
.note-body :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 24px 0 12px;
}
.note-body :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 20px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.note-body :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 16px 0 8px;
}
.note-body :deep(p) {
  margin: 8px 0;
}
.note-body :deep(ul),
.note-body :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}
.note-body :deep(li) {
  margin: 4px 0;
}
.note-body :deep(blockquote) {
  margin: 12px 0;
  padding: 8px 16px;
  background: rgba(128, 128, 128,0.06);
  border-left: 3px solid var(--accent-purple);
  border-radius: 0 8px 8px 0;
  color: var(--text-secondary);
}
.note-body :deep(code) {
  background: var(--code-inline-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.note-body :deep(pre) {
  background: var(--code-bg);
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
  border: 1px solid var(--code-border);
}
.note-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: var(--code-text);
}
.note-body :deep(strong) {
  font-weight: 600;
  color: var(--text-primary);
}
.note-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}
.note-body :deep(th),
.note-body :deep(td) {
  border: 1px solid rgba(255,255,255,0.1);
  padding: 8px 12px;
  text-align: left;
}
.note-body :deep(th) {
  background: rgba(255,255,255,0.05);
  font-weight: 600;
}

/* 底部 */
.note-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.footer-stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--text-muted);
}
.footer-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.btn-edit,
.btn-delete,
.btn-export-word {
  padding: 6px 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-export-word {
  background: rgba(128, 128, 128,0.12);
  border-color: rgba(128, 128, 128,0.28);
  color: #A3A3A3;
}
.btn-export-word:hover {
  background: rgba(128, 128, 128,0.22);
  border-color: rgba(128, 128, 128,0.45);
  color: #A3A3A3;
}
.btn-export-word:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-edit:hover {
  background: rgba(128, 128, 128,0.15);
  border-color: rgba(128, 128, 128,0.3);
  color: var(--accent-light);
}
.btn-delete:hover {
  background: rgba(128, 128, 128,0.15);
  border-color: rgba(128, 128, 128,0.3);
  color: #A3A3A3;
}
.btn-edit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.action-tip {
  margin: 10px 0 0;
  color: var(--accent-light);
  font-size: 13px;
}
.action-tip.success {
  color: #A3A3A3;
}
.action-tip.error {
  color: #A3A3A3;
}
.interaction-panel,
.related-panel {
  margin-top: 18px;
  padding: 16px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.035);
}
.interaction-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.interaction-btn {
  padding: 7px 14px;
  border: 1px solid rgba(128, 128, 128,0.28);
  border-radius: 8px;
  background: rgba(128, 128, 128,0.1);
  color: var(--accent-light);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.interaction-btn:hover:not(:disabled),
.interaction-btn.active {
  background: rgba(128, 128, 128,0.2);
  border-color: rgba(128, 128, 128,0.45);
}
.interaction-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.login-tip {
  color: var(--text-muted);
  font-size: 13px;
  text-decoration: none;
}
.login-tip:hover {
  color: var(--accent-light);
}
.section-title {
  margin-bottom: 12px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
}
.sub-loading,
.sub-empty {
  padding: 16px 0;
  color: var(--text-muted);
  font-size: 13px;
}
.comment-list {
  display: grid;
  gap: 10px;
}
.comment-item {
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px;
  background: rgba(255,255,255,0.035);
}
.comment-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.comment-author {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}
.comment-time,
.comment-delete,
.reply-item {
  color: var(--text-muted);
  font-size: 12px;
}
.comment-item p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}
.comment-delete {
  margin-top: 8px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
}
.comment-delete:hover {
  color: #A3A3A3;
}
.reply-list {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  padding-left: 12px;
  border-left: 2px solid rgba(255,255,255,0.08);
}
.comment-form {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}
.comment-form textarea {
  min-height: 86px;
  resize: vertical;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-input);
  color: var(--text-primary);
  outline: none;
  line-height: 1.6;
}
.comment-form textarea:focus {
  border-color: var(--border-focus);
}
.related-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.related-item {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px;
  background: rgba(255,255,255,0.035);
  color: var(--text-secondary);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}
.related-item:hover {
  border-color: rgba(128, 128, 128,0.35);
  background: rgba(128, 128, 128,0.08);
}
.related-title,
.related-meta {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.related-title {
  margin-bottom: 6px;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
}
.related-meta {
  color: var(--text-muted);
  font-size: 12px;
}

/* 布局：正文 + 目录侧栏 */
.note-layout {
  display: flex;
  gap: 28px;
  align-items: flex-start;
}
.note-content-col {
  flex: 1;
  min-width: 0;
}

/* 目录侧栏 */
.note-toc {
  position: sticky;
  top: 20px;
  flex: 0 0 200px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  font-size: 13px;
}
.toc-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-default);
}
.note-toc ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.note-toc li {
  padding: 5px 10px;
  color: var(--text-muted);
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: all 0.15s;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.note-toc li:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}
.note-toc li.active {
  color: var(--accent-light);
  border-left-color: var(--accent-purple);
}
.toc-lvl-2 { padding-left: 18px; }
.toc-lvl-3 { padding-left: 30px; font-size: 12px; }
.toc-lvl-4 { padding-left: 42px; font-size: 12px; }

/* 移动端浮动目录按钮（默认隐藏，移动端显示） */
.toc-fab {
  display: none;
}
/* 移动端目录抽屉（默认隐藏） */
.toc-drawer {
  display: none;
}

@media (max-width: 960px) {
  .note-layout {
    flex-direction: column;
    align-items: stretch;
  }
  .note-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }
  .footer-stats,
  .footer-actions {
    flex-wrap: wrap;
  }
  .related-list {
    grid-template-columns: 1fr;
  }
  /* 移动端隐藏固定侧栏，改用浮动按钮 + 抽屉 */
  .note-toc {
    display: none;
  }
  /* 浮动按钮：右下角 */
  .toc-fab {
    display: flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    right: 18px;
    bottom: 80px;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    border: 1px solid var(--border-default);
    background: var(--bg-surface);
    color: var(--text-primary);
    font-size: 20px;
    box-shadow: var(--shadow-sm);
    cursor: pointer;
    z-index: 50;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .toc-fab:active {
    transform: scale(0.92);
  }
  /* 抽屉：从右侧滑出 */
  .toc-drawer {
    display: block;
    position: fixed;
    right: 0;
    top: 0;
    bottom: 0;
    width: 78%;
    max-width: 320px;
    background: var(--bg-surface);
    border-left: 1px solid var(--border-default);
    box-shadow: var(--shadow-sm);
    z-index: 60;
    overflow-y: auto;
    padding: 16px 0;
  }
  .toc-drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 18px 12px;
    border-bottom: 1px solid var(--border-default);
    font-weight: 600;
    color: var(--text-primary);
  }
  .toc-drawer-close {
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
  }
  .toc-drawer ul {
    list-style: none;
    padding: 8px 0;
    margin: 0;
  }
  .toc-drawer li {
    padding: 10px 18px;
    color: var(--text-muted);
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: all 0.15s;
    line-height: 1.5;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .toc-drawer li:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }
  .toc-drawer li.active {
    color: var(--accent-light);
    border-left-color: var(--accent-purple);
    background: var(--bg-hover);
  }
  .toc-drawer .toc-lvl-2 { padding-left: 30px; }
  .toc-drawer .toc-lvl-3 { padding-left: 42px; font-size: 12px; }
  .toc-drawer .toc-lvl-4 { padding-left: 54px; font-size: 12px; }
}
/* 抽屉过渡动画 */
.toc-drawer-enter-active, .toc-drawer-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.toc-drawer-enter-from, .toc-drawer-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
@media print {
  .back-btn,
  .footer-actions,
  .interaction-panel,
  .related-panel,
  .note-toc,
  .toc-fab,
  .toc-drawer,
  .summary-block .btn-regenerate {
    display: none !important;
  }
  .note-detail-page,
  .main-container,
  .note-content-col {
    padding: 0;
    max-width: none;
    color: #141414;
    background: #ffffff;
  }
  .note-header h1,
  .note-body :deep(h1),
  .note-body :deep(h2),
  .note-body :deep(h3),
  .note-body :deep(strong) {
    color: #141414;
  }
  .note-body,
  .summary-text,
  .key-points li {
    color: #374151;
  }
}
</style>
