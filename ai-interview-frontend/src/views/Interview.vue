<template>
  <StarryBackground />
  <div class="interview-page">
    <!-- 面试准备动画 -->
    <div v-if="preparing" class="prepare-overlay">
      <div class="prepare-card">
        <div class="ai-face-large">
          <svg viewBox="0 0 80 80" width="80" height="80">
            <circle cx="40" cy="40" r="38" fill="white" stroke="#4f46e5" stroke-width="2"/>
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
          <circle cx="16" cy="16" r="15" fill="white" stroke="#4f46e5" stroke-width="1.5"/>
          <ellipse cx="11" cy="14" rx="2.5" ry="3" fill="#1e1e1e"/>
          <ellipse cx="21" cy="14" rx="2.5" ry="3" fill="#1e1e1e"/>
        </svg>
        <span>AI 面试官</span>
      </div>
      <span class="progress">第 {{ currentIndex + 1 }} / {{ totalQuestions }} 题</span>
      <router-link to="/dashboard" class="btn-secondary" style="padding:4px 12px;font-size:12px;border-radius:6px;display:inline-block">退出</router-link>
    </div>

    <!-- 聊天区域 -->
    <div class="chat-area" ref="chatArea" v-if="!preparing">
      <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
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
          <div v-if="msg.score" class="bubble-score">⭐ {{ msg.score }}/10</div>
        </div>
        <!-- 用户头像 -->
        <div v-if="msg.role === 'candidate'" class="avatar-col">
          <img v-if="userAvatar && !avatarError" :src="userAvatar" class="user-avatar" alt="me" @error="avatarError = true" />
          <div v-else class="user-avatar-placeholder">{{ userInitial }}</div>
        </div>
      </div>

      <!-- 流式输出 -->
      <div v-if="streamingText" class="message interviewer">
        <div class="avatar-col">
          <svg viewBox="0 0 40 40" width="36" height="36" class="ai-avatar thinking">
            <circle cx="20" cy="20" r="19" fill="white" stroke="#4f46e5" stroke-width="1.5"/>
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
            <circle cx="20" cy="20" r="19" fill="white" stroke="#4f46e5" stroke-width="1.5"/>
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
      <p>🎉 面试结束！</p>
      <router-link :to="`/interview/${interviewId}/report`" class="btn-primary" style="display:inline-block;padding:10px 24px;color:white;border-radius:8px">
        查看评估报告
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { submitAnswerStream, getMessages } from '../api/interview'
import StarryBackground from '../components/StarryBackground.vue'

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

// 准备动画
const preparing = ref(true)
const preparePercent = ref(0)
const prepareTips = [
  '请做好准备，保持冷静自信 💪',
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
  return name.charAt(0).toUpperCase() || '👤'
})

function renderContent(text) {
  if (!text) return ''
  // 实时过滤AI返回的JSON评分数据，避免流式输出时闪现
  let cleaned = text
    .replace(/```json\s*\{[\s\S]*?\}\s*```/g, '')
    .replace(/\{[^{}]*"score"\s*:\s*[\d.]+[^{}]*\}/g, '')
    .trim()
  return cleaned.replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatArea.value) chatArea.value.scrollTop = chatArea.value.scrollHeight
  })
}

async function loadMessages() {
  const data = await getMessages(interviewId)
  const msgList = Array.isArray(data) ? data : (data.items || [])
  messages.value = msgList.map(m => ({
    role: m.role, content: m.content, score: m.score, feedback: m.feedback, question_index: m.question_index
  }))
  const indices = msgList.map(m => m.question_index).filter(i => i != null)
  if (indices.length) currentIndex.value = Math.max(...indices)
  if (data.total_questions) totalQuestions.value = data.total_questions
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

async function handleSubmit() {
  if (!answer.value.trim() || thinking.value) return
  const myAnswer = answer.value.trim()
  answer.value = ''
  messages.value.push({ role: 'candidate', content: myAnswer })
  scrollToBottom()
  thinking.value = true
  streamingText.value = ''
  let rawStreamText = ''  // 保存原始完整文本用于最终提取

  try {
    await submitAnswerStream(interviewId, myAnswer,
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
        if (rawStreamText.trim()) {
          let displayText = rawStreamText
            .replace(/```json\s*\{[\s\S]*?\}\s*```/g, '')
            .replace(/\{[^{}]*"score"\s*:\s*[\d.]+[^{}]*\}/g, '')
            .trim()
          if (displayText) {
            messages.value.push({ role: 'interviewer', content: displayText, score: data.score })
          }
        }
        streamingText.value = ''
        rawStreamText = ''
        const lastCandidate = [...messages.value].reverse().find(m => m.role === 'candidate')
        if (lastCandidate) lastCandidate.score = data.score

        try {
          await loadMessages()
        } catch (e) {
          console.error('刷新消息失败:', e)
        }
        const hasSavedAnswer = messages.value.some(m =>
          m.role === 'candidate' &&
          m.content === myAnswer &&
          m.question_index === data.question_index
        )
        if (!hasSavedAnswer) {
          messages.value.push({ role: 'candidate', content: myAnswer, score: data.score, question_index: data.question_index })
        }

        if (data.is_finished) {
          finished.value = true
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
    )
  } catch (e) {
    streamingText.value = ''
    messages.value.push({ role: 'interviewer', content: '⚠️ 出错了：' + e.message })
    scrollToBottom()
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
  width: 280px; height: 6px; background: rgba(139,92,246,0.1); border-radius: 3px;
  margin: 16px auto 0; overflow: hidden;
}
.prepare-bar {
  height: 100%; background: linear-gradient(90deg, #7c3aed, #a855f7);
  border-radius: 3px; transition: width 0.3s ease;
}

/* 顶部 */
.interview-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; background: var(--bg-surface); border-bottom: 1px solid var(--border-default);
  font-size: 14px; font-weight: 600; backdrop-filter: blur(20px);
}
.progress { color: var(--text-muted); font-weight: 400; }

/* 聊天 */
.chat-area { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.message { display: flex; align-items: flex-start; gap: 10px; }
.message.interviewer { justify-content: flex-start; }
.message.candidate { justify-content: flex-end; }

/* 头像 */
.avatar-col { flex-shrink: 0; margin-top: 2px; }
.ai-avatar { border-radius: 50%; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3)); }
.ai-avatar.thinking { animation: avatarPulse 1.5s ease-in-out infinite; }
@keyframes avatarPulse {
  0%, 100% { filter: drop-shadow(0 0 0 rgba(168,85,247,0)); }
  50% { filter: drop-shadow(0 0 8px rgba(168,85,247,0.5)); }
}
.user-avatar { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
.user-avatar-placeholder {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: white; display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600;
}

/* 气泡 */
.bubble { max-width: 70%; padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
.interviewer .bubble { background: var(--bg-hover); border:1px solid var(--border-default); border-bottom-left-radius: 4px; color: var(--text-primary); }
.candidate .bubble { background: linear-gradient(135deg, #7c3aed, #6366f1); color: white; border-bottom-right-radius: 4px; }
.thinking-bubble { color: var(--text-muted); font-style: italic; }
.dot-animation .dots::after { content: ''; animation: dots 1.5s steps(4, end) infinite; }
@keyframes dots {
  0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; } 100% { content: ''; }
}
.streaming-content { display: inline; }
.cursor-blink { display: inline; animation: blink 0.8s step-end infinite; color: var(--accent-primary); font-size: 14px; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.bubble-score { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.15); font-size: 13px; }
.interviewer .bubble-score { border-top-color: rgba(139,92,246,0.12); }

/* 输入 */
.input-area { padding: 16px 20px; background: var(--bg-surface); border-top: 1px solid var(--border-default); display: flex; gap: 12px; align-items: flex-end; backdrop-filter: blur(20px); }
.input-area textarea { flex: 1; resize: none; font-family: inherit; }
.input-area.finished { justify-content: center; align-items: center; padding: 24px; gap: 16px; }
.input-area.finished p { font-size: 18px; font-weight: 600; }
</style>
