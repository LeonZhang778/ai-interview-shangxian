<template>
  <StarryBackground />
  <div class="interview-page">
    <!-- 面试准备动画 -->
    <div v-if="preparing" class="prepare-overlay">
      <div class="prepare-card">
        <div class="ai-face-large">
          <svg viewBox="0 0 80 80" width="80" height="80">
            <circle cx="40" cy="40" r="38" fill="white" stroke="#A3A3A3" stroke-width="2"/>
            <ellipse cx="28" cy="36" rx="5" ry="6" fill="#1e1e1e">
              <animate attributeName="ry" values="6;1;6" dur="2.5s" repeatCount="indefinite"/>
            </ellipse>
            <ellipse cx="52" cy="36" rx="5" ry="6" fill="#1e1e1e">
              <animate attributeName="ry" values="6;1;6" dur="2.5s" repeatCount="indefinite"/>
            </ellipse>
            <path d="M30 52 Q40 60 50 52" stroke="#1e1e1e" stroke-width="2" fill="none" stroke-linecap="round"/>
          </svg>
        </div>
        <h2 style="margin-top:20px;font-size:20px">面试即将开始</h2>
        <p style="color:var(--text-muted);margin-top:8px;font-size:14px">{{ prepareTip }}</p>
        <div class="prepare-progress">
          <div class="prepare-bar" :style="{ width: preparePercent + '%' }"></div>
        </div>
        <p style="color:var(--text-secondary);font-size:12px;margin-top:8px">AI 正在为你准备面试题目...</p>
      </div>
    </div>

    <!-- 顶部状态栏 -->
    <div class="interview-header" v-if="!preparing">
      <div style="display:flex;align-items:center;gap:8px">
        <svg viewBox="0 0 32 32" width="24" height="24">
          <circle cx="16" cy="16" r="15" fill="white" stroke="#A3A3A3" stroke-width="1.5"/>
          <ellipse cx="11" cy="14" rx="2.5" ry="3" fill="#1e1e1e"/>
          <ellipse cx="21" cy="14" rx="2.5" ry="3" fill="#1e1e1e"/>
        </svg>
        <span>AI 面试官</span>
      </div>
      <span class="progress">第 {{ currentIndex + 1 }} / {{ totalQuestions }} 题</span>
      <router-link to="/dashboard" class="btn-secondary" style="padding:4px 12px;font-size:12px;border-radius:6px;display:inline-block">退出</router-link>
    </div>

    <details v-if="!preparing && gapAnalysisStatus !== 'not_requested' && gapAnalysisStatus !== 'disabled'" class="gap-panel">
      <summary>岗位要求 / 准备差距</summary>
      <div v-if="gapAnalysisStatus === 'failed'" class="gap-fallback">
        岗位分析暂时不可用，本场已使用通用岗位题目继续面试。
      </div>
      <div v-else-if="gapAnalysis" class="gap-content">
        <div class="gap-score">岗位匹配度 <strong>{{ gapAnalysis.overall_match_score || 0 }}</strong><span>/100</span></div>
        <div v-if="gapAnalysis.required_skills?.length" class="gap-section">
          <h4>必备技能</h4>
          <div class="gap-tags">
            <span v-for="skill in gapAnalysis.required_skills" :key="`required-${skill.name}`" :class="['gap-tag', `status-${skill.resume_status}`]">
              {{ skill.name }} · {{ skillStatus(skill.resume_status) }}
            </span>
          </div>
        </div>
        <div v-if="gapAnalysis.resume_gaps?.length" class="gap-section">
          <h4>优先准备</h4>
          <ul class="gap-list">
            <li v-for="gap in gapAnalysis.resume_gaps.slice(0, 4)" :key="`${gap.skill}-${gap.reason}`">
              <strong>{{ gap.skill }}</strong><span>{{ gap.practice_action || gap.reason }}</span>
            </li>
          </ul>
        </div>
      </div>
    </details>

    <!-- 聊天区域 -->
    <div class="chat-area" ref="chatArea" v-if="!preparing">
      <template v-for="(msg, i) in messages" :key="msg.key ?? i">
        <div :class="['message', msg.role]">
          <!-- AI 头像 -->
          <div v-if="msg.role === 'interviewer'" class="avatar-col">
            <svg viewBox="0 0 40 40" width="36" height="36" class="ai-avatar">
              <circle cx="20" cy="20" r="19" fill="white" stroke="#e5e7eb" stroke-width="1"/>
              <ellipse cx="14" cy="17" rx="2.5" ry="3" fill="#1e1e1e"/>
              <ellipse cx="26" cy="17" rx="2.5" ry="3" fill="#1e1e1e"/>
            </svg>
          </div>
          <div class="bubble">
            <div class="bubble-content" v-html="renderContent(msg.content)"></div>
          </div>
          <!-- 用户头像 -->
          <div v-if="msg.role === 'candidate'" class="avatar-col">
            <img v-if="userAvatar && !avatarError" :src="userAvatar" class="user-avatar" alt="me" @error="avatarError = true" />
            <div v-else class="user-avatar-placeholder">{{ userInitial }}</div>
          </div>
        </div>

        <!-- 面试官评语：跟随在对应回答之后单独成条（评语存于候选人消息的 feedback 字段） -->
        <div v-if="msg.role === 'candidate' && msg.feedback" class="message interviewer feedback-message">
          <div class="avatar-col">
            <svg viewBox="0 0 40 40" width="36" height="36" class="ai-avatar">
              <circle cx="20" cy="20" r="19" fill="white" stroke="#e5e7eb" stroke-width="1"/>
              <ellipse cx="14" cy="17" rx="2.5" ry="3" fill="#1e1e1e"/>
              <ellipse cx="26" cy="17" rx="2.5" ry="3" fill="#1e1e1e"/>
            </svg>
          </div>
          <div class="bubble feedback-bubble">
            <div class="bubble-content" v-html="renderContent(msg.feedback)"></div>
            <div v-if="msg.score" class="bubble-score"><BaseIcon name="star-fill" :size="14" /> {{ msg.score }}/10</div>
            <details v-if="msg.evaluation?.dimension_scores?.length" class="evaluation-details">
              <summary>查看评分依据</summary>
              <div v-for="dimension in msg.evaluation.dimension_scores" :key="dimension.key" class="evaluation-dimension">
                <div class="evaluation-dimension-header">
                  <span>{{ dimension.name || dimension.key }}</span>
                  <strong>{{ dimension.score }}/{{ dimension.max_score || 10 }}</strong>
                </div>
                <p v-if="dimension.evidence?.length" class="evaluation-label">回答原句</p>
                <blockquote v-for="evidence in dimension.evidence" :key="`${dimension.key}-${evidence.start}-${evidence.end}`">
                  “{{ evidence.quote }}”
                </blockquote>
                <p v-if="dimension.missing_evidence?.length" class="evaluation-label">未覆盖证据</p>
                <ul v-if="dimension.missing_evidence?.length">
                  <li v-for="missing in dimension.missing_evidence" :key="missing.criterion_key">{{ missing.description }}</li>
                </ul>
                <p v-if="dimension.improvement_actions?.length" class="evaluation-label">改进建议</p>
                <ul v-if="dimension.improvement_actions?.length">
                  <li v-for="action in dimension.improvement_actions" :key="action">{{ action }}</li>
                </ul>
              </div>
            </details>
          </div>
        </div>
      </template>

      <!-- 流式输出 -->
      <div v-if="streamingText" class="message interviewer">
        <div class="avatar-col">
          <svg viewBox="0 0 40 40" width="36" height="36" class="ai-avatar thinking">
            <circle cx="20" cy="20" r="19" fill="white" stroke="#A3A3A3" stroke-width="1.5"/>
            <ellipse cx="14" cy="17" rx="2.5" ry="3" fill="#1e1e1e">
              <animate attributeName="ry" values="3;1;3" dur="1.5s" repeatCount="indefinite"/>
            </ellipse>
            <ellipse cx="26" cy="17" rx="2.5" ry="3" fill="#1e1e1e">
              <animate attributeName="ry" values="3;1;3" dur="1.5s" repeatCount="indefinite"/>
            </ellipse>
          </svg>
        </div>
        <div class="bubble">
          <div class="bubble-content streaming-content" v-html="renderContent(streamingText)"></div>
          <span class="cursor-blink">▊</span>
        </div>
      </div>

      <!-- AI 思考中 -->
      <div v-if="thinking && !streamingText" class="message interviewer">
        <div class="avatar-col">
          <svg viewBox="0 0 40 40" width="36" height="36" class="ai-avatar thinking">
            <circle cx="20" cy="20" r="19" fill="white" stroke="#A3A3A3" stroke-width="1.5"/>
            <ellipse cx="14" cy="17" rx="2.5" ry="3" fill="#1e1e1e">
              <animate attributeName="ry" values="3;1;3" dur="1s" repeatCount="indefinite"/>
            </ellipse>
            <ellipse cx="26" cy="17" rx="2.5" ry="3" fill="#1e1e1e">
              <animate attributeName="ry" values="3;1;3" dur="1s" repeatCount="indefinite"/>
            </ellipse>
          </svg>
        </div>
        <div class="bubble thinking-bubble">
          <span class="dot-animation">AI 思考中<span class="dots"></span></span>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area" v-if="!preparing && !finished">
      <textarea v-model="answer" placeholder="输入你的回答..." @keydown.enter.exact.prevent="handleSubmit" @keydown.shift.enter.exact="null" :disabled="thinking" rows="3"></textarea>
      <button class="btn-primary" @click="handleSubmit" :disabled="!answer.trim() || thinking">
        {{ thinking ? '评估中...' : '发送 (Enter)' }}
      </button>
    </div>

    <!-- 面试结束 -->
    <div class="input-area finished" v-if="!preparing && finished">
      <p><BaseIcon name="check" :size="18" /> 面试结束！</p>
      <!-- 报告已改为后台生成：status=completed 只代表问答结束，报告可能还在路上。
           这里等 report_status 就绪再放行，避免用户点进一个空白报告页；
           等待期间也允许先进报告页（那边同样会轮询并给出重试入口）。 -->
      <template v-if="reportReady">
        <router-link :to="`/interview/${interviewId}/report`" class="btn-primary" style="display:inline-block;padding:10px 24px;color:white;border-radius:8px">
          查看评估报告
        </router-link>
      </template>
      <template v-else>
        <p class="report-pending">
          <span class="poll-spinner"></span>
          {{ reportFailed ? '报告生成遇到问题' : '正在生成评估报告' }}<span v-if="!reportFailed" class="dots"></span>
        </p>
        <p class="report-hint">
          {{ reportFailed ? '可以重新生成，或稍后到报告页重试' : '通常需要几十秒，可以先去报告页等待' }}
        </p>
        <div class="report-actions">
          <button v-if="reportFailed" class="btn-primary" @click="retryReport">重新生成报告</button>
          <router-link :to="`/interview/${interviewId}/report`" class="btn-ghost">
            去报告页
          </router-link>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { submitAnswerStream, getMessages, regenerateReport } from '../api/interview'
import { escapeHtml } from '../utils/html'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'

const route = useRoute()
const authStore = useAuthStore()
const interviewId = route.params.id

const messages = ref([])
const answer = ref('')
const thinking = ref(false)
const finished = ref(false)
const currentIndex = ref(0)
const totalQuestions = ref(5)
const chatArea = ref(null)
const streamingText = ref('')

// 报告就绪状态。后端把报告生成搬到了后台，所以「面试结束」与「报告可读」不再同时发生：
//   reportReady=false 时展示“生成中”，并轮询 /messages 上的 report_status。
// 默认 true 是为了让「进行中的面试」不受影响（那些面试根本不会走到结束态）。
const reportReady = ref(true)
const reportFailed = ref(false)
const gapAnalysisStatus = ref('not_requested')
const gapAnalysis = ref(null)

const REPORT_POLL_INTERVAL_MS = 3000
// 最多轮询约 2 分钟。超时不报错也不硬等，直接放行到报告页 —— 那边同样有轮询与重试，
// 比让用户卡在这个页面干等更合理。
const REPORT_POLL_MAX_TICKS = 40
let reportPollTimer = null
let reportPollTicks = 0

function stopReportPolling() {
  if (reportPollTimer) {
    clearInterval(reportPollTimer)
    reportPollTimer = null
  }
}

function applyReportStatus(status) {
  if (status) {
    reportFailed.value = status === 'failed'
    reportReady.value = status === 'ready'
  }
  if (reportReady.value) stopReportPolling()
}

function skillStatus(status) {
  return { matched: '已覆盖', partial: '部分覆盖', missing: '未发现证据', unknown: '待确认' }[status] || '待确认'
}

function startReportPolling() {
  if (reportPollTimer || reportReady.value) return
  reportPollTicks = 0
  reportPollTimer = setInterval(async () => {
    reportPollTicks += 1
    if (reportPollTicks > REPORT_POLL_MAX_TICKS) {
      stopReportPolling()
      reportReady.value = true
      return
    }
    try {
      const data = await getMessages(interviewId)
      applyReportStatus(data.report_status)
      if (reportReady.value) scrollToBottom()
    } catch (e) {
      console.error('轮询报告状态失败:', e)
    }
  }, REPORT_POLL_INTERVAL_MS)
}

async function retryReport() {
  try {
    await regenerateReport(interviewId)
    reportFailed.value = false
    reportReady.value = false
    startReportPolling()
  } catch (e) {
    messages.value.push({ role: 'interviewer', content: '重新生成报告失败：' + e.message })
    scrollToBottom()
  }
}

// 准备动画
const preparing = ref(true)
const preparePercent = ref(0)
const prepareTips = [
  '请做好准备，保持冷静自信',
  '回答时尽量结合项目经验',
  '注意条理清晰，分点作答',
  '面试官会根据你的简历提问'
]
const prepareTip = ref(prepareTips[0])

// 用户头像
const userAvatar = computed(() => authStore.userAvatar || '')
const avatarError = ref(false)
const userInitial = computed(() => {
  const name = authStore.userName || ''
  return name.charAt(0).toUpperCase() || 'U'
})

// 注意：本函数的返回值会交给 v-html 渲染。AI 输出受用户回答/简历内容影响、
// 且会落库后再次渲染，因此必须「先转义、再拼 <br>」，否则模型输出里的
// <script>/<img onerror> 会被当作 HTML 执行（自伤型 XSS，且被 token 存于
// localStorage 放大）。顺序不可颠倒，否则 <br> 自己也会被转义掉。
function renderContent(text) {
  if (!text) return ''
  // 实时过滤AI返回的JSON评分数据，避免流式输出时闪现（在原始文本上匹配，转义后就匹配不到了）
  const cleaned = text.split('__EVALUATION_JSON__')[0]
    .replace(/```json\s*\{[\s\S]*?\}\s*```/g, '')
    .replace(/\{[^{}]*"score"\s*:\s*[\d.]+[^{}]*\}/g, '')
    .trim()
  return escapeHtml(cleaned).replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatArea.value) chatArea.value.scrollTop = chatArea.value.scrollHeight
  })
}

async function loadMessages() {
  const data = await getMessages(interviewId)
  const msgList = Array.isArray(data) ? data : (data.items || [])
  // key 优先用后端消息 id（稳定），本地新推的消息用临时 key，避免重排时内容跳动
  messages.value = msgList.map(m => ({
    key: m.id != null ? `db-${m.id}` : undefined,
    role: m.role, content: m.content, score: m.score, feedback: m.feedback,
    evaluation: m.evaluation || {}, question_index: m.question_index
  }))
  const indices = msgList.map(m => m.question_index).filter(i => i != null)
  if (indices.length) currentIndex.value = Math.max(...indices)
  if (data.total_questions) totalQuestions.value = data.total_questions
  gapAnalysisStatus.value = data.gap_analysis_status || 'not_requested'
  gapAnalysis.value = data.gap_analysis || null
  // 以后端状态为准恢复“面试已结束”态：
  // 覆盖三种会丢失 done 事件的场景——① 最后一题的 SSE 流被中途掐断；
  // ② 用户在结束后刷新页面；③ 结束后从历史记录重新进入。
  if (data.status === 'completed') finished.value = true
  // 报告就绪标记：报告已改为后台生成，「状态已完成」不再等于「报告可读」。
  // 顺序不能反 —— 启动轮询的前置条件是已经进入结束态。
  applyReportStatus(data.report_status)
  if (finished.value && !reportReady.value) startReportPolling()
  scrollToBottom()
}

onMounted(async () => {
  // 准备动画
  let tipIdx = 0
  const tipTimer = setInterval(() => {
    tipIdx = (tipIdx + 1) % prepareTips.length
    prepareTip.value = prepareTips[tipIdx]
  }, 1500)

  const barTimer = setInterval(() => {
    if (preparePercent.value < 90) preparePercent.value += 2
  }, 100)

  try {
    await loadMessages()
  } catch (e) {
    console.error('加载消息失败:', e)
  }

  // 完成准备动画
  preparePercent.value = 100
  clearInterval(barTimer)
  clearInterval(tipTimer)
  setTimeout(() => { preparing.value = false }, 600)
  nextTick(scrollToBottom)
})

// 离开页面必须停掉轮询，否则定时器会在组件销毁后继续发请求
onUnmounted(stopReportPolling)

// 收尾：以数据库为准刷新会话，并推进题号。
// 抽成独立函数，供 onDone 正常回调与“流被掐断后的自愈”两条路径复用。
//
// 注意：评语（feedback）由后端持久化在候选人消息的 feedback 字段，
// 模板会将其渲染为独立的“面试官评语”气泡。因此这里不再把流式文本 push 成
// interviewer 消息——否则 loadMessages() 之后会与 DB 版本重复，且刷新即丢。
// 流式文本仅用于流式过程中的实时展示，落库以 DB 为唯一事实来源。
async function applyDone(data, rawStreamText, myAnswer) {
  streamingText.value = ''

  // 以 DB 为准刷新（含评语、下一题、分数）
  try {
    await loadMessages()
  } catch (e) {
    console.error('刷新消息失败:', e)
  }

  // 容错：若 DB 尚未返回刚落库的候选人回答（极端时序），本地补一条，
  // 保证用户能看到自己的回答；评语仍以后续刷新为准。
  const hasSavedAnswer = messages.value.some(m =>
    m.role === 'candidate' &&
    m.content === myAnswer &&
    m.question_index === data.question_index
  )
  if (!hasSavedAnswer) {
    messages.value.push({
      role: 'candidate',
      content: myAnswer,
      score: data.score,
      feedback: data.feedback || '',
        evaluation: data.evaluation || {},
      question_index: data.question_index
    })
  }

  if (data.is_finished) {
    finished.value = true
    // 报告可能仍在后台生成：结束态下若尚未就绪，启动轮询等它（正常情况下
    // 上面的 loadMessages 已经启动了，这里只是兜住极端时序）。
    if (!reportReady.value) startReportPolling()
  } else if (data.next_question) {
    currentIndex.value = data.question_index + 1
    const hasNextQuestion = messages.value.some(m =>
      m.role === 'interviewer' &&
      m.content === data.next_question &&
      m.question_index === data.question_index + 1
    )
    if (!hasNextQuestion) {
      messages.value.push({ role: 'interviewer', content: data.next_question, question_index: data.question_index + 1 })
    }
  }
  scrollToBottom()
}

async function handleSubmit() {
  if (!answer.value.trim() || thinking.value) return
  const myAnswer = answer.value.trim()
  answer.value = ''
  messages.value.push({ role: 'candidate', content: myAnswer })
  scrollToBottom()
  thinking.value = true
  streamingText.value = ''
  let rawStreamText = ''  // 保存原始完整文本用于最终提取
  let doneHandled = false  // 是否已收到并处理终态事件

  try {
    const result = await submitAnswerStream(interviewId, myAnswer,
      (chunk) => {
        rawStreamText += chunk
        // 实时过滤：去掉已完成的JSON块和正在构建中的JSON片段（以```json或裸{开头的尾部）
        let display = rawStreamText
          .replace(/```json\s*\{[\s\S]*?\}\s*```/g, '')
          .replace(/\{[^{}]*"score"\s*:\s*[\d.]+[^{}]*\}/g, '')
        // 过滤尾部不完整的JSON片段（```json...未闭合 或 {"sco...未闭合）
        display = display.replace(/```json[\s\S]*$/g, '')
        display = display.replace(/\{[^}]*$/g, function(match) {
          // 只过滤看起来像JSON评分的不完整片段
          return /["']?score/.test(match) || /^\{\s*$/.test(match) ? '' : match
        })
        streamingText.value = display.trim()
        scrollToBottom()
      },
      async (data) => {
        doneHandled = true
        await applyDone(data, rawStreamText, myAnswer)
        rawStreamText = ''
      }
    )

    // 自愈：流已结束但没收到 done（连接被中断 / 后端异常）。
    // 此时后端大概率已把评语和下一题写库，直接重新拉取消息并恢复输入态，
    // 避免界面永久停在“光标闪烁”的思考态。
    if (!doneHandled) {
      if (result?.error) {
        messages.value.push({ role: 'interviewer', content: result.error.message })
      }
      try {
        await loadMessages()
      } catch (e) {
        console.error('自愈刷新消息失败:', e)
      }
      streamingText.value = ''
    }
  } catch (e) {
    streamingText.value = ''
        messages.value.push({ role: 'interviewer', content: '出错了：' + e.message })
    scrollToBottom()
    // 出错也尝试拉一次，把后端已落库的内容同步回来
    try {
      await loadMessages()
    } catch (err) {
      console.error('出错后刷新消息失败:', err)
    }
  } finally {
    thinking.value = false
  }
}
</script>

<style scoped>
.interview-page { display: flex; flex-direction: column; height: 100vh; max-width: 800px; margin: 0 auto; color: var(--text-primary); }

/* 准备动画 */
.prepare-overlay {
  position: fixed; inset: 0; background: var(--bg-base);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.prepare-card { text-align: center; padding: 40px; }
.ai-face-large { animation: faceFloat 2s ease-in-out infinite; }
@keyframes faceFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.prepare-progress {
  width: 280px; height: 6px; background: rgba(128, 128, 128,0.1); border-radius: 3px;
  margin: 16px auto 0; overflow: hidden;
}
.prepare-bar {
  height: 100%; background: var(--accent-primary);
  border-radius: 3px; transition: width 0.3s ease;
}

/* 顶部 */
.interview-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; background: var(--bg-surface); border-bottom: 1px solid var(--border-default);
  font-size: 14px; font-weight: 600; backdrop-filter: none;
}
.progress { color: var(--text-muted); font-weight: 400; }

.gap-panel {
  margin: 10px 16px 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
}
.gap-panel summary { cursor:pointer; padding:10px 12px; font-size:13px; font-weight:600; color:var(--text-primary); }
.gap-content { padding:0 12px 12px; }
.gap-score { font-size:12px; color:var(--text-muted); margin-bottom:8px; }
.gap-score strong { color:var(--accent-light); font-size:17px; margin-left:6px; }
.gap-score span { margin-left:2px; }
.gap-section { margin-top:10px; }
.gap-section h4 { font-size:12px; color:var(--text-muted); margin-bottom:6px; }
.gap-tags { display:flex; flex-wrap:wrap; gap:6px; }
.gap-tag { padding:4px 7px; border-radius:5px; font-size:12px; border:1px solid var(--border-default); }
.status-matched { color:var(--state-success); }
.status-partial { color:var(--state-warning); }
.status-missing { color:var(--state-error); }
.gap-list { list-style:none; padding:0; margin:0; }
.gap-list li { display:flex; gap:8px; font-size:12px; line-height:1.6; margin-top:5px; }
.gap-list li strong { flex:0 0 auto; color:var(--text-primary); }
.gap-list li span { min-width:0; }
.gap-fallback { padding:0 12px 12px; color:var(--text-muted); font-size:12px; }

/* 聊天 */
.chat-area { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.message { display: flex; align-items: flex-start; gap: 10px; }
.message.interviewer { justify-content: flex-start; }
.message.candidate { justify-content: flex-end; }

/* 头像 */
.avatar-col { flex-shrink: 0; margin-top: 2px; }
.ai-avatar { border-radius: 50%; filter: none; }
.ai-avatar.thinking { animation: avatarPulse 1.5s ease-in-out infinite; }
@keyframes avatarPulse {
  0%, 100% { filter: none; }
  50% { filter: none; }
}
.user-avatar { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
.user-avatar-placeholder {
  width: 36px; height: 36px; border-radius: 50%;
  background: var(--accent-primary); color: var(--bg-base); display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600;
}

/* 气泡 */
.bubble { max-width: 70%; padding: 12px 16px; border-radius: 8px; font-size: 14px; line-height: 1.6; }
.interviewer .bubble { background: var(--bg-hover); border:1px solid var(--border-default); border-bottom-left-radius: 4px; color: var(--text-primary); }
.candidate .bubble { background: var(--accent-primary); color: var(--bg-base); border-bottom-right-radius: 4px; }
.thinking-bubble { color: var(--text-muted); font-style: italic; }
.dot-animation .dots::after { content: ''; animation: dots 1.5s steps(4, end) infinite; }
@keyframes dots {
  0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; } 100% { content: ''; }
}
.streaming-content { display: inline; }
.cursor-blink { display: inline; animation: blink 0.8s step-end infinite; color: var(--accent-primary); font-size: 14px; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.bubble-score { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.15); font-size: 13px; }
.interviewer .bubble-score { border-top-color: rgba(128, 128, 128,0.12); }

/* 面试官评语气泡：用左侧强调色边框与普通题目气泡区分，且不与下一题混淆 */
.feedback-message .feedback-bubble {
  border-left: 3px solid var(--accent-primary, #A3A3A3);
  background: rgba(128, 128, 128, 0.06);
}
.feedback-message .ai-avatar { filter: none; }
.evaluation-details { margin-top:10px; border-top:1px solid var(--border-default); padding-top:8px; font-size:12px; }
.evaluation-details summary { cursor:pointer; color:var(--accent-light); }
.evaluation-dimension { margin-top:10px; padding-top:8px; border-top:1px solid var(--border-default); }
.evaluation-dimension-header { display:flex; justify-content:space-between; gap:8px; color:var(--text-secondary); }
.evaluation-dimension-header strong { color:var(--text-primary); }
.evaluation-label { margin:7px 0 4px; color:var(--text-muted); font-size:11px; }
.evaluation-details blockquote { margin:4px 0; padding:5px 8px; border-left:2px solid var(--accent-primary); color:var(--text-secondary); line-height:1.5; }
.evaluation-details ul { margin:3px 0 0; padding-left:18px; color:var(--text-muted); }
.evaluation-details li { line-height:1.5; }

/* 输入 */
.input-area { padding: 16px 20px; background: var(--bg-surface); border-top: 1px solid var(--border-default); display: flex; gap: 12px; align-items: flex-end; backdrop-filter: none; }
.input-area textarea { flex: 1; resize: none; font-family: inherit; }
.input-area.finished { flex-direction: column; justify-content: center; align-items: center; padding: 24px; gap: 14px; }
.input-area.finished > p { font-size: 18px; font-weight: 600; }

/* 报告生成中：等就绪标记期间展示，避免把用户直接送进空白报告页 */
.report-pending { display: flex; align-items: center; gap: 8px; font-size: 15px !important; color: var(--text-secondary); }
.report-hint { font-size: 13px !important; font-weight: 400 !important; color: var(--text-secondary); opacity: 0.75; }
.report-actions { display: flex; gap: 12px; align-items: center; }
.btn-ghost {
  padding: 10px 20px; border-radius: 8px; font-size: 14px;
  color: var(--text-secondary); background: transparent;
  border: 1px solid var(--border-default); text-decoration: none;
  transition: color .15s, border-color .15s;
}
.btn-ghost:hover { color: var(--text-primary); border-color: var(--text-secondary); }
.poll-spinner {
  width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0;
  border: 2px solid var(--border-default); border-top-color: #A3A3A3;
  animation: poll-spin .8s linear infinite;
}
@keyframes poll-spin { to { transform: rotate(360deg); } }
</style>
