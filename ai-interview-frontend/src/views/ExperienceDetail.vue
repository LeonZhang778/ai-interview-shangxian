<template>
  <div class="detail-page">
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="!experience" class="empty-state">面经不存在或已被删除</div>
    <template v-else>
      <!-- 面包屑 -->
      <div class="breadcrumb-bar">
        <div class="breadcrumb-content">
          <router-link to="/experiences">面经广场</router-link>
          <span class="sep">/</span>
          <span>{{ experience.company }}</span>
          <span class="sep">/</span>
          <span>{{ experience.position }}</span>
        </div>
      </div>

      <!-- 文章头部 -->
      <div class="article-header">
        <h1>{{ experience.title }}</h1>
        <div class="meta-row">
          <span class="author">{{ experience.author_name }}</span>
          <span class="dot">·</span>
          <span class="date">{{ experience.created_at }}</span>
          <span class="dot">·</span>
          <span class="views">阅读 {{ experience.view_count }}</span>
        </div>
        <div class="tags-row">
          <span
            v-for="tag in experience.tags"
            :key="tag"
            class="article-tag"
          >{{ tag }}</span>
          <span class="company-tag">{{ experience.company }}</span>
          <span class="position-tag">{{ experience.position }}</span>
          <span v-if="experience.level" class="level-tag">{{ experience.level }}</span>
          <span v-if="experience.round" class="round-tag">{{ experience.round }}</span>
        </div>
      </div>

      <!-- 文章内容 -->
      <div class="article-body" v-html="renderedContent"></div>

      <!-- 互动区 -->
      <div class="interaction-bar">
        <button class="interact-btn" :class="{ liked }" @click="handleLike">
          <span class="icon">{{ liked ? '❤️' : '🤍' }}</span>
          <span>点赞 {{ experience.like_count }}</span>
        </button>
        <button class="interact-btn" :class="{ collected }" @click="handleCollect">
          <span class="icon">{{ collected ? '⭐' : '☆' }}</span>
          <span>{{ collected ? '已收藏' : '收藏' }} {{ experience.collect_count }}</span>
        </button>
      </div>

      <!-- 评论区 -->
      <div class="comment-section">
        <h2 class="comment-title">评论 ({{ commentTotal }})</h2>

        <!-- 评论输入框 -->
        <div class="comment-input-box">
          <textarea
            v-model="commentContent"
            placeholder="写下你的评论..."
            rows="3"
            maxlength="1000"
          ></textarea>
          <div class="comment-input-actions">
            <span class="char-count">{{ commentContent.length }}/1000</span>
            <button
              class="btn-primary btn-sm"
              :disabled="!commentContent.trim() || commentSubmitting"
              @click="submitComment(null)"
            >
              {{ commentSubmitting ? '发送中...' : '发表评论' }}
            </button>
          </div>
        </div>

        <!-- 评论列表 -->
        <div v-if="comments.length === 0" class="comment-empty">暂无评论，快来抢沙发吧</div>

        <div v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-header">
            <span class="comment-avatar">{{ (c.user.first_name || '?')[0] }}</span>
            <span class="comment-name">{{ c.user.first_name || '匿名用户' }}</span>
            <span class="comment-time">{{ formatTime(c.created_at) }}</span>
            <button
              v-if="Number(authStore.userId) === c.user.id"
              class="comment-delete"
              @click="handleDeleteComment(c.id)"
            >删除</button>
          </div>
          <div class="comment-body">{{ c.content }}</div>
          <div class="comment-footer">
            <button class="reply-btn" @click="replyTo = replyTo === c.id ? null : c.id">
              {{ replyTo === c.id ? '取消回复' : '回复' }}
            </button>
          </div>

          <!-- 回复输入框 -->
          <div v-if="replyTo === c.id" class="reply-input-box">
            <textarea v-model="replyContent" placeholder="回复..." rows="2" maxlength="500"></textarea>
            <button
              class="btn-primary btn-sm"
              :disabled="!replyContent.trim() || commentSubmitting"
              @click="submitReply(c.id)"
            >回复</button>
          </div>

          <!-- 子回复 -->
          <div v-for="r in c.replies" :key="r.id" class="comment-item reply-item">
            <div class="comment-header">
              <span class="comment-avatar small">{{ (r.user.first_name || '?')[0] }}</span>
              <span class="comment-name">{{ r.user.first_name || '匿名用户' }}</span>
              <span class="comment-time">{{ formatTime(r.created_at) }}</span>
              <button
                v-if="Number(authStore.userId) === r.user.id"
                class="comment-delete"
                @click="handleDeleteComment(r.id)"
              >删除</button>
            </div>
            <div class="comment-body">{{ r.content }}</div>
          </div>
        </div>

        <!-- 加载更多 -->
        <div v-if="comments.length < commentTotal" class="comment-load-more">
          <button class="btn-sm" @click="loadComments(commentPage + 1)">加载更多评论</button>
        </div>
      </div>

      <!-- 转化入口 -->
      <div class="cta-section">
        <div class="cta-content">
          <h3>这篇面经的题目，你能在智面答出来吗？</h3>
          <p>上传简历，AI 面试官为你模拟真实面试场景</p>
          <router-link to="/resume/upload" class="cta-btn">开始模拟面试</router-link>
        </div>
      </div>

      <!-- 相关面经 -->
      <div v-if="experience.related && experience.related.length > 0" class="related-section">
        <h2>相关面经推荐</h2>
        <div class="related-list">
          <div
            v-for="item in experience.related"
            :key="item.id"
            class="related-card"
            @click="goToDetail(item.id)"
          >
            <h4>{{ item.title }}</h4>
            <div class="related-tags">
              <span class="company-tag small">{{ item.company }}</span>
              <span class="position-tag small">{{ item.position }}</span>
            </div>
            <div class="related-stats">
              <span>阅读 {{ item.view_count }}</span>
              <span>{{ item.created_at }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getExperienceDetail, likeExperience, collectExperience, getInteractionStatus, getComments, createComment, deleteComment } from '../api/experience'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const experience = ref(null)
const loading = ref(true)
const liked = ref(false)
const collected = ref(false)

const comments = ref([])
const commentTotal = ref(0)
const commentPage = ref(1)
const commentContent = ref('')
const commentSubmitting = ref(false)
const replyTo = ref(null)
const replyContent = ref('')

const renderedContent = computed(() => {
  if (!experience.value?.content) return ''
  return renderMarkdown(experience.value.content)
})

function renderMarkdown(text) {
  if (!text) return ''
  let html = text
    // 标题
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // 粗体和斜体
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 行内代码
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 代码块
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // 列表
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    // 链接
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
    // 换行
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')

  // 包裹 li
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
  html = html.replace(/<\/ul>\s*<ul>/g, '')

  return '<p>' + html + '</p>'
}

async function fetchDetail() {
  loading.value = true
  try {
    const id = route.params.id
    const data = await getExperienceDetail(id)
    experience.value = data
    await Promise.all([loadInteractionStatus(), loadComments(1)])
  } catch (e) {
    console.error('加载面经详情失败:', e)
    experience.value = null
  } finally {
    loading.value = false
  }
}

async function loadInteractionStatus() {
  if (!authStore.token) return
  try {
    const data = await getInteractionStatus(experience.value.id)
    liked.value = data.liked
    collected.value = data.collected
  } catch (e) { /* ignore */ }
}

async function loadComments(page) {
  try {
    const data = await getComments(experience.value.id, { page, size: 20 })
    if (page === 1) {
      comments.value = data.items
    } else {
      comments.value = [...comments.value, ...data.items]
    }
    commentTotal.value = data.total
    commentPage.value = page
  } catch (e) { console.error(e) }
}

async function handleLike() {
  if (!authStore.token) { router.push('/login'); return }
  try {
    const data = await likeExperience(experience.value.id)
    liked.value = data.liked
    experience.value.like_count = data.like_count
  } catch (e) {
    console.error('点赞失败:', e)
  }
}

async function handleCollect() {
  if (!authStore.token) { router.push('/login'); return }
  try {
    const data = await collectExperience(experience.value.id)
    collected.value = data.collected
    experience.value.collect_count = data.collect_count
  } catch (e) {
    console.error('收藏失败:', e)
  }
}

async function submitComment(parentId) {
  if (!authStore.token) { router.push('/login'); return }
  const content = parentId ? replyContent.value : commentContent.value
  if (!content.trim()) return
  commentSubmitting.value = true
  try {
    const newComment = await createComment(experience.value.id, { content: content.trim(), parent_id: parentId || null })
    if (parentId) {
      const parent = comments.value.find(c => c.id === parentId)
      if (parent) { if (!parent.replies) parent.replies = []; parent.replies.push(newComment) }
      replyContent.value = ''
      replyTo.value = null
    } else {
      comments.value.unshift(newComment)
      commentContent.value = ''
    }
    commentTotal.value++
  } catch (e) {
    alert('评论失败: ' + e.message)
  } finally {
    commentSubmitting.value = false
  }
}

async function submitReply(parentId) {
  await submitComment(parentId)
}

async function handleDeleteComment(commentId) {
  if (!confirm('确定删除这条评论？')) return
  try {
    await deleteComment(commentId)
    // Remove from list
    comments.value = comments.value.filter(c => {
      if (c.id === commentId) return false
      c.replies = c.replies.filter(r => r.id !== commentId)
      return true
    })
    commentTotal.value--
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

function formatTime(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function goToDetail(id) {
  router.push(`/experiences/${id}`)
}

watch(() => route.params.id, (newId) => {
  if (newId) fetchDetail()
})

onMounted(() => {
  fetchDetail()
})
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: #f8fafc;
  padding-bottom: 40px;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #9ca3af;
  font-size: 15px;
}

/* 面包屑 */
.breadcrumb-bar {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 0;
}

.breadcrumb-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
  font-size: 13px;
  color: #9ca3af;
}

.breadcrumb-content a {
  color: #4f46e5;
  text-decoration: none;
}

.breadcrumb-content a:hover {
  text-decoration: underline;
}

.sep {
  margin: 0 8px;
  color: #d1d5db;
}

/* 文章头部 */
.article-header {
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 20px 24px;
  background: white;
  border-radius: 0 0 12px 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.article-header h1 {
  font-size: 26px;
  font-weight: 800;
  color: #111827;
  line-height: 1.4;
  margin: 0 0 14px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #9ca3af;
  margin-bottom: 14px;
}

.dot {
  color: #d1d5db;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.article-tag {
  background: #f3f4f6;
  color: #6b7280;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.company-tag {
  background: #eef2ff;
  color: #4f46e5;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.position-tag {
  background: #f0fdf4;
  color: #16a34a;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.level-tag {
  background: #fef3c7;
  color: #d97706;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.round-tag {
  background: #fce7f3;
  color: #db2777;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
}

/* 文章内容 */
.article-body {
  max-width: 800px;
  margin: 20px auto;
  padding: 24px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  font-size: 15px;
  line-height: 1.8;
  color: #374151;
}

.article-body :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  margin: 24px 0 12px;
}

.article-body :deep(h2) {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 20px 0 10px;
}

.article-body :deep(h3) {
  font-size: 17px;
  font-weight: 700;
  color: #111827;
  margin: 16px 0 8px;
}

.article-body :deep(p) {
  margin: 0 0 12px;
}

.article-body :deep(ul) {
  padding-left: 20px;
  margin: 8px 0 12px;
}

.article-body :deep(li) {
  margin-bottom: 6px;
}

.article-body :deep(code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Courier New', monospace;
}

.article-body :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.article-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.article-body :deep(strong) {
  font-weight: 700;
  color: #111827;
}

.article-body :deep(a) {
  color: #4f46e5;
  text-decoration: none;
}

.article-body :deep(a:hover) {
  text-decoration: underline;
}

/* 互动区 */
.interaction-bar {
  max-width: 800px;
  margin: 0 auto 20px;
  display: flex;
  gap: 12px;
  padding: 0 20px;
}

.interact-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: white;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.interact-btn:hover {
  border-color: #4f46e5;
  color: #4f46e5;
}

.interact-btn.liked {
  border-color: #ef4444;
  color: #ef4444;
  background: #fef2f2;
}

.interact-btn.collected {
  border-color: #f59e0b;
  color: #f59e0b;
  background: #fffbeb;
}

.icon {
  font-size: 16px;
}

/* 转化入口 */
.cta-section {
  max-width: 800px;
  margin: 0 auto 24px;
  padding: 0 20px;
}

.cta-content {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  color: white;
}

.cta-content h3 {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 8px;
}

.cta-content p {
  font-size: 14px;
  opacity: 0.9;
  margin: 0 0 20px;
}

.cta-btn {
  display: inline-block;
  padding: 12px 32px;
  border-radius: 10px;
  background: white;
  color: #4f46e5;
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
  transition: transform 0.2s;
}

.cta-btn:hover {
  transform: translateY(-1px);
}

/* 相关推荐 */
.related-section {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
}

.related-section h2 {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 16px;
}

.related-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.related-card {
  background: white;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.related-card:hover {
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1);
}

.related-card h4 {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px;
  line-height: 1.4;
}

.related-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.small {
  font-size: 11px;
  padding: 2px 8px;
}

.related-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #9ca3af;
}

/* 评论区 */
.comment-section {
  max-width: 800px;
  margin: 0 auto 24px;
  padding: 0 20px;
}

.comment-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 16px;
}

.comment-input-box {
  background: white;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.comment-input-box textarea {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  resize: vertical;
  box-sizing: border-box;
}

.comment-input-box textarea:focus {
  outline: none;
  border-color: #4f46e5;
}

.comment-input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.char-count {
  font-size: 12px;
  color: #9ca3af;
}

.comment-empty {
  text-align: center;
  color: #9ca3af;
  padding: 32px 0;
  font-size: 14px;
}

.comment-item {
  background: white;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.reply-item {
  margin-left: 40px;
  margin-bottom: 8px;
  background: #f9fafb;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.comment-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e0e7ff;
  color: #4f46e5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.comment-avatar.small {
  width: 26px;
  height: 26px;
  font-size: 12px;
}

.comment-name {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.comment-time {
  font-size: 12px;
  color: #9ca3af;
  margin-left: auto;
}

.comment-delete {
  font-size: 12px;
  color: #ef4444;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.comment-delete:hover {
  background: #fef2f2;
}

.comment-body {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
  margin-bottom: 8px;
}

.comment-footer {
  display: flex;
  gap: 16px;
}

.reply-btn {
  font-size: 12px;
  color: #6b7280;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.reply-btn:hover {
  color: #4f46e5;
  background: #eef2ff;
}

.reply-input-box {
  margin: 8px 0 8px 40px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.reply-input-box textarea {
  flex: 1;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  resize: none;
}

.reply-input-box textarea:focus {
  outline: none;
  border-color: #4f46e5;
}

.reply-input-box .btn-primary {
  flex-shrink: 0;
  margin-top: 2px;
}

.comment-load-more {
  text-align: center;
  padding: 12px 0;
}

.btn-sm {
  padding: 6px 16px;
  font-size: 13px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: white;
  color: #374151;
  cursor: pointer;
}

.btn-sm:hover {
  border-color: #4f46e5;
  color: #4f46e5;
}

.btn-primary {
  background: #4f46e5;
  color: white;
  border: none;
}

.btn-primary:hover {
  background: #4338ca;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 响应式 */
@media (max-width: 768px) {
  .article-header {
    padding: 24px 16px 20px;
    border-radius: 0;
  }
  .article-header h1 {
    font-size: 20px;
  }
  .article-body {
    margin: 12px;
    padding: 16px;
    border-radius: 10px;
    font-size: 14px;
  }
  .interaction-bar {
    padding: 0 12px;
  }
  .cta-section {
    padding: 0 12px;
  }
  .cta-content {
    padding: 24px 16px;
  }
  .related-section {
    padding: 0 12px;
  }
}
</style>
