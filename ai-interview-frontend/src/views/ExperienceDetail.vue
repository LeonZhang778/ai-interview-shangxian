<template>
  <StarryBackground />
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
            <img v-if="c.user.avatar" :src="c.user.avatar" style="width:32px;height:32px;border-radius:50%;object-fit:cover;flex-shrink:0;display:block;" />
            <span v-else class="comment-avatar">{{ (c.user.first_name || '?')[0] }}</span>
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
              <img v-if="r.user.avatar" :src="r.user.avatar" style="width:26px;height:26px;border-radius:50%;object-fit:cover;flex-shrink:0;display:block;" />
              <span v-else class="comment-avatar small">{{ (r.user.first_name || '?')[0] }}</span>
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

      <!-- AI 模拟面试入口 -->
      <div class="cta-section">
        <div class="cta-content">
          <h3>基于这篇面经，AI 为你模拟面试</h3>
          <p>AI 将根据面经内容生成同类型面试题，开启模拟面试</p>
          <div class="practice-options">
            <select v-model="practiceCount" class="practice-select">
              <option :value="3">3 题</option>
              <option :value="5">5 题</option>
              <option :value="8">8 题</option>
              <option :value="10">10 题</option>
            </select>
            <button class="cta-btn" :disabled="practiceLoading" @click="handlePractice">
              {{ practiceLoading ? '生成中...' : '开始模拟面试' }}
            </button>
          </div>
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
import { startPractice } from '../api/interview'
import { useAuthStore } from '../stores/auth'
import { marked } from 'marked'
import StarryBackground from '../components/StarryBackground.vue'

marked.setOptions({
  breaks: true,
  gfm: true,
})

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const experience = ref(null)
const loading = ref(true)
const liked = ref(false)
const collected = ref(false)

const practiceCount = ref(5)
const practiceLoading = ref(false)

const comments = ref([])
const commentTotal = ref(0)
const commentPage = ref(1)
const commentContent = ref('')
const commentSubmitting = ref(false)
const replyTo = ref(null)
const replyContent = ref('')

const renderedContent = computed(() => {
  if (!experience.value?.content) return ''
  return marked.parse(experience.value.content)
})

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

async function handlePractice() {
  if (!authStore.token) { router.push('/login'); return }
  practiceLoading.value = true
  try {
    const data = await startPractice(experience.value.id, practiceCount.value)
    router.push(`/interview/${data.interview_id}`)
  } catch (e) {
    alert('创建模拟面试失败: ' + e.message)
  } finally {
    practiceLoading.value = false
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
  padding-bottom: 40px;
}
.loading-state, .empty-state { text-align: center; padding: 80px 20px; color: var(--text-dim); font-size: 15px; }

.breadcrumb-bar {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  padding: 12px 0;
}
.breadcrumb-content { max-width: 800px; margin: 0 auto; padding: 0 20px; font-size: 13px; color: var(--text-muted); }
.breadcrumb-content a { color: var(--accent-primary); text-decoration: none; }
.breadcrumb-content a:hover { text-decoration: underline; }
.sep { margin: 0 8px; color: var(--text-dim); }

.article-header {
  max-width: 800px; margin: 0 auto; padding: 32px 20px 24px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 0 0 14px 14px;
}
.article-header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 26px; font-weight: 800; color: var(--text-primary); line-height: 1.4; margin: 0 0 14px; }
.meta-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }
.dot { color: var(--text-dim); }
.tags-row { display: flex; flex-wrap: wrap; gap: 8px; }
.article-tag { background: var(--bg-hover); color: var(--accent-purple); padding: 3px 10px; border-radius: 12px; font-size: 12px; }
.company-tag { background: rgba(139,92,246,0.1); color: var(--accent-purple); padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.position-tag { background: var(--bg-hover); color: var(--accent-purple); padding: 3px 10px; border-radius: 12px; font-size: 12px; }
.level-tag { background: rgba(6,182,212,0.08); color: var(--accent-cyan); padding: 3px 10px; border-radius: 12px; font-size: 12px; }
.round-tag { background: var(--bg-hover); color: var(--accent-purple); padding: 3px 10px; border-radius: 12px; font-size: 12px; }

.article-body {
  max-width: 800px; margin: 20px auto; padding: 24px 20px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; font-size: 15px; line-height: 1.8; color: var(--text-secondary);
}
.article-body :deep(h1) { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 24px 0 12px; }
.article-body :deep(h2) { font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 20px 0 10px; }
.article-body :deep(h3) { font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 16px 0 8px; }
.article-body :deep(p) { margin: 0 0 12px; }
.article-body :deep(ul) { padding-left: 20px; margin: 8px 0 12px; }
.article-body :deep(li) { margin-bottom: 6px; }
.article-body :deep(code) { background: var(--bg-hover); padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: 'Courier New', monospace; color: var(--accent-light); }
.article-body :deep(pre) { background: rgba(0,0,0,0.4); color: var(--text-primary); padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; border: 1px solid var(--border-default); }
.article-body :deep(pre code) { background: none; padding: 0; color: inherit; }
.article-body :deep(strong) { font-weight: 700; color: var(--text-primary); }
.article-body :deep(a) { color: var(--accent-primary); text-decoration: none; }
.article-body :deep(a:hover) { text-decoration: underline; }

.interaction-bar { max-width: 800px; margin: 0 auto 20px; display: flex; gap: 12px; padding: 0 20px; }
.interact-btn {
  display: flex; align-items: center; gap: 8px; padding: 10px 20px;
  border-radius: 10px; border:1px solid var(--border-default);
  background: var(--bg-card); font-size: 14px; color: var(--text-secondary);
  cursor: pointer; transition: all 0.2s;
}
.interact-btn:hover { border-color: rgba(139,92,246,0.3); color: var(--accent-purple); }
.interact-btn.liked { border-color: rgba(239,68,68,0.2); color: var(--red); background: rgba(239,68,68,0.06); }
.interact-btn.collected { border-color: rgba(245,158,11,0.2); color: var(--amber); background: rgba(245,158,11,0.06); }
.icon { font-size: 16px; }

.cta-section { max-width: 800px; margin: 0 auto 24px; padding: 0 20px; }
.cta-content {
  background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(99,102,241,0.15));
  border:1px solid var(--border-default);
  border-radius: 14px; padding: 32px; text-align: center; color: var(--text-primary);
}
.cta-content h3 { font-family: 'Space Grotesk', sans-serif; font-size: 20px; font-weight: 700; margin: 0 0 8px; color: var(--text-primary); }
.cta-content p { font-size: 14px; color: var(--text-secondary); margin: 0 0 20px; }
.practice-options { display: flex; align-items: center; justify-content: center; gap: 12px; }
.practice-select {
  padding: 10px 14px; border-radius: 8px;
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default); font-size: 14px;
  cursor: pointer;
}
.practice-select:focus { outline: none; border-color: rgba(139,92,246,0.4); }
.cta-btn {
  display: inline-block; padding: 12px 32px; border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed, #6366f1); color: white;
  font-size: 15px; font-weight: 700; text-decoration: none; border: none; cursor: pointer;
  transition: all 0.3s; box-shadow: 0 4px 20px rgba(124,58,237,0.3);
}
.cta-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(124,58,237,0.45); }
.cta-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.related-section { max-width: 800px; margin: 0 auto; padding: 0 20px; }
.related-section h2 { font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 700; color: var(--accent-light); margin: 0 0 16px; }
.related-list { display: flex; flex-direction: column; gap: 12px; }
.related-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 12px; padding: 16px; cursor: pointer; transition: all 0.3s;
}
.related-card:hover { border-color: var(--border-hover); background: rgba(139,92,246,0.07); transform: translateY(-1px); }
.related-card h4 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 8px; line-height: 1.4; }
.related-tags { display: flex; gap: 8px; margin-bottom: 8px; }
.small { font-size: 11px; padding: 2px 8px; }
.related-stats { display: flex; gap: 16px; font-size: 12px; color: var(--text-dim); }

.comment-section { max-width: 800px; margin: 0 auto 24px; padding: 0 20px; }
.comment-title { font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 700; color: var(--accent-light); margin: 0 0 16px; }
.comment-input-box {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 12px; padding: 16px; margin-bottom: 20px;
}
.comment-input-box textarea {
  width: 100%; border:1px solid var(--border-default); border-radius: 8px;
  padding: 10px 12px; font-size: 14px; resize: vertical; box-sizing: border-box;
  background: var(--bg-card); color: var(--text-primary);
}
.comment-input-box textarea::placeholder { color: var(--text-dim); }
.comment-input-box textarea:focus { outline: none; border-color: rgba(139,92,246,0.35); }
.comment-input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.char-count { font-size: 12px; color: var(--text-dim); }
.comment-empty { text-align: center; color: var(--text-dim); padding: 32px 0; font-size: 14px; }
.comment-item {
  background: var(--bg-card); border: 1px solid rgba(139,92,246,0.06);
  border-radius: 12px; padding: 16px; margin-bottom: 12px;
}
.reply-item { margin-left: 40px; margin-bottom: 8px; background: rgba(139,92,246,0.02); }
.comment-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.comment-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: rgba(139,92,246,0.12); color: var(--accent-purple);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; flex-shrink: 0;
}
.comment-avatar.small { width: 26px; height: 26px; font-size: 12px; }
.comment-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.comment-time { font-size: 12px; color: var(--text-dim); margin-left: auto; }
.comment-delete { font-size: 12px; color: var(--red); background: none; border: none; cursor: pointer; padding: 2px 6px; border-radius: 4px; }
.comment-delete:hover { background: rgba(239,68,68,0.1); }
.comment-body { font-size: 14px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 8px; }
.comment-footer { display: flex; gap: 16px; }
.reply-btn { font-size: 12px; color: var(--text-muted); background: none; border: none; cursor: pointer; padding: 2px 6px; border-radius: 4px; }
.reply-btn:hover { color: var(--accent-primary); background: var(--bg-hover); }
.reply-input-box { margin: 8px 0 8px 40px; display: flex; gap: 8px; align-items: flex-start; }
.reply-input-box textarea {
  flex: 1; border:1px solid var(--border-default); border-radius: 8px;
  padding: 8px 10px; font-size: 13px; resize: none;
  background: var(--bg-card); color: var(--text-primary);
}
.reply-input-box textarea:focus { outline: none; border-color: rgba(139,92,246,0.35); }
.reply-input-box .btn-primary { flex-shrink: 0; margin-top: 2px; }
.comment-load-more { text-align: center; padding: 12px 0; }
.btn-sm {
  padding: 6px 16px; font-size: 13px; border-radius: 6px;
  border:1px solid var(--border-default); background: var(--bg-hover);
  color: var(--accent-purple); cursor: pointer;
}
.btn-sm:hover { border-color: rgba(139,92,246,0.3); background: rgba(139,92,246,0.12); }
.btn-primary { background: linear-gradient(135deg, #7c3aed, #6366f1); color: white; border: none; }
.btn-primary:hover { box-shadow: 0 4px 16px rgba(124,58,237,0.3); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 768px) {
  .article-header { padding: 24px 16px 20px; border-radius: 0; }
  .article-header h1 { font-size: 20px; }
  .article-body { margin: 12px; padding: 16px; border-radius: 10px; font-size: 14px; }
  .interaction-bar { padding: 0 12px; }
  .cta-section { padding: 0 12px; }
  .cta-content { padding: 24px 16px; }
  .related-section { padding: 0 12px; }
}
</style>
