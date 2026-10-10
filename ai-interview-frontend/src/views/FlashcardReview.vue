<template>
  <StarryBackground />
  <div class="flashcard-page">
    <div class="page-header">
      <button type="button" class="back-btn" @click="router.push('/learning-notes')">返回笔记</button>
      <div>
        <h1>闪卡复习</h1>
        <p class="header-desc">按间隔重复节奏复盘面试知识点</p>
      </div>
    </div>

    <main class="main-container">
      <div v-if="error" class="page-message error-message" role="alert">
        <span>{{ error }}</span>
        <button type="button" @click="loadData">重试</button>
      </div>
      <div v-if="successMessage" class="page-message success-message" role="status">
        {{ successMessage }}
      </div>

      <section class="stats-row">
        <div class="stat-tile">
          <div class="stat-value">{{ stats.due || 0 }}</div>
          <div class="stat-label">待复习</div>
        </div>
        <div class="stat-tile">
          <div class="stat-value">{{ stats.reviewed_today || 0 }}</div>
          <div class="stat-label">今日已复习</div>
        </div>
        <div class="stat-tile">
          <div class="stat-value">{{ stats.mastered || 0 }}</div>
          <div class="stat-label">已掌握</div>
        </div>
        <div class="stat-tile">
          <div class="stat-value">{{ stats.total || 0 }}</div>
          <div class="stat-label">总闪卡</div>
        </div>
      </section>

      <div v-if="loading" class="loading-state">加载中...</div>

      <section v-else-if="cards.length" class="review-panel">
        <div class="review-toolbar">
          <span>第 {{ currentIndex + 1 }} / {{ cards.length }} 张</span>
          <span>间隔 {{ currentCard.interval || 0 }} 天</span>
        </div>

        <button
          type="button"
          class="flashcard"
          :class="{ flipped: showAnswer }"
          @click="showAnswer = !showAnswer"
        >
          <span class="card-kicker">{{ showAnswer ? '答案' : '问题' }}</span>
          <span class="card-text">{{ showAnswer ? currentCard.answer : currentCard.question }}</span>
          <span class="card-hint">{{ showAnswer ? '选择你的掌握程度' : '点击查看答案' }}</span>
        </button>

        <div v-if="showAnswer" class="quality-grid">
          <button
            v-for="option in qualityOptions"
            :key="option.value"
            type="button"
            class="quality-btn"
            :disabled="reviewing"
            @click="submitReview(option.value)"
          >
            <span>{{ option.label }}</span>
            <small>{{ option.desc }}</small>
          </button>
        </div>
      </section>

      <section v-else class="empty-state">
        <div class="empty-icon"><BaseIcon name="check" :size="40" /></div>
        <p>今天没有待复习的闪卡</p>
        <router-link to="/learning-notes" class="primary-link">去笔记详情页生成闪卡</router-link>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'
import { getDueCards, getFlashcardStats, reviewCard } from '../api/learningNote'

const router = useRouter()
const cards = ref([])
const stats = ref({})
const currentIndex = ref(0)
const showAnswer = ref(false)
const loading = ref(true)
const reviewing = ref(false)
const error = ref('')
const successMessage = ref('')

const qualityOptions = [
  { value: 0, label: '完全忘记', desc: '重新开始' },
  { value: 2, label: '答错但熟悉', desc: '明天再来' },
  { value: 3, label: '勉强答对', desc: '短间隔复习' },
  { value: 4, label: '基本掌握', desc: '正常推进' },
  { value: 5, label: '非常熟练', desc: '拉长间隔' },
]

const currentCard = computed(() => cards.value[currentIndex.value] || {})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [dueRes, statsRes] = await Promise.all([
      getDueCards(20),
      getFlashcardStats(),
    ])
    cards.value = dueRes.cards || []
    stats.value = statsRes || {}
    currentIndex.value = 0
    showAnswer.value = false
  } catch (e) {
    error.value = e?.message || '加载闪卡失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function submitReview(quality) {
  if (!currentCard.value.id || reviewing.value) return
  reviewing.value = true
  error.value = ''
  successMessage.value = ''
  try {
    const res = await reviewCard(currentCard.value.id, quality)
    successMessage.value = `下次复习：${formatDate(res.next_review_at)}`
    if (currentIndex.value < cards.value.length - 1) {
      currentIndex.value += 1
      showAnswer.value = false
    } else {
      await loadData()
    }
  } catch (e) {
    error.value = e?.message || '提交复习结果失败'
  } finally {
    reviewing.value = false
  }
}

function formatDate(value) {
  if (!value) return '稍后'
  return new Date(value).toLocaleDateString('zh-CN')
}

onMounted(loadData)
</script>

<style scoped>
.flashcard-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.page-header {
  max-width: 960px;
  display: flex;
  align-items: center;
  gap: 18px;
  margin: 0 auto;
  padding: 34px 20px 18px;
}
.page-header h1 {
  margin: 0 0 6px;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}
.header-desc {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
}
.back-btn,
.primary-link,
.page-message button {
  border: 1px solid rgba(128, 128, 128, 0.28);
  border-radius: 8px;
  background: rgba(128, 128, 128, 0.12);
  color: var(--accent-light);
  cursor: pointer;
  transition: all 0.2s;
}
.back-btn {
  padding: 7px 14px;
  flex-shrink: 0;
}
.back-btn:hover,
.primary-link:hover,
.page-message button:hover {
  background: rgba(128, 128, 128, 0.2);
  border-color: rgba(128, 128, 128, 0.45);
}
.main-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 20px;
}
.page-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}
.page-message button {
  padding: 4px 10px;
}
.error-message {
  color: #A3A3A3;
  background: rgba(128, 128, 128, 0.14);
  border: 1px solid rgba(128, 128, 128, 0.3);
}
.success-message {
  color: #A3A3A3;
  background: rgba(163, 163, 163, 0.14);
  border: 1px solid rgba(163, 163, 163, 0.3);
}
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}
.stat-tile {
  padding: 16px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--accent-light);
}
.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}
.loading-state,
.empty-state {
  padding: 70px 20px;
  text-align: center;
  color: var(--text-muted);
}
.empty-icon {
  width: 52px;
  height: 52px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  border-radius: 50%;
  color: #A3A3A3;
  border: 1px solid rgba(163, 163, 163, 0.3);
  background: rgba(163, 163, 163, 0.12);
  font-size: 24px;
}
.primary-link {
  display: inline-block;
  margin-top: 12px;
  padding: 9px 18px;
  text-decoration: none;
}
.review-panel {
  display: grid;
  gap: 16px;
}
.review-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}
.flashcard {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
  padding: 28px;
  border: 1px solid rgba(128, 128, 128, 0.28);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition: transform 0.2s, border-color 0.2s, background 0.2s;
}
.flashcard:hover {
  transform: translateY(-2px);
  border-color: rgba(128, 128, 128, 0.5);
}
.flashcard.flipped {
  background: var(--bg-hover);
}
.card-kicker {
  color: var(--accent-light);
  font-size: 13px;
  font-weight: 600;
}
.card-text {
  font-size: 22px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.card-hint {
  color: var(--text-muted);
  font-size: 12px;
}
.quality-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}
.quality-btn {
  min-height: 72px;
  padding: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.05);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}
.quality-btn:hover:not(:disabled) {
  border-color: rgba(128, 128, 128,0.4);
  background: rgba(128, 128, 128,0.12);
  color: var(--text-primary);
}
.quality-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.quality-btn span,
.quality-btn small {
  display: block;
}
.quality-btn span {
  font-size: 13px;
  font-weight: 600;
}
.quality-btn small {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
}
@media (max-width: 768px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .stats-row,
  .quality-grid {
    grid-template-columns: 1fr 1fr;
  }
  .card-text {
    font-size: 18px;
  }
}
</style>
