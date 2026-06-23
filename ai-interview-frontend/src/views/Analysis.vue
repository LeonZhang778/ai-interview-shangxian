<template>
  <StarryBackground />
  <div class="analysis-page">
    <div class="page-header">
      <h1>面试分析</h1>
      <p class="subtitle">基于你的面试历史，分析优势与提升空间</p>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="data.total_interviews === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>暂无面试数据</p>
      <router-link to="/resume/upload" class="cta-link">开始第一次面试</router-link>
    </div>

    <template v-else>
      <!-- 概览卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-value">{{ data.total_interviews }}</div>
          <div class="stat-label">面试次数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ latestScore }}</div>
          <div class="stat-label">最近得分</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" :class="improvementClass">{{ improvementText }}</div>
          <div class="stat-label">进步率</div>
        </div>
        <div class="stat-card">
          <div class="stat-value weakest">{{ data.weakest_dimension || '-' }}</div>
          <div class="stat-label">薄弱维度</div>
        </div>
      </div>

      <!-- 分数趋势 -->
      <div class="chart-section">
        <h2>分数趋势</h2>
        <div class="trend-chart">
          <div class="chart-area">
            <div v-for="(point, idx) in data.score_trend" :key="idx" class="chart-bar-group">
              <div class="chart-bar-wrapper">
                <div
                  class="chart-bar"
                  :style="{ height: (point.score / 100 * 100) + '%' }"
                  :class="getScoreClass(point.score)"
                >
                  <span class="bar-label">{{ point.score }}</span>
                </div>
              </div>
              <div class="chart-x-label">{{ formatChartDate(point.date) }}</div>
              <div class="chart-position">{{ point.position }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 维度分析 -->
      <div v-if="Object.keys(data.dimension_avg).length > 0" class="chart-section">
        <h2>维度分析</h2>
        <div class="dimension-list">
          <div v-for="(score, dim) in data.dimension_avg" :key="dim" class="dimension-item">
            <div class="dim-header">
              <span class="dim-name">{{ dim }}</span>
              <span class="dim-score">{{ score }}</span>
            </div>
            <div class="dim-bar-bg">
              <div
                class="dim-bar"
                :style="{ width: (score / 100 * 100) + '%' }"
                :class="getScoreClass(score)"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getAnalysis } from '../api/interview'
import StarryBackground from '../components/StarryBackground.vue'

const data = ref({
  total_interviews: 0,
  completed_interviews: 0,
  score_trend: [],
  dimension_avg: {},
  weakest_dimension: null,
  improvement_rate: 0
})
const loading = ref(true)

const latestScore = computed(() => {
  const trend = data.value.score_trend
  return trend.length > 0 ? trend[trend.length - 1].score : '-'
})

const improvementText = computed(() => {
  const rate = data.value.improvement_rate
  if (rate > 0) return `+${(rate * 100).toFixed(0)}%`
  if (rate < 0) return `${(rate * 100).toFixed(0)}%`
  return '0%'
})

const improvementClass = computed(() => {
  const rate = data.value.improvement_rate
  if (rate > 0) return 'positive'
  if (rate < 0) return 'negative'
  return ''
})

function getScoreClass(score) {
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-mid'
  return 'score-low'
}

function formatChartDate(dateStr) {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return `${parts[1]}/${parts[2]}`
}

onMounted(async () => {
  try {
    data.value = await getAnalysis()
  } catch (e) {
    console.error('加载分析数据失败:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.analysis-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 20px;
  min-height: 100vh;
}
.page-header { margin-bottom: 24px; }
.page-header h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}
.subtitle { font-size: 14px; color: var(--text-muted); margin: 0; }

.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
  font-size: 15px;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { margin: 0 0 16px; }
.cta-link {
  display: inline-block;
  padding: 10px 24px;
  border-radius: 8px;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: white;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s;
}
.cta-link:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(124,58,237,0.3); }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}
.stat-value {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 4px;
  line-height: 1.2;
  word-break: break-all;
}
.stat-value.positive { color: #22c55e; }
.stat-value.negative { color: var(--red); }
.stat-value.weakest { font-size: 16px; font-weight: 600; color: var(--amber); }
.stat-label { font-size: 12px; color: var(--text-muted); }

.chart-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 20px;
}
.chart-section h2 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px;
}

.trend-chart { overflow-x: auto; }
.chart-area {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  min-height: 200px;
  padding-bottom: 50px;
  position: relative;
}
.chart-bar-group {
  flex: 1;
  min-width: 50px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}
.chart-bar-wrapper {
  width: 100%;
  height: 180px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.chart-bar {
  width: 70%;
  max-width: 48px;
  border-radius: 6px 6px 0 0;
  position: relative;
  transition: height 0.5s ease;
  min-height: 4px;
}
.chart-bar.score-high { background: linear-gradient(180deg, #22c55e, #16a34a); }
.chart-bar.score-mid { background: linear-gradient(180deg, #f59e0b, #d97706); }
.chart-bar.score-low { background: linear-gradient(180deg, #ef4444, #dc2626); }
.bar-label {
  position: absolute;
  top: -22px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
}
.chart-x-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 8px;
  text-align: center;
}
.chart-position {
  font-size: 10px;
  color: var(--text-dim);
  text-align: center;
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dimension-list { display: flex; flex-direction: column; gap: 14px; }
.dimension-item {}
.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.dim-name {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dim-score {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}
.dim-bar-bg {
  width: 100%;
  height: 8px;
  background: var(--bg-hover);
  border-radius: 4px;
  overflow: hidden;
}
.dim-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}
.dim-bar.score-high { background: linear-gradient(90deg, #22c55e, #16a34a); }
.dim-bar.score-mid { background: linear-gradient(90deg, #f59e0b, #d97706); }
.dim-bar.score-low { background: linear-gradient(90deg, #ef4444, #dc2626); }

@media (max-width: 640px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .stat-value { font-size: 22px; }
}
</style>
