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
        <div class="stat-card">
          <div class="stat-icon">⭐</div>
          <div class="stat-value">{{ latestScore }}</div>
          <div class="stat-label">最近得分</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📈</div>
          <div class="stat-value" :class="improvementClass">{{ improvementText }}</div>
          <div class="stat-label">进步率</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">💡</div>
          <div class="stat-value weakest">{{ data.weakest_dimension || '-' }}</div>
          <div class="stat-label">薄弱维度</div>
        </div>
      </div>

      <!-- 分数趋势折线图 -->
      <div class="chart-section">
        <h2>分数趋势</h2>
        <div ref="trendChart" class="chart-container"></div>
      </div>

      <!-- 维度分析雷达图 -->
      <div v-if="Object.keys(data.dimension_avg).length > 0" class="chart-section">
        <h2>维度分析</h2>
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
  improvement_rate: 0,
  company_stats: [],
  position_stats: [],
  score_distribution: { low: 0, mid: 0, high: 0 },
  time_distribution: { weekday: 0, weekend: 0 },
  recent_activity: []
})
const loading = ref(true)

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
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}

function initTrendChart() {
  if (!trendChart.value || data.value.score_trend.length === 0) return
  const chart = echarts.init(trendChart.value)
  chartInstances.push(chart)

  const trend = data.value.score_trend
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 15, 25, 0.9)',
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
      max: 100,
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
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#7c3aed' },
          { offset: 1, color: '#6366f1' }
        ])
      },
      itemStyle: {
        color: '#7c3aed',
        borderWidth: 2,
        borderColor: '#fff'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(124, 58, 237, 0.3)' },
          { offset: 1, color: 'rgba(124, 58, 237, 0)' }
        ])
      }
    }]
  }
  chart.setOption(option)
}

function initRadarChart() {
  if (!radarChart.value || Object.keys(data.value.dimension_avg).length === 0) return
  const chart = echarts.init(radarChart.value)
  chartInstances.push(chart)

  const dims = Object.entries(data.value.dimension_avg)
  const option = {
    tooltip: {
      backgroundColor: 'rgba(15, 15, 25, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    radar: {
      indicator: dims.map(([name]) => ({ name, max: 100 })),
      shape: 'polygon',
      splitNumber: 4,
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
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(124, 58, 237, 0.4)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.1)' }
          ])
        },
        lineStyle: { color: '#7c3aed', width: 2 },
        itemStyle: { color: '#7c3aed' }
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
      backgroundColor: 'rgba(15, 15, 25, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'value',
      max: 100,
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
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: getScoreColor(s.avg_score) + '80' },
            { offset: 1, color: getScoreColor(s.avg_score) }
          ]),
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
      backgroundColor: 'rgba(15, 15, 25, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff' }
    },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'value',
      max: 100,
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
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#6366f180' },
            { offset: 1, color: '#6366f1' }
          ]),
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
      backgroundColor: 'rgba(15, 15, 25, 0.9)',
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
      itemStyle: { borderRadius: 8, borderColor: '#0f0f19', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: dist.high, name: '优秀 (80+)', itemStyle: { color: '#22c55e' } },
        { value: dist.mid, name: '良好 (60-80)', itemStyle: { color: '#f59e0b' } },
        { value: dist.low, name: '待提升 (<60)', itemStyle: { color: '#ef4444' } }
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
      backgroundColor: 'rgba(15, 15, 25, 0.9)',
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
      itemStyle: { borderRadius: 8, borderColor: '#0f0f19', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: time.weekday, name: '工作日', itemStyle: { color: '#6366f1' } },
        { value: time.weekend, name: '周末', itemStyle: { color: '#a78bfa' } }
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
      backgroundColor: 'rgba(15, 15, 25, 0.9)',
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
            ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#7c3aed' },
                { offset: 1, color: '#6366f1' }
              ])
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
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(124, 58, 237, 0.2);
  border-top-color: #7c3aed;
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
  transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-icon { font-size: 20px; margin-bottom: 6px; }
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
.stat-value.weakest { font-size: 14px; font-weight: 600; color: var(--amber); }
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
</style>
