<template>
  <StarryBackground />
  <div class="analysis-page">
    <div class="page-header">
      <h1>面试分析</h1>
      <p class="subtitle">基于你的面试历史，分析优势与提升空间</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="data.total_interviews === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>暂无面试数据</p>
      <router-link to="/resume/upload" class="cta-link">开始第一次面试</router-link>
    </div>

    <template v-else>
      <!-- 概览卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon">🎯</div>
          <div class="stat-value">{{ data.total_interviews }}</div>
          <div class="stat-label">面试次数</div>
        </div>
        <div class="stat-card clickable" @click="data.recent_scores?.length && (showRecentScoresModal = true)">
          <div class="stat-icon">⭐</div>
          <div class="stat-value">{{ latestScore }}</div>
          <div class="stat-label">最近得分<span v-if="data.recent_scores?.length > 1" class="hint">查看历史 ›</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📈</div>
          <div class="stat-value" :class="improvementClass">{{ improvementText }}</div>
          <div class="stat-label">进步率</div>
        </div>
        <div class="stat-card clickable" @click="data.weakest_dimension_details?.length && (showWeaknessModal = true)">
          <div class="stat-icon">💡</div>
          <div class="stat-value weakest">{{ data.weakest_dimension || '-' }}</div>
          <div class="stat-label">薄弱维度<span v-if="data.weakest_dimension_details?.length" class="hint">查看详情 ›</span></div>
        </div>
      </div>

      <!-- 分数趋势折线图 -->
      <div class="chart-section">
        <h2>分数趋势</h2>
        <div ref="trendChart" class="chart-container"></div>
      </div>

      <!-- 维度分析雷达图（精简：仅展示最薄弱 3 项 + 最强 1 项） -->
      <div v-if="Object.keys(data.dimension_avg).length > 0" class="chart-section">
        <h2>维度分析<span class="chart-hint">（重点维度）</span></h2>
        <div ref="radarChart" class="chart-container"></div>
      </div>

      <!-- 双列布局：公司统计 + 岗位统计 -->
      <div class="dual-chart-row">
        <div v-if="data.company_stats && data.company_stats.length > 0" class="chart-section">
          <h2>难度统计</h2>
          <div ref="companyChart" class="chart-container"></div>
        </div>
        <div v-if="data.position_stats && data.position_stats.length > 0" class="chart-section">
          <h2>岗位统计</h2>
          <div ref="positionChart" class="chart-container"></div>
        </div>
      </div>

      <!-- 双列布局：分数分布 + 时间分布 -->
      <div class="dual-chart-row">
        <div class="chart-section">
          <h2>分数分布</h2>
          <div ref="scoreDistChart" class="chart-container"></div>
        </div>
        <div class="chart-section">
          <h2>面试时间分布</h2>
          <div ref="timeDistChart" class="chart-container"></div>
        </div>
      </div>

      <!-- 最近活跃度 -->
      <div class="chart-section">
        <h2>最近 7 天活跃度</h2>
        <div ref="activityChart" class="chart-container"></div>
      </div>

      <!-- 薄弱维度详情弹窗 -->
      <div v-if="showWeaknessModal" class="modal-overlay" @click.self="showWeaknessModal = false">
        <div class="modal-box">
          <button class="modal-close" @click="showWeaknessModal = false">×</button>
          <h3>薄弱维度详情：{{ data.weakest_dimension }}</h3>
          <p class="modal-desc">该维度历史得分明细，点击可跳转到对应面试报告。</p>
          <div class="detail-list">
            <div v-for="(d, i) in data.weakest_dimension_details" :key="i" class="detail-item"
                 @click="d.interview_id && $router.push(`/report/${d.interview_id}`)">
              <span class="detail-score" :style="{ color: getScoreColor(d.score) }">{{ d.score }}</span>
              <span class="detail-info">
                <span class="detail-date">{{ d.date }}</span>
                <span class="detail-position" v-if="d.position">{{ d.position }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 最近得分历史弹窗 -->
      <div v-if="showRecentScoresModal" class="modal-overlay" @click.self="showRecentScoresModal = false">
        <div class="modal-box">
          <button class="modal-close" @click="showRecentScoresModal = false">×</button>
          <h3>最近得分历史</h3>
          <p class="modal-desc">最近 {{ data.recent_scores.length }} 次面试得分趋势。</p>
          <div class="detail-list">
            <div v-for="(s, i) in data.recent_scores" :key="i" class="detail-item">
              <span class="detail-score" :style="{ color: getScoreColor(s.score) }">{{ s.score }}</span>
              <span class="detail-info">
                <span class="detail-date">{{ s.date }}</span>
                <span class="detail-position" v-if="s.position">{{ s.position }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import { getAnalysis } from '../api/interview'
import StarryBackground from '../components/StarryBackground.vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, PieChart, RadarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  LineChart, BarChart, PieChart, RadarChart,
  TitleComponent, TooltipComponent, LegendComponent, GridComponent, RadarComponent,
  CanvasRenderer
])

const data = ref({
  total_interviews: 0,
  completed_interviews: 0,
  score_trend: [],
  dimension_avg: {},
  weakest_dimension: null,
  weakest_dimension_details: [],
  improvement_rate: 0,
  recent_scores: [],
  company_stats: [],
  position_stats: [],
  score_distribution: { low: 0, mid: 0, high: 0 },
  time_distribution: { weekday: 0, weekend: 0 },
  recent_activity: []
})
const loading = ref(true)
const showWeaknessModal = ref(false)
const showRecentScoresModal = ref(false)

// Chart refs
const trendChart = ref(null)
const radarChart = ref(null)
const companyChart = ref(null)
const positionChart = ref(null)
const scoreDistChart = ref(null)
const timeDistChart = ref(null)
const activityChart = ref(null)

let chartInstances = []

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

function getScoreColor(score) {
  if (score >= 8) return '#EDEDED'
  if (score >= 6) return '#A3A3A3'
  return '#737373'
}

function initTrendChart() {
  if (!trendChart.value || data.value.score_trend.length === 0) return
  const chart = echarts.init(trendChart.value)
  chartInstances.push(chart)

  const trend = data.value.score_trend
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 17, 17, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' },
      formatter: (params) => {
        const p = params[0]
        const item = trend[p.dataIndex]
        return `${p.axisValue}<br/>${item.company} - ${item.position}<br/>分数: <strong>${p.value}</strong>`
      }
    },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: trend.map(t => t.date.slice(5)),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 10,
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 }
    },
    series: [{
      type: 'line',
      data: trend.map(t => t.score),
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: {
        width: 3,
        color: '#A3A3A3'
      },
      itemStyle: {
        color: '#A3A3A3',
        borderWidth: 2,
        borderColor: '#fff'
      },
      areaStyle: {
        color: 'rgba(128, 128, 128, 0.12)'
      }
    }]
  }
  chart.setOption(option)
}

function initRadarChart() {
  if (!radarChart.value || Object.keys(data.value.dimension_avg).length === 0) return
  const chart = echarts.init(radarChart.value)
  chartInstances.push(chart)

  // 精简：只展示最薄弱 3 项 + 最强 1 项，突出重点而非密密麻麻全维度
  const allDims = Object.entries(data.value.dimension_avg)
  const sorted = [...allDims].sort((a, b) => a[1] - b[1])
  const weakest3 = sorted.slice(0, 3)
  const strongest1 = sorted.slice(-1)
  // 去重合并（维度少于 4 个时全展示）
  const seen = new Set()
  const focus = []
  for (const d of [...weakest3, ...strongest1]) {
    if (!seen.has(d[0])) { seen.add(d[0]); focus.push(d) }
  }
  const dims = allDims.length <= 4 ? allDims : focus

  const option = {
    tooltip: {
      backgroundColor: 'rgba(17, 17, 17, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    radar: {
      indicator: dims.map(([name]) => ({ name, max: 10 })),
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: 'rgba(255,255,255,0.7)',
        fontSize: 12
      },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: dims.map(([, score]) => score),
        areaStyle: {
          color: 'rgba(128, 128, 128, 0.16)'
        },
        lineStyle: { color: '#A3A3A3', width: 2 },
        itemStyle: { color: '#A3A3A3' }
      }]
    }]
  }
  chart.setOption(option)
}

function initCompanyChart() {
  if (!companyChart.value || data.value.company_stats.length === 0) return
  const chart = echarts.init(companyChart.value)
  chartInstances.push(chart)

  const stats = data.value.company_stats.slice(0, 8)
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 17, 17, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'value',
      max: 10,
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 }
    },
    yAxis: {
      type: 'category',
      data: stats.map(s => s.company),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: {
        color: 'rgba(255,255,255,0.7)',
        fontSize: 12,
        width: 60,
        overflow: 'truncate'
      }
    },
    series: [{
      type: 'bar',
      data: stats.map(s => ({
        value: s.avg_score,
        itemStyle: {
          color: getScoreColor(s.avg_score),
          borderRadius: [0, 4, 4, 0]
        }
      })),
      barWidth: 16,
      label: {
        show: true,
        position: 'right',
        color: 'rgba(255,255,255,0.7)',
        fontSize: 11,
        formatter: '{c}分'
      }
    }]
  }
  chart.setOption(option)
}

function initPositionChart() {
  if (!positionChart.value || data.value.position_stats.length === 0) return
  const chart = echarts.init(positionChart.value)
  chartInstances.push(chart)

  const stats = data.value.position_stats.slice(0, 8)
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 17, 17, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'value',
      max: 10,
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 }
    },
    yAxis: {
      type: 'category',
      data: stats.map(s => s.position),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: {
        color: 'rgba(255,255,255,0.7)',
        fontSize: 12,
        width: 60,
        overflow: 'truncate'
      }
    },
    series: [{
      type: 'bar',
      data: stats.map(s => ({
        value: s.avg_score,
        itemStyle: {
          color: '#A3A3A3',
          borderRadius: [0, 4, 4, 0]
        }
      })),
      barWidth: 16,
      label: {
        show: true,
        position: 'right',
        color: 'rgba(255,255,255,0.7)',
        fontSize: 11,
        formatter: '{c}分'
      }
    }]
  }
  chart.setOption(option)
}

function initScoreDistChart() {
  if (!scoreDistChart.value) return
  const chart = echarts.init(scoreDistChart.value)
  chartInstances.push(chart)

  const dist = data.value.score_distribution
  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(17, 17, 17, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    legend: {
      bottom: 10,
      textStyle: { color: 'rgba(255,255,255,0.7)', fontSize: 12 }
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#111111', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: dist.high, name: '优秀 (8+)', itemStyle: { color: '#EDEDED' } },
        { value: dist.mid, name: '良好 (6-8)', itemStyle: { color: '#A3A3A3' } },
        { value: dist.low, name: '待提升 (<6)', itemStyle: { color: '#737373' } }
      ]
    }]
  }
  chart.setOption(option)
}

function initTimeDistChart() {
  if (!timeDistChart.value) return
  const chart = echarts.init(timeDistChart.value)
  chartInstances.push(chart)

  const time = data.value.time_distribution
  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(17, 17, 17, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    legend: {
      bottom: 10,
      textStyle: { color: 'rgba(255,255,255,0.7)', fontSize: 12 }
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#111111', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: time.weekday, name: '工作日', itemStyle: { color: '#EDEDED' } },
        { value: time.weekend, name: '周末', itemStyle: { color: '#737373' } }
      ]
    }]
  }
  chart.setOption(option)
}

function initActivityChart() {
  if (!activityChart.value || data.value.recent_activity.length === 0) return
  const chart = echarts.init(activityChart.value)
  chartInstances.push(chart)

  const activity = data.value.recent_activity
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 17, 17, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: activity.map(a => a.date.slice(5)),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 }
    },
    series: [{
      type: 'bar',
      data: activity.map(a => ({
        value: a.count,
        itemStyle: {
          color: a.count > 0
            ? '#A3A3A3'
            : 'rgba(255,255,255,0.05)',
          borderRadius: [4, 4, 0, 0]
        }
      })),
      barWidth: 24
    }]
  }
  chart.setOption(option)
}

function handleResize() {
  chartInstances.forEach(chart => chart.resize())
}

onMounted(async () => {
  try {
    data.value = await getAnalysis()
  } catch (e) {
    console.error('加载分析数据失败:', e)
  } finally {
    loading.value = false
  }

  await nextTick()
  initTrendChart()
  initRadarChart()
  initCompanyChart()
  initPositionChart()
  initScoreDistChart()
  initTimeDistChart()
  initActivityChart()

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstances.forEach(chart => chart.dispose())
  chartInstances = []
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.analysis-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px;
  min-height: 100vh;
}
.page-header { margin-bottom: 24px; }
.page-header h1 {
  font-family: Inter, sans-serif;
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
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(128, 128, 128, 0.2);
  border-top-color: #A3A3A3;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { margin: 0 0 16px; }
.cta-link {
  display: inline-block;
  padding: 10px 24px;
  border-radius: 8px;
  background: var(--accent-primary); color: var(--bg-base);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s;
}
.cta-link:hover { transform: translateY(-2px); box-shadow: var(--shadow-sm); }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-icon { font-size: 20px; margin-bottom: 6px; }
.stat-value {
  font-family: Inter, sans-serif;
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 4px;
  line-height: 1.2;
  word-break: break-all;
}
.stat-value.positive { color: #A3A3A3; }
.stat-value.negative { color: var(--red); }
.stat-value.weakest { font-size: 14px; font-weight: 600; color: var(--amber); }
.stat-label { font-size: 12px; color: var(--text-muted); }

.chart-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.chart-section h2 {
  font-family: Inter, sans-serif;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px;
}
.chart-container {
  width: 100%;
  height: 300px;
}

.dual-chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 0;
}
.dual-chart-row .chart-section {
  margin-bottom: 20px;
}
.dual-chart-row .chart-container {
  height: 260px;
}

@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .stat-value { font-size: 22px; }
  .dual-chart-row { grid-template-columns: 1fr; }
}

/* 可点击卡片 */
.stat-card.clickable {
  cursor: pointer;
}
.stat-card.clickable:hover {
  border-color: rgba(128, 128, 128, 0.4);
  box-shadow: var(--shadow-sm);
}
.stat-label .hint {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  color: var(--text-muted, #9ca3af);
}
.chart-hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted, #9ca3af);
  margin-left: 6px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: none;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal-box {
  background: var(--bg-card, #141414);
  border: 1px solid var(--border-default, rgba(255,255,255,0.1));
  border-radius: 8px;
  padding: 24px;
  max-width: 480px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
}
.modal-box h3 {
  font-family: Inter, sans-serif;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}
.modal-desc {
  font-size: 13px;
  color: var(--text-muted, #9ca3af);
  margin: 0 0 16px;
}
.modal-close {
  position: absolute;
  top: 12px;
  right: 16px;
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-muted, #9ca3af);
  cursor: pointer;
  line-height: 1;
}
.modal-close:hover { color: var(--text-primary); }
.detail-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.detail-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(128, 128, 128, 0.04);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.detail-item:hover {
  background: rgba(128, 128, 128, 0.1);
}
.detail-score {
  font-family: Inter, sans-serif;
  font-size: 22px;
  font-weight: 800;
  min-width: 36px;
  text-align: center;
}
.detail-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-date {
  font-size: 13px;
  color: var(--text-primary);
}
.detail-position {
  font-size: 12px;
  color: var(--text-muted, #9ca3af);
}
</style>
