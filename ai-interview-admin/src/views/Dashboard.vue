<template>
  <div>
    <h1 style="font-size:22px;margin-bottom:24px;color:var(--admin-text-primary)">数据概览</h1>

    <div v-if="dashboardError" class="dashboard-alert" role="alert">
      <span>{{ dashboardError }}</span>
      <button type="button" class="retry-btn" @click="loadAnalytics">重试</button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="(s, i) in statCards" :key="i" :style="{ '--accent': s.color }">
        <div class="stat-num">{{ stats[s.key] ?? '—' }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- 活跃用户 & 访问量 -->
    <div class="active-row">
      <div class="active-card">
        <span class="active-num">{{ activeUsers.dau ?? '—' }}</span>
        <span class="active-label">日活用户 (DAU)</span>
      </div>
      <div class="active-card">
        <span class="active-num">{{ activeUsers.wau ?? '—' }}</span>
        <span class="active-label">周活用户 (WAU)</span>
      </div>
      <div class="active-card">
        <span class="active-num">{{ activeUsers.today_pv ?? '—' }}</span>
        <span class="active-label">今日 PV</span>
      </div>
      <div class="active-card">
        <span class="active-num">{{ activeUsers.today_uv ?? '—' }}</span>
        <span class="active-label">今日 UV</span>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3 class="chart-title">用户注册趋势（近30天）</h3>
        <div v-if="chartErrors.user" class="chart-state">{{ chartErrors.user }}</div>
        <div v-else ref="userChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3 class="chart-title">面试完成趋势（近30天）</h3>
        <div v-if="chartErrors.interview" class="chart-state">{{ chartErrors.interview }}</div>
        <div v-else ref="interviewChartRef" class="chart-box"></div>
      </div>
    </div>

    <!-- 浏览量趋势 + 地理分布 -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3 class="chart-title">每日浏览量趋势（近30天）</h3>
        <div v-if="chartErrors.pv" class="chart-state">{{ chartErrors.pv }}</div>
        <div v-else ref="pvChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3 class="chart-title">访客地理分布</h3>
        <div class="geo-row">
          <div class="geo-block">
            <h4 class="geo-subtitle">国家 Top 10</h4>
            <table>
              <thead><tr><th>#</th><th>国家</th><th>访问数</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in geo.top_countries" :key="r.name">
                  <td>{{ i + 1 }}</td>
                  <td>{{ r.name }}</td>
                  <td><span style="font-weight:700;color:var(--admin-primary)">{{ r.count }}</span></td>
                </tr>
                <tr v-if="!geo.top_countries.length"><td colspan="3" style="color:var(--admin-text-muted);text-align:center">暂无数据</td></tr>
              </tbody>
            </table>
          </div>
          <div class="geo-block">
            <h4 class="geo-subtitle">省份 Top 10</h4>
            <table>
              <thead><tr><th>#</th><th>省份</th><th>访问数</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in geo.top_provinces" :key="r.name">
                  <td>{{ i + 1 }}</td>
                  <td>{{ r.name }}</td>
                  <td><span style="font-weight:700;color:var(--admin-primary)">{{ r.count }}</span></td>
                </tr>
                <tr v-if="!geo.top_provinces.length"><td colspan="3" style="color:var(--admin-text-muted);text-align:center">暂无数据</td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="ip-stat">
          <span class="active-num">{{ geo.unique_ips ?? '—' }}</span>
          <span class="active-label">独立 IP 数</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { analyticsApi } from '../api'

const stats = ref({ total_users: null, total_interviews: null, total_experiences: null, total_images: null, today_new_users: null, today_interviews: null, completion_rate: null, average_score: null })
const activeUsers = ref({ dau: null, wau: null, today_pv: null, today_uv: null })
const geo = ref({ top_countries: [], top_provinces: [], unique_ips: null })
const dashboardError = ref('')
const chartErrors = ref({ user: '', interview: '', pv: '' })

const userChartRef = ref(null)
const interviewChartRef = ref(null)
const pvChartRef = ref(null)
let userChart = null
let interviewChart = null
let pvChart = null

const statCards = [
  { key: 'total_users', label: '注册用户', color: 'var(--admin-primary)' },
  { key: 'total_interviews', label: '面试总数', color: 'var(--admin-primary)' },
  { key: 'total_experiences', label: '面经数量', color: 'var(--admin-primary)' },
  { key: 'average_score', label: '平均分', color: 'var(--admin-primary)' },
]

function getAdminToken(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function initChart(el, labels, data) {
  const color = getAdminToken('--admin-primary')
  const chart = echarts.init(el)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11, rotate: 45 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      type: 'line',
      data: data,
      smooth: false,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color, width: 2 },
      itemStyle: { color },
      areaStyle: { color, opacity: 0.06 },
    }],
  })
  return chart
}

function disposeCharts() {
  userChart?.dispose()
  interviewChart?.dispose()
  pvChart?.dispose()
  userChart = null
  interviewChart = null
  pvChart = null
}

function normalizeTrend(result) {
  const labels = Array.isArray(result?.labels) ? result.labels : []
  const values = Array.isArray(result?.data) ? result.data : []
  return {
    labels,
    data: labels.map((_, index) => Number(values[index] ?? 0)),
  }
}

async function loadAnalytics() {
  dashboardError.value = ''
  chartErrors.value = { user: '', interview: '', pv: '' }
  disposeCharts()

  const results = await Promise.allSettled([
    analyticsApi.overview(),
    analyticsApi.userTrend(30),
    analyticsApi.interviewTrend(30),
    analyticsApi.pageviewTrend(30),
    analyticsApi.geoDistribution(),
    analyticsApi.activeUsers(),
  ])

  const [overview, userTrend, interviewTrend, pvTrend, geoData, active] = results
  const failedLabels = []
  const resolveResult = (result, label, fallback) => {
    if (result.status === 'fulfilled') return result.value ?? fallback
    failedLabels.push(label)
    return fallback
  }

  stats.value = {
    ...stats.value,
    ...resolveResult(overview, '概览统计', {}),
  }
  geo.value = resolveResult(geoData, '访客地理分布', geo.value)
  activeUsers.value = resolveResult(active, '活跃用户统计', activeUsers.value)

  const userSeries = normalizeTrend(resolveResult(userTrend, '用户注册趋势', {}))
  const interviewSeries = normalizeTrend(resolveResult(interviewTrend, '面试完成趋势', {}))
  const pvSeries = normalizeTrend(resolveResult(pvTrend, '浏览量趋势', {}))

  chartErrors.value = {
    user: userTrend.status === 'rejected' ? '用户注册趋势加载失败' : userSeries.labels.length ? '' : '暂无趋势数据',
    interview: interviewTrend.status === 'rejected' ? '面试完成趋势加载失败' : interviewSeries.labels.length ? '' : '暂无趋势数据',
    pv: pvTrend.status === 'rejected' ? '浏览量趋势加载失败' : pvSeries.labels.length ? '' : '暂无趋势数据',
  }

  if (failedLabels.length) {
    dashboardError.value = `部分统计数据加载失败：${failedLabels.join('、')}。其余数据仍可查看。`
  }

  await nextTick()
  if (!chartErrors.value.user && userChartRef.value) userChart = initChart(userChartRef.value, userSeries.labels, userSeries.data)
  if (!chartErrors.value.interview && interviewChartRef.value) interviewChart = initChart(interviewChartRef.value, interviewSeries.labels, interviewSeries.data)
  if (!chartErrors.value.pv && pvChartRef.value) pvChart = initChart(pvChartRef.value, pvSeries.labels, pvSeries.data)
}

onMounted(async () => {
  try {
    await loadAnalytics()
  } catch (e) {
    dashboardError.value = '统计数据加载失败，请稍后重试。'
  }
})

onBeforeUnmount(() => {
  disposeCharts()
})
</script>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }

.stat-card {
  background: var(--admin-bg-card);
  border-radius: var(--admin-radius-lg);
  padding: 24px;
  text-align: center;
  position: relative;
  overflow: hidden;
  transition: border-color 0.15s;
  border: 1px solid var(--admin-border);
  box-shadow: none;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--accent);
}
.stat-card:hover {
  transform: none;
  border-color: var(--admin-border-strong);
}
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-num { font-size: 40px; font-weight: 700; color: var(--accent); }
.stat-label { font-size: 14px; color: var(--admin-text-secondary); margin-top: 4px; }

.active-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.active-card {
  flex: 1;
  background: var(--admin-bg-card);
  border: 1px solid var(--admin-border);
  border-radius: var(--admin-radius-lg);
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: none;
}
.active-num { font-size: 36px; font-weight: 700; color: var(--admin-primary); }
.active-label { font-size: 14px; color: var(--admin-text-secondary); }

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}
.chart-card {
  background: var(--admin-bg-card);
  border: 1px solid var(--admin-border);
  border-radius: var(--admin-radius-lg);
  padding: 20px;
  box-shadow: none;
}
.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--admin-text-primary);
  margin-bottom: 12px;
}
.chart-box { width: 100%; height: 260px; }
.chart-state {
  height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--admin-text-muted);
  font-size: 14px;
  border: 1px dashed var(--admin-border);
  border-radius: var(--admin-radius-md);
}

.dashboard-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: -8px 0 20px;
  padding: 10px 12px;
  color: var(--admin-text-secondary);
  background: var(--admin-bg-muted);
  border: 1px solid var(--admin-border);
  border-radius: var(--admin-radius-md);
  font-size: 13px;
}

.retry-btn {
  flex: 0 0 auto;
  padding: 5px 12px;
  color: var(--admin-primary-contrast);
  background: var(--admin-primary);
  border-color: var(--admin-primary);
}

.geo-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.geo-block h4.geo-subtitle {
  font-size: 13px;
  font-weight: 600;
  color: var(--admin-text-secondary);
  margin: 0 0 8px;
}
.ip-stat {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--admin-border);
}

table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 8px 12px;
  text-align: left;
  font-size: 13px;
  border-bottom: 1px solid var(--admin-border);
}
th {
  font-weight: 600;
  color: var(--admin-text-secondary);
  font-size: 12px;
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .active-row { flex-direction: column; }
  .geo-row { grid-template-columns: 1fr; }
}
</style>
