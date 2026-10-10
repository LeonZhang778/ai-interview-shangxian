<template>
  <StarryBackground />
  <div class="container">
    <div v-if="loading" class="loading">加载报告中...</div>

    <div v-else-if="report" style="max-width:700px;margin:30px auto">
      <!-- 头部提示 -->
      <div class="share-banner">
        <span class="banner-icon"><BaseIcon name="link" :size="16" /></span>
        <span>这是来自 <strong>智面AI</strong> 的面试报告分享</span>
      </div>

      <!-- 总分 -->
      <div class="card score-card">
        <div class="score-circle">
          <span class="score-num">{{ data.overall_score }}</span>
          <span class="score-label">/10</span>
        </div>
        <div class="score-info">
          <h2>面试评估报告</h2>
          <p class="position" v-if="data.target_position">{{ data.target_position }}</p>
          <p class="hire-rec" v-if="report.hire_recommendation">
            {{ report.hire_recommendation }}
          </p>
        </div>
      </div>

      <!-- 总结 -->
      <div class="card" style="margin-top:16px" v-if="report.summary">
        <h3 style="margin-bottom:10px;color:var(--accent-light)">总体评价</h3>
        <p style="font-size:14px;line-height:1.8;color:var(--text-secondary)">{{ report.summary }}</p>
      </div>

      <!-- 优势 & 不足 -->
      <div class="two-col" style="margin-top:16px">
        <div class="card" v-if="report.strengths?.length">
          <h3 style="margin-bottom:10px;color:var(--green)">优势</h3>
          <ul>
            <li v-for="(s, i) in report.strengths" :key="i">{{ s }}</li>
          </ul>
        </div>
        <div class="card" v-if="report.weaknesses?.length">
          <h3 style="margin-bottom:10px;color:var(--red)">不足</h3>
          <ul>
            <li v-for="(w, i) in report.weaknesses" :key="i">{{ w }}</li>
          </ul>
        </div>
      </div>

      <!-- 建议 -->
      <div class="card" style="margin-top:16px" v-if="report.suggestions?.length">
        <h3 style="margin-bottom:10px;color:var(--accent-light)">改进建议</h3>
        <ul>
          <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
        </ul>
      </div>

      <!-- 各题得分 -->
      <div class="card" style="margin-top:16px" v-if="report.question_scores?.length">
        <h3 style="margin-bottom:12px"><BaseIcon name="chart" :size="16" /> 各题得分</h3>
        <div v-for="(q, i) in report.question_scores" :key="i" class="q-score-item">
          <div class="q-score-header">
            <span class="q-index">Q{{ i + 1 }}</span>
            <span class="q-text">{{ q.question }}</span>
            <span class="q-score" :style="{ color: q.score >= 7 ? 'var(--state-success)' : q.score >= 5 ? 'var(--state-warning)' : 'var(--state-error)' }">
              {{ q.score }}
            </span>
          </div>
          <div class="q-bar">
            <div class="q-bar-fill" :style="{ width: (q.score * 10) + '%', background: q.score >= 7 ? 'var(--state-success)' : q.score >= 5 ? 'var(--state-warning)' : 'var(--state-error)' }"></div>
          </div>
        </div>
      </div>

      <!-- CTA引导 -->
      <div class="card cta-card" style="margin-top:24px;margin-bottom:40px">
        <h3 style="margin-bottom:8px;color:var(--text-primary)"><BaseIcon name="target" :size="16" /> 也想试试 AI 模拟面试？</h3>
        <p style="font-size:14px;color:var(--text-muted);margin-bottom:16px">上传简历，AI 为你量身定制面试题，实时评估你的表现</p>
        <router-link to="/register" class="btn-cta">免费开始面试</router-link>
      </div>
    </div>

    <div v-else class="card" style="text-align:center;padding:60px;max-width:500px;margin:60px auto;color:var(--text-muted)">
        <p style="font-size:40px;margin-bottom:16px"><BaseIcon name="link" :size="40" /></p>
      <p style="font-size:16px;margin-bottom:8px">分享链接无效或已失效</p>
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:20px">该分享可能已被取消或链接不正确</p>
      <router-link to="/" style="display:inline-block;padding:10px 24px;background: var(--accent-primary); color: var(--bg-base);border-radius:8px;text-decoration:none">
        前往智面AI
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getSharedReport } from '../api/interview'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'

const route = useRoute()
const shareToken = route.params.token
const data = ref(null)
const report = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await getSharedReport(shareToken)
    data.value = res
    report.value = res.report || {}
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.loading {
  text-align: center;
  padding: 80px;
  color: var(--text-muted);
}
.share-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(128, 128, 128, 0.1);
  border: 1px solid rgba(128, 128, 128, 0.2);
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 13px;
  color: var(--text-secondary);
}
.banner-icon {
  font-size: 16px;
}
.score-card {
  display: flex;
  align-items: center;
  gap: 24px;
}
.score-circle {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  background: var(--accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}
.score-num {
  font-size: 32px;
  font-weight: 700;
  color: white;
}
.score-label {
  font-size: 14px;
  color: rgba(255,255,255,0.7);
}
.score-info h2 {
  font-family: Inter, sans-serif;
  font-size: 20px;
  margin-bottom: 4px;
  color: var(--text-primary);
}
.position {
  font-size: 14px;
  color: var(--accent-purple);
  margin-bottom: 4px;
}
.hire-rec {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 4px;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 520px) {
  .two-col { grid-template-columns: 1fr; }
}
ul {
  list-style: none;
  padding: 0;
}
ul li {
  font-size: 14px;
  line-height: 1.8;
  padding-left: 16px;
  position: relative;
  color: var(--text-secondary);
}
ul li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--text-muted);
}
.q-score-item {
  margin-bottom: 14px;
}
.q-score-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--text-primary);
}
.q-index {
  background: rgba(128, 128, 128,0.1);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 12px;
  color: var(--accent-purple);
}
.q-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.q-score {
  font-weight: 700;
  font-size: 16px;
  color: var(--text-primary);
}
.q-bar {
  height: 6px;
  background: var(--bg-hover);
  border-radius: 3px;
  overflow: hidden;
}
.q-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

/* CTA */
.cta-card {
  text-align: center;
  background: var(--bg-surface);
  border: 1px solid rgba(128, 128, 128, 0.2);
}
.btn-cta {
  display: inline-block;
  padding: 12px 32px;
  background: var(--accent-primary); color: var(--bg-base);
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s;
}
.btn-cta:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}
</style>
