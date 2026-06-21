<template>
  <div class="container">
    <div v-if="loading" class="loading">加载报告中...</div>

    <div v-else-if="report" style="max-width:700px;margin:30px auto">
      <!-- 总分 -->
      <div class="card score-card">
        <div class="score-circle">
          <span class="score-num">{{ data.overall_score }}</span>
          <span class="score-label">/10</span>
        </div>
        <div class="score-info">
          <h2>面试评估报告</h2>
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
        <h3 style="margin-bottom:12px">📊 各题得分</h3>
        <div v-for="(q, i) in report.question_scores" :key="i" class="q-score-item">
          <div class="q-score-header">
            <span class="q-index">Q{{ i + 1 }}</span>
            <span class="q-text">{{ q.question }}</span>
            <span class="q-score" :style="{ color: q.score >= 7 ? '#059669' : q.score >= 5 ? '#d97706' : '#dc2626' }">
              {{ q.score }}
            </span>
          </div>
          <div class="q-bar">
            <div class="q-bar-fill" :style="{ width: (q.score * 10) + '%', background: q.score >= 7 ? '#10b981' : q.score >= 5 ? '#f59e0b' : '#ef4444' }"></div>
          </div>
        </div>
      </div>

      <!-- 分享卡片（隐藏，用于截图） -->
      <div ref="shareCard" class="share-card" v-if="report">
        <div class="share-header">🎯 智面 AI 面试报告</div>
        <div class="share-score">{{ data.overall_score }}<span>/10</span></div>
        <div class="share-position">{{ data.target_position || '模拟面试' }}</div>
        <div class="share-rec" v-if="report.hire_recommendation">{{ report.hire_recommendation }}</div>
        <div class="share-footer">扫码免费体验 AI 模拟面试</div>
      </div>

      <!-- 操作 -->
      <div style="text-align:center;margin-top:24px;margin-bottom:40px">
        <button @click="handleShare" class="btn-share" style="padding:10px 24px;border-radius:8px;margin-right:12px">
          {{ shareStatus === 'generating' ? '生成中...' : shareStatus === 'done' ? '已复制到剪贴板' : '📸 分享报告' }}
        </button>
        <router-link to="/resume/upload" class="btn-primary" style="display:inline-block;padding:10px 24px;color:white;border-radius:8px;margin-right:12px">
          再来一次
        </router-link>
        <router-link to="/dashboard" class="btn-secondary" style="display:inline-block;padding:10px 24px;border-radius:8px">
          返回首页
        </router-link>
      </div>
    </div>

    <div v-else class="card" style="text-align:center;padding:60px;max-width:500px;margin:60px auto;color:var(--text-muted)">
      <p>报告加载失败</p>
      <router-link to="/dashboard" style="margin-top:12px;display:inline-block">返回首页</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getReport } from '../api/interview'

const route = useRoute()
const interviewId = route.params.id
const data = ref(null)
const report = ref(null)
const loading = ref(true)
const shareCard = ref(null)
const shareStatus = ref('idle')

onMounted(async () => {
  try {
    const res = await getReport(interviewId)
    data.value = res
    report.value = res.report || {}
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function handleShare() {
  if (shareStatus.value === 'generating') return
  shareStatus.value = 'generating'
  try {
    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(shareCard.value, {
      backgroundColor: '#4f46e5',
      scale: 2
    })
    canvas.toBlob(async (blob) => {
      try {
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
        shareStatus.value = 'done'
        setTimeout(() => { shareStatus.value = 'idle' }, 3000)
      } catch {
        // Clipboard API not supported, download instead
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'interview-report.png'
        a.click()
        URL.revokeObjectURL(url)
        shareStatus.value = 'done'
        setTimeout(() => { shareStatus.value = 'idle' }, 3000)
      }
    })
  } catch (e) {
    console.error(e)
    shareStatus.value = 'idle'
  }
}
</script>

<style scoped>
.loading {
  text-align: center;
  padding: 80px;
  color: var(--text-muted);
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
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 0 24px rgba(124,58,237,0.3);
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
  font-family: 'Space Grotesk', sans-serif;
  font-size: 20px;
  margin-bottom: 4px;
  color: var(--text-primary);
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
  background: rgba(139,92,246,0.1);
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

/* Share card */
.share-card {
  position: absolute;
  left: -9999px;
  top: 0;
  width: 360px;
  padding: 40px 30px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  text-align: center;
  border-radius: 16px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.share-header { font-size: 14px; opacity: 0.8; margin-bottom: 16px; }
.share-score { font-size: 64px; font-weight: 800; line-height: 1; margin-bottom: 8px; }
.share-score span { font-size: 24px; font-weight: 400; opacity: 0.6; }
.share-position { font-size: 16px; opacity: 0.9; margin-bottom: 12px; }
.share-rec { font-size: 14px; background: rgba(255,255,255,0.2); border-radius: 8px; padding: 6px 14px; display: inline-block; margin-bottom: 20px; }
.share-footer { font-size: 12px; opacity: 0.6; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 14px; margin-top: 10px; }

.btn-share {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: white;
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-share:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(245,158,11,0.4);
}
</style>
