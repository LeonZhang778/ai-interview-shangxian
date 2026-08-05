<template>
  <StarryBackground />
  <div class="mistake-page">
    <div class="page-header">
      <button type="button" class="back-btn" @click="router.push('/learning-notes')">返回笔记</button>
      <div>
        <h1>错题本仪表盘</h1>
        <p class="header-desc">聚合面试薄弱点和错题笔记，安排下一步练习</p>
      </div>
    </div>

    <main class="main-container">
      <div v-if="error" class="page-message error-message" role="alert">
        <span>{{ error }}</span>
        <button type="button" @click="loadData">重试</button>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>

      <template v-else>
        <section class="stats-row">
          <div class="stat-tile">
            <div class="stat-value">{{ dashboard.mistake_count || 0 }}</div>
            <div class="stat-label">错题笔记</div>
          </div>
          <div class="stat-tile">
            <div class="stat-value">{{ weakness.total || 0 }}</div>
            <div class="stat-label">薄弱知识点</div>
          </div>
          <div class="stat-tile accent">
            <div class="stat-value text">{{ weakness.top_3?.[0]?.keyword || '暂无' }}</div>
            <div class="stat-label">最需要补强</div>
          </div>
        </section>

        <section class="section-panel">
          <div class="section-header">
            <h2>薄弱点热力图</h2>
            <span>{{ weakness.total || 0 }} 个知识点</span>
          </div>
          <div v-if="weakness.items?.length" class="heatmap">
            <button
              v-for="item in weakness.items"
              :key="item.keyword"
              type="button"
              class="heat-chip"
              :style="{ '--heat': 0.22 + item.heat * 0.48 }"
            >
              <span>{{ item.keyword }}</span>
              <strong>{{ item.count }}</strong>
            </button>
          </div>
          <div v-else class="empty-state compact">完成面试或创建错题笔记后，这里会出现薄弱点分布。</div>
        </section>

        <section class="section-panel">
          <div class="section-header">
            <h2>最近错题</h2>
            <router-link to="/learning-notes/edit?type=mistake" class="section-link">新建错题</router-link>
          </div>
          <div v-if="dashboard.recent_mistakes?.length" class="mistake-list">
            <router-link
              v-for="item in dashboard.recent_mistakes"
              :key="item.id"
              :to="`/learning-notes/${item.id}`"
              class="mistake-item"
            >
              <span class="mistake-title">{{ item.title }}</span>
              <span class="mistake-tags">{{ item.tags || '未标记标签' }}</span>
              <span class="mistake-time">{{ formatTime(item.updated_at) }}</span>
            </router-link>
          </div>
          <div v-else class="empty-state compact">还没有错题笔记。</div>
        </section>

        <section class="section-panel">
          <div class="section-header">
            <h2>针对性练习推荐</h2>
            <span>按薄弱点匹配面经</span>
          </div>
          <div v-if="recommendations.length" class="recommend-list">
            <div v-for="group in recommendations" :key="group.keyword" class="recommend-group">
              <div class="recommend-keyword">{{ group.keyword }} · 出现 {{ group.count }} 次</div>
              <div v-if="group.experiences?.length" class="recommend-items">
                <router-link
                  v-for="exp in group.experiences"
                  :key="exp.id"
                  :to="`/experiences/${exp.id}`"
                  class="recommend-item"
                >
                  <span>{{ exp.company }} · {{ exp.position }}</span>
                  <strong>{{ exp.title }}</strong>
                </router-link>
              </div>
              <div v-else class="recommend-empty">暂无匹配面经</div>
            </div>
          </div>
          <div v-else class="empty-state compact">暂无推荐，先积累一些面试报告或错题笔记吧。</div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StarryBackground from '../components/StarryBackground.vue'
import { getMistakeDashboard, getWeaknessRecommendations } from '../api/learningNote'

const router = useRouter()
const loading = ref(true)
const error = ref('')
const dashboard = ref({})
const weakness = ref({})
const recommendations = ref([])

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [dashboardRes, recRes] = await Promise.all([
      getMistakeDashboard(),
      getWeaknessRecommendations(5),
    ])
    dashboard.value = dashboardRes || {}
    weakness.value = dashboardRes?.weakness || {}
    recommendations.value = recRes || []
  } catch (e) {
    error.value = e?.message || '加载错题仪表盘失败'
  } finally {
    loading.value = false
  }
}

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString('zh-CN')
}

onMounted(loadData)
</script>

<style scoped>
.mistake-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.page-header {
  max-width: 1040px;
  display: flex;
  align-items: center;
  gap: 18px;
  margin: 0 auto;
  padding: 34px 20px 18px;
}
.page-header h1 {
  margin: 0 0 6px;
  font-size: 28px;
  color: var(--text-primary);
}
.header-desc {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
}
.main-container {
  max-width: 1040px;
  margin: 0 auto;
  padding: 0 20px;
}
.back-btn,
.section-link,
.page-message button {
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.12);
  color: var(--accent-light);
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}
.back-btn {
  padding: 7px 14px;
}
.section-link,
.page-message button {
  padding: 6px 12px;
  font-size: 13px;
}
.back-btn:hover,
.section-link:hover,
.page-message button:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.45);
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
.error-message {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.14);
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.loading-state,
.empty-state {
  padding: 70px 20px;
  color: var(--text-muted);
  text-align: center;
}
.empty-state.compact {
  padding: 24px 12px;
  border: 1px dashed rgba(255,255,255,0.1);
  border-radius: 8px;
}
.stats-row {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-tile,
.section-panel {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
}
.stat-tile {
  padding: 16px;
}
.stat-tile.accent {
  background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(99,102,241,0.08));
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--accent-light);
}
.stat-value.text {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 18px;
}
.stat-label {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}
.section-panel {
  margin-top: 14px;
  padding: 18px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.section-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}
.section-header span {
  color: var(--text-muted);
  font-size: 13px;
}
.heatmap {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.heat-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgba(239,68,68,var(--heat));
  border-radius: 8px;
  background: rgba(239,68,68,var(--heat));
  color: var(--text-primary);
  cursor: default;
}
.heat-chip strong {
  color: #fecaca;
}
.mistake-list,
.recommend-list,
.recommend-items {
  display: grid;
  gap: 10px;
}
.mistake-item,
.recommend-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px;
  background: rgba(255,255,255,0.035);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
}
.mistake-item:hover,
.recommend-item:hover {
  border-color: rgba(99,102,241,0.35);
  background: rgba(99,102,241,0.08);
}
.mistake-title,
.recommend-item strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}
.mistake-tags,
.mistake-time,
.recommend-item span,
.recommend-empty {
  color: var(--text-muted);
  font-size: 12px;
}
.recommend-group {
  display: grid;
  gap: 8px;
}
.recommend-keyword {
  color: var(--accent-light);
  font-size: 13px;
  font-weight: 600;
}
@media (max-width: 768px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .stats-row,
  .mistake-item,
  .recommend-item {
    grid-template-columns: 1fr;
  }
}
</style>
