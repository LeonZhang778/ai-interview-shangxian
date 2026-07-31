<template>
  <div>
    <h1 style="font-size:22px;margin-bottom:24px;color:#1e293b">📊 数据概览</h1>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="(s, i) in statCards" :key="i" :style="{ '--accent': s.color, '--glow': s.glow }">
        <div class="stat-icon">{{ s.icon }}</div>
        <div class="stat-num">{{ stats[s.key] }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- 活跃用户 & 访问量 -->
    <div class="active-row">
      <div class="active-card">
        <span class="active-num">{{ activeUsers.dau }}</span>
        <span class="active-label">日活用户 (DAU)</span>
      </div>
      <div class="active-card">
        <span class="active-num">{{ activeUsers.wau }}</span>
        <span class="active-label">周活用户 (WAU)</span>
      </div>
      <div class="active-card">
        <span class="active-num">{{ activeUsers.today_pv }}</span>
        <span class="active-label">今日 PV</span>
      </div>
      <div class="active-card">
        <span class="active-num">{{ activeUsers.today_uv }}</span>
        <span class="active-label">今日 UV</span>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3 class="chart-title">用户注册趋势（近30天）</h3>
        <div ref="userChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3 class="chart-title">面试完成趋势（近30天）</h3>
        <div ref="interviewChartRef" class="chart-box"></div>
      </div>
    </div>

    <!-- 浏览量趋势 + 地理分布 -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3 class="chart-title">每日浏览量趋势（近30天）</h3>
        <div ref="pvChartRef" class="chart-box"></div>
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
                  <td><span style="font-weight:700;color:#6366f1">{{ r.count }}</span></td>
                </tr>
                <tr v-if="!geo.top_countries.length"><td colspan="3" style="color:#94a3b8;text-align:center">暂无数据</td></tr>
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
                  <td><span style="font-weight:700;color:#8b5cf6">{{ r.count }}</span></td>
                </tr>
                <tr v-if="!geo.top_provinces.length"><td colspan="3" style="color:#94a3b8;text-align:center">暂无数据</td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="ip-stat">
          <span class="active-num">{{ geo.unique_ips }}</span>
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

const stats = ref({ total_users: 0, total_interviews: 0, total_experiences: 0, total_images: 0, today_new_users: 0, today_interviews: 0, completion_rate: 0, average_score: 0 })
const activeUsers = ref({ dau: 0, wau: 0, today_pv: 0, today_uv: 0 })
const geo = ref({ top_countries: [], top_provinces: [], unique_ips: 0 })

const userChartRef = ref(null)
const interviewChartRef = ref(null)
const pvChartRef = ref(null)
let userChart = null
let interviewChart = null
let pvChart = null

const statCards = [
  { key: 'total_users', label: '注册用户', icon: '👥', color: '#6366f1', glow: 'rgba(99,102,241,0.3)' },
  { key: 'total_interviews', label: '面试总数', icon: '🎤', color: '#8b5cf6', glow: 'rgba(139,92,246,0.3)' },
  { key: 'total_experiences', label: '面经数量', icon: '📝', color: '#06b6d4', glow: 'rgba(6,182,212,0.3)' },
  { key: 'average_score', label: '平均分', icon: '⭐', color: '#10b981', glow: 'rgba(16,185,129,0.3)' },
]

function initChart(el, labels, data, color) {
  const chart = echarts.init(el)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11, rotate: 45 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color, width: 2 },
      itemStyle: { color },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: color + '40' },
        { offset: 1, color: color + '05' },
      ]) },
    }],
  })
  return chart
}

onMounted(async () => {
  try {
    const [overview, userTrend, interviewTrend, pvTrend, geoData, active] = await Promise.all([
      analyticsApi.overview(),
      analyticsApi.userTrend(30),
      analyticsApi.interviewTrend(30),
      analyticsApi.pageviewTrend(30),
      analyticsApi.geoDistribution(),
      analyticsApi.activeUsers(),
    ])
    stats.value = overview
    geo.value = geoData
    activeUsers.value = active

    await nextTick()
    if (userChartRef.value) userChart = initChart(userChartRef.value, userTrend.labels, userTrend.data, '#6366f1')
    if (interviewChartRef.value) interviewChart = initChart(interviewChartRef.value, interviewTrend.labels, interviewTrend.data, '#06b6d4')
    if (pvChartRef.value) pvChart = initChart(pvChartRef.value, pvTrend.labels, pvTrend.data, '#f59e0b')
  } catch (e) { console.error(e) }
})

onBeforeUnmount(() => {
  userChart?.dispose()
  interviewChart?.dispose()
  pvChart?.dispose()
})
</script>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }

.stat-card {
  background: white;
  border-radius: 14px;
  padding: 28px 24px;
  text-align: center;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px var(--glow);
}
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-num { font-size: 40px; font-weight: 700; color: var(--accent); }
.stat-label { font-size: 14px; color: #6b7280; margin-top: 4px; }

.active-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.active-card {
  flex: 1;
  background: white;
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.active-num { font-size: 36px; font-weight: 700; color: #f59e0b; }
.active-label { font-size: 14px; color: #6b7280; }

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}
.chart-card {
  background: white;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}
.chart-box { width: 100%; height: 260px; }

.geo-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.geo-block h4.geo-subtitle {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 8px;
}
.ip-stat {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f1f5f9;
}

table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 8px 12px;
  text-align: left;
  font-size: 13px;
  border-bottom: 1px solid #f1f5f9;
}
th {
  font-weight: 600;
  color: #6b7280;
  font-size: 12px;
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .active-row { flex-direction: column; }
  .geo-row { grid-template-columns: 1fr; }
}
</style>
