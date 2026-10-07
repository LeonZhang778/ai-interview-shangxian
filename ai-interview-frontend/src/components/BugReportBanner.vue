<template>
  <div class="bug-report-wrapper">
    <transition name="fade">
      <div v-if="expanded" class="bug-panel">
        <div class="bug-header">
          <span>意见反馈</span>
          <button class="close-btn" @click="expanded = false">&times;</button>
        </div>
        <div class="form-group">
          <label>反馈类型</label>
          <select v-model="form.feedback_type">
            <option value="bug">Bug 反馈</option>
            <option value="suggestion">功能建议</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div class="form-group">
          <label>内容 <span style="color:var(--red)">*</span></label>
          <textarea v-model="form.content" rows="4" placeholder="请描述你遇到的问题或建议..."></textarea>
        </div>
        <div class="form-group">
          <label>联系方式（选填）</label>
          <input v-model="form.contact" placeholder="邮箱或手机号，方便我们联系你" />
        </div>
        <button class="submit-btn" @click="submitFeedback" :disabled="!form.content || submitting">
          {{ submitting ? '提交中...' : '提交反馈' }}
        </button>
        <p v-if="submitSuccess" class="success-msg">感谢反馈！我们会尽快处理</p>
        <p class="bug-note">所有反馈都会被记录，帮助我们持续改进</p>
      </div>
    </transition>
    <button class="bug-toggle" @click="expanded = !expanded" title="意见反馈" aria-label="意见反馈">
      ?
    </button>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import api from '../api/request'

const expanded = ref(false)
const submitting = ref(false)
const submitSuccess = ref(false)

const form = reactive({
  feedback_type: 'bug',
  content: '',
  contact: '',
  page_url: window.location.href,
})

async function submitFeedback() {
  if (!form.content) return
  submitting.value = true
  submitSuccess.value = false
  try {
    await api.post('/feedbacks', {
      content: form.content,
      feedback_type: form.feedback_type,
      contact: form.contact || undefined,
      page_url: window.location.href,
    })
    submitSuccess.value = true
    form.content = ''
    form.contact = ''
    setTimeout(() => { submitSuccess.value = false }, 3000)
  } catch (e) {
    alert('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.bug-report-wrapper {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.bug-toggle {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: var(--text-primary);
  color: var(--bg-base);
  font-size: 22px;
  cursor: pointer;
  box-shadow: none;
  transition: opacity 0.15s, background-color 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bug-toggle:hover {
  transform: none;
  opacity: 0.85;
  box-shadow: none;
}

.bug-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  box-shadow: none;
  width: 300px;
  font-size: 13px;
  line-height: 1.6;
}

.bug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 14px;
  color: var(--text-primary);
}

.close-btn {
  border: none;
  background: none;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.2s;
}
.close-btn:hover { color: var(--text-primary); }

.form-group {
  margin-bottom: 10px;
}
.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  box-sizing: border-box;
  font-family: inherit;
  background: var(--bg-input);
  color: var(--text-primary);
  transition: border-color 0.2s, background 0.3s;
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--border-focus);
  background: var(--bg-input-focus);
}
.form-group textarea {
  resize: vertical;
}

/* Dark mode: override browser defaults for select/option */
.bug-panel select option {
  background-color: var(--bg-surface);
  color: var(--text-primary);
}
:root[data-theme="light"] .bug-panel select option {
  background-color: var(--bg-surface);
  color: var(--text-primary);
}

.submit-btn {
  width: 100%;
  padding: 10px;
  background: var(--text-primary);
  color: var(--bg-base);
  border: 1px solid var(--text-primary);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  box-shadow: none;
}
.submit-btn:hover {
  opacity: 0.85;
  transform: none;
  box-shadow: none;
}
.submit-btn:disabled {
  background: var(--text-primary);
  border-color: var(--text-primary);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.success-msg {
  color: var(--green);
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  margin: 8px 0 0;
}

.bug-note {
  color: var(--text-dim);
  font-size: 11px;
  margin: 8px 0 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 480px) {
  .bug-report-wrapper {
    bottom: 16px;
    right: 16px;
  }
  .bug-panel {
    width: calc(100vw - 32px);
    max-width: 300px;
  }
}
</style>
