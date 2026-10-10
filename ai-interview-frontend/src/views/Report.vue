<template>
  <StarryBackground />
  <div class="container">
    <div v-if="loading" class="loading">加载报告中...</div>

    <!-- 报告已改为后台生成：未就绪时给出明确状态与重试入口。
         以前这里是 `v-else-if="report"`，而 report 被赋成 {}（空对象为真值），
         于是报告还没生成完也会渲染出一个「什么都没有」的空报告页 —— 看起来像丢数据。 -->
    <div v-else-if="reportStatus !== 'ready'" class="report-pending">
      <template v-if="reportStatus === 'failed' || pollTimedOut">
        <p class="status-title">
          {{ reportStatus === 'failed' ? '报告生成失败' : '报告生成时间较长' }}
        </p>
        <p class="status-hint">
          {{
            reportStatus === 'failed'
              ? '多半是生成时服务抖动了一下，重新生成通常就能拿到。'
              : '可能是任务排队或服务繁忙，可以重新生成一次。'
          }}
        </p>
        <button class="btn-generate" :disabled="regenerating" @click="handleRegenerate">
          {{ regenerating ? '正在重新生成...' : '重新生成报告' }}
        </button>
      </template>
      <template v-else>
        <p class="status-title">
          <span class="poll-spinner"></span>
          报告生成中<span class="dots"></span>
        </p>
        <p class="status-hint">面试刚结束，正在为你撰写评估报告，通常需要几十秒。</p>
        <p class="status-hint">这个页面会自动刷新，不用一直等着。</p>
      </template>
    </div>

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
            <span class="q-score" :style="{ color: q.score >= 7 ? 'var(--state-success)' : q.score >= 5 ? 'var(--state-warning)' : 'var(--state-error)' }">
              {{ q.score }}
            </span>
          </div>
          <div class="q-bar">
            <div class="q-bar-fill" :style="{ width: (q.score * 10) + '%', background: q.score >= 7 ? 'var(--state-success)' : q.score >= 5 ? 'var(--state-warning)' : 'var(--state-error)' }"></div>
          </div>
        </div>
      </div>

      <!-- 分享链接面板 -->
      <div class="card share-link-panel" style="margin-top:16px">
        <h3 style="margin-bottom:12px;color:var(--accent-light)">🔗 分享报告</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:14px">生成分享链接，发给朋友查看你的面试表现</p>

        <div v-if="isShared && shareToken" class="share-link-box">
          <div class="share-link-url">
            <input :value="shareUrl" readonly class="share-input" />
            <button @click="copyShareLink" class="btn-copy" :class="{ copied: copyStatus === 'done' }">
              {{ copyStatus === 'done' ? '已复制' : '复制' }}
            </button>
          </div>
          <button @click="handleUnshare" class="btn-unshare">取消分享</button>
        </div>

        <button v-else @click="handleShareLink" class="btn-generate" :disabled="shareLinkStatus === 'loading'">
          {{ shareLinkStatus === 'loading' ? '生成中...' : '生成分享链接' }}
        </button>
      </div>

      <!-- 保存到学习笔记 -->
      <div class="card save-note-panel" style="margin-top:16px">
        <h3 style="margin-bottom:12px;color:var(--accent-light)">📝 保存到学习笔记</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:14px">
          将本次面试结果自动生成复盘笔记草稿，含逐题记录、错题标记和 AI 改进建议
        </p>
        <button @click="handleSaveToNote" class="btn-generate" :disabled="noteStatus === 'loading'">
          {{ noteStatus === 'loading' ? '生成中...' : '生成学习笔记' }}
        </button>
        <p v-if="noteMessage" :class="['note-msg', noteMessageType]">{{ noteMessage }}</p>
      </div>

      <!-- 相关笔记推荐 -->
      <div class="card recommend-note-panel" style="margin-top:16px" v-if="recommendNotes.length">
        <h3 style="margin-bottom:12px;color:var(--accent-light)">相关笔记推荐</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:14px">
          根据本次报告的薄弱点，推荐你已经沉淀过的相关笔记
        </p>
        <div class="recommend-note-list">
          <button
            v-for="note in recommendNotes"
            :key="note.id"
            type="button"
            class="recommend-note-item"
            @click="router.push(`/learning-notes/${note.id}`)"
          >
            <span>{{ note.title }}</span>
            <small>{{ note.tags || typeLabel(note.note_type) }}</small>
          </button>
        </div>
      </div>

      <!-- 操作 -->
      <div style="text-align:center;margin-top:24px;margin-bottom:40px">
        <button @click.stop="handleExportDocx" class="btn-export-docx" style="padding:10px 24px;border-radius:8px;margin-right:12px" :disabled="exportStatus === 'loading'">
          {{ exportStatus === 'loading' ? '导出中...' : '导出 Word' }}
        </button>
        <button @click.stop="handleShowQRCode" class="btn-share" style="padding:10px 24px;border-radius:8px;margin-right:12px" :disabled="shareStatus === 'generating'">
          {{ shareStatus === 'generating' ? '生成中...' : '生成二维码分享' }}
        </button>
        <router-link to="/resume/upload" class="btn-primary" style="display:inline-block;padding:10px 24px;color:white;border-radius:8px;margin-right:12px">
          再来一次
        </router-link>
        <router-link to="/dashboard" class="btn-secondary" style="display:inline-block;padding:10px 24px;border-radius:8px">
          返回首页
        </router-link>
        <p v-if="exportMessage" :class="['note-msg', exportMessageType]">{{ exportMessage }}</p>
      </div>

      <!-- 二维码分享弹窗 -->
      <Teleport to="body">
        <div v-if="qrCodeDataUrl" class="preview-overlay" @click.self="closeQRCode">
          <div class="preview-modal qrcode-modal">
            <div class="preview-header">
              <span>扫码查看报告</span>
              <button class="preview-close" @click="closeQRCode">&times;</button>
            </div>
            <div class="preview-body">
              <img :src="qrCodeDataUrl" class="qrcode-img" alt="报告分享二维码" />
            </div>
            <div class="preview-footer">
              <a :href="qrCodeDataUrl" download="interview-report-qrcode.png" class="btn-primary" style="display:block;padding:10px 20px;color:white;border-radius:8px;text-decoration:none;font-size:14px;text-align:center">下载二维码</a>
            </div>
          </div>
        </div>
      </Teleport>
    </div>

    <div v-else class="card" style="text-align:center;padding:60px;max-width:500px;margin:60px auto;color:var(--text-muted)">
      <p>报告加载失败</p>
      <router-link to="/dashboard" style="margin-top:12px;display:inline-block">返回首页</router-link>
    </div>
  </div>
</template>

<script setup>
import QRCode from 'qrcode'
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReport, shareInterview, unshareInterview, exportReportDocx, regenerateReport } from '../api/interview'
import { generateFromInterview, recommendForInterview } from '../api/learningNote'
import StarryBackground from '../components/StarryBackground.vue'

const route = useRoute()
const router = useRouter()
const interviewId = route.params.id
const data = ref(null)
const report = ref(null)
const loading = ref(true)
const qrCodeDataUrl = ref(null)
const shareStatus = ref('idle')
const shareLinkStatus = ref('idle')
const shareToken = ref(null)
const isShared = ref(false)
const copyStatus = ref('idle')
const noteStatus = ref('idle')
const noteMessage = ref('')
const noteMessageType = ref('')
const exportStatus = ref('idle')
const exportMessage = ref('')
const exportMessageType = ref('')
const recommendNotes = ref([])

// 报告就绪状态：报告已改为后台生成，进到本页时可能还在生成中。
// 未就绪时不再渲染空报告，而是显示状态并轮询，直到 ready 或 failed。
const reportStatus = ref('ready')
const regenerating = ref(false)
const pollTimedOut = ref(false)

const REPORT_POLL_INTERVAL_MS = 3000
// 约 2 分钟。超时后仍留在“生成中”界面但给出人工重试入口 ——
// 后端对重新生成有节流，重复请求不会造成任务风暴。
const REPORT_POLL_MAX_TICKS = 40
let reportPollTimer = null
let reportPollTicks = 0

function stopReportPolling() {
  if (reportPollTimer) {
    clearInterval(reportPollTimer)
    reportPollTimer = null
  }
}

function startReportPolling() {
  if (reportPollTimer) return
  reportPollTicks = 0
  pollTimedOut.value = false
  reportPollTimer = setInterval(async () => {
    reportPollTicks += 1
    if (reportPollTicks > REPORT_POLL_MAX_TICKS) {
      stopReportPolling()
      pollTimedOut.value = true
      return
    }
    try {
      const res = await getReport(interviewId)
      data.value = res
      reportStatus.value = res.report_status || 'ready'
      if (reportStatus.value === 'ready') {
        report.value = res.report || {}
        stopReportPolling()
        await loadRecommendNotes()
      }
    } catch (e) {
      console.error('轮询报告状态失败:', e)
    }
  }, REPORT_POLL_INTERVAL_MS)
}

async function handleRegenerate() {
  if (regenerating.value) return
  regenerating.value = true
  try {
    await regenerateReport(interviewId)
    reportStatus.value = 'pending'
    startReportPolling()
  } catch (e) {
    console.error('重新生成报告失败:', e)
    exportMessage.value = '重新生成失败：' + (e.message || '请稍后再试')
    exportMessageType.value = 'error'
  } finally {
    regenerating.value = false
  }
}

async function loadReport() {
  const res = await getReport(interviewId)
  data.value = res
  reportStatus.value = res.report_status || 'ready'
  if (reportStatus.value === 'ready') {
    report.value = res.report || {}
    await loadRecommendNotes()
    // 如果已有分享token
    if (res.share_token) {
      shareToken.value = res.share_token
      isShared.value = true
    }
  } else {
    report.value = null
    startReportPolling()
  }
}

const shareUrl = computed(() => {
  if (!shareToken.value) return ''
  return `${window.location.origin}/shared/${shareToken.value}`
})

onMounted(async () => {
  try {
    await loadReport()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

onUnmounted(stopReportPolling)

function typeLabel(type) {
  const map = { review: '复盘', mistake: '错题', experience: '面经', material: '资料', note: '笔记' }
  return map[type] || '笔记'
}

async function loadRecommendNotes() {
  const keywords = [
    ...(report.value?.weaknesses || []),
    ...(report.value?.suggestions || []),
  ].slice(0, 8)
  if (!keywords.length) return
  try {
    const res = await recommendForInterview(keywords, 5)
    recommendNotes.value = res.items || []
  } catch (e) {
    console.error('加载相关笔记推荐失败', e)
  }
}

async function handleShowQRCode() {
  if (shareStatus.value === 'generating') return
  shareStatus.value = 'generating'
  try {
    let token = shareToken.value
    // 二维码分享需要公开 token 才能让对方扫码访问；没有就先创建。
    // 注意：这里不写回 shareToken/isShared —— 「分享链接」面板有独立的显式开关，
    // 用户没点那边就不该被这边的操作隐式改成「已分享」。
    if (!token) {
      const res = await shareInterview(interviewId)
      token = res.share_token
    }

    qrCodeDataUrl.value = await QRCode.toDataURL(`${window.location.origin}/shared/${token}`, {
      width: 480,
      margin: 2,
      errorCorrectionLevel: 'H',
      color: { dark: '#141414', light: '#ffffff' }
    })
    shareStatus.value = 'idle'
  } catch (e) {
    console.error(e)
    shareStatus.value = 'idle'
  }
}

function closeQRCode() {
  qrCodeDataUrl.value = null
}

async function handleShareLink() {
  if (shareLinkStatus.value === 'loading') return
  shareLinkStatus.value = 'loading'
  try {
    const res = await shareInterview(interviewId)
    shareToken.value = res.share_token
    isShared.value = true
    shareLinkStatus.value = 'done'
  } catch (e) {
    console.error(e)
    shareLinkStatus.value = 'idle'
  }
}

async function handleUnshare() {
  try {
    await unshareInterview(interviewId)
    shareToken.value = null
    isShared.value = false
  } catch (e) {
    console.error(e)
  }
}

async function copyShareLink() {
  if (!shareUrl.value) return
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    copyStatus.value = 'done'
    setTimeout(() => { copyStatus.value = 'idle' }, 2000)
  } catch {
    // Fallback
    const input = document.createElement('input')
    input.value = shareUrl.value
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    copyStatus.value = 'done'
    setTimeout(() => { copyStatus.value = 'idle' }, 2000)
  }
}

async function handleSaveToNote() {
  if (noteStatus.value === 'loading') return
  noteStatus.value = 'loading'
  noteMessage.value = ''
  try {
    const res = await generateFromInterview({
      interview_id: interviewId,
      note_type: 'review',
    })
    noteMessage.value = res.message || '学习笔记草稿已生成'
    noteMessageType.value = 'success'
    // 若返回笔记 id，3 秒后跳转或保留查看链接
    if (res.id) {
      setTimeout(() => {
        router.push(`/learning-notes/${res.id}`)
      }, 1500)
    }
  } catch (e) {
    noteMessage.value = e.response?.data?.detail || '生成失败，请重试'
    noteMessageType.value = 'error'
  } finally {
    noteStatus.value = 'idle'
  }
}

async function handleExportDocx() {
  if (exportStatus.value === 'loading') return
  exportStatus.value = 'loading'
  exportMessage.value = ''
  try {
    await exportReportDocx(interviewId)
    exportMessage.value = 'Word 报告已开始下载'
    exportMessageType.value = 'success'
  } catch (e) {
    exportMessage.value = e.message || '导出失败，请稍后重试'
    exportMessageType.value = 'error'
  } finally {
    exportStatus.value = 'idle'
  }
}
</script>

<style scoped>
.loading {
  text-align: center;
  padding: 80px;
  color: var(--text-muted);
}

/* 报告生成中 / 生成失败：把状态说清楚，并给一个明确的动作 */
.report-pending {
  max-width: 480px;
  margin: 90px auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.status-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.status-hint { font-size: 13px; color: var(--text-muted); margin: 0; line-height: 1.7; }
.poll-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid var(--border-default);
  border-top-color: var(--accent-primary);
  animation: poll-spin .8s linear infinite;
}
@keyframes poll-spin { to { transform: rotate(360deg); } }
.dots::after { content: ''; animation: poll-dots 1.5s steps(4, end) infinite; }
@keyframes poll-dots {
  0% { content: ''; }
  25% { content: '.'; }
  50% { content: '..'; }
  75% { content: '...'; }
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

.btn-share {
  background: var(--accent-primary); color: var(--bg-base);
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-share:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.btn-export-docx {
  background: var(--accent-primary); color: var(--bg-base);
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-export-docx:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.btn-export-docx:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Share link panel */
.share-link-panel {
  background: rgba(128, 128, 128, 0.08);
  border: 1px solid rgba(128, 128, 128, 0.2);
}
.share-link-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.share-link-url {
  display: flex;
  gap: 8px;
}
.share-input {
  flex: 1;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
.btn-copy {
  padding: 10px 18px;
  background: rgba(128, 128, 128, 0.3);
  border: 1px solid rgba(128, 128, 128, 0.5);
  border-radius: 8px;
  color: var(--accent-light);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.btn-copy:hover {
  background: rgba(128, 128, 128, 0.5);
}
.btn-copy.copied {
  background: rgba(128, 128, 128, 0.3);
  border-color: rgba(128, 128, 128, 0.5);
  color: #A3A3A3;
}
.btn-unshare {
  align-self: flex-end;
  padding: 6px 14px;
  background: transparent;
  border: 1px solid rgba(128, 128, 128, 0.3);
  border-radius: 6px;
  color: #A3A3A3;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-unshare:hover {
  background: rgba(128, 128, 128, 0.1);
}
.btn-generate {
  padding: 12px 24px;
  background: var(--accent-primary);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-generate:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 保存到学习笔记 */
.save-note-panel {
  margin-top: 16px;
}
.note-msg {
  margin-top: 12px;
  font-size: 13px;
  font-weight: 500;
}
.note-msg.success { color: var(--state-success); }
.note-msg.error { color: var(--state-error); }
.recommend-note-list {
  display: grid;
  gap: 10px;
}
.recommend-note-item {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}
.recommend-note-item:hover {
  border-color: rgba(128, 128, 128,0.35);
  background: rgba(128, 128, 128,0.08);
}
.recommend-note-item span,
.recommend-note-item small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recommend-note-item span {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
}
.recommend-note-item small {
  color: var(--text-muted);
  font-size: 12px;
}

/* 截图预览弹窗 */
.preview-overlay {
  position: fixed;
  inset: 0;
  padding: 24px;
  background: rgba(10, 10, 10, .82);
  backdrop-filter: none;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  z-index: 9999;
}
.preview-modal {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  max-width: 560px;
  width: min(560px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  margin: auto 0;
  min-width: 0;
  box-shadow: var(--shadow-sm);
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-default);
}
.preview-close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-hover);
  border: 0;
  font-size: 22px;
  color: var(--text-muted);
  cursor: pointer;
}
.preview-close:hover { color: var(--text-primary); background: var(--border-default); }
.preview-body { padding: 22px; display: flex; justify-content: center; background: var(--bg-input); min-width: 0; overflow: auto; }
/* 二维码弹窗：只展示一个二维码，不做整页卡片截图（原先是 html2canvas 渲染 420px 卡片）。 */
.qrcode-modal { max-width: 400px; width: min(400px, 100%); }
.qrcode-img {
  display: block;
  width: min(260px, 100%);
  height: auto;
  aspect-ratio: 1;
  object-fit: contain;
  max-width: 100%;
  max-height: min(60vh, 320px);
  padding: 12px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}
.preview-footer { display: flex; gap: 12px; padding: 18px 22px; border-top: 1px solid var(--border-default); justify-content: stretch; }
.preview-footer > * { flex: 1; text-align: center; }
@media (max-width: 520px) {
  .preview-overlay { padding: 12px; }
  .preview-footer { flex-direction: column; }
}
</style>
