<template>
  <div class="bug-report-wrapper">
    <transition name="fade">
      <div v-if="expanded" class="bug-panel">
        <div class="bug-header">
          <span>🐛 反馈问题</span>
          <button class="close-btn" @click="expanded = false">&times;</button>
        </div>
        <p class="bug-desc">发现平台 Bug？请反馈至：</p>
        <a href="mailto:1448203623@qq.com" class="bug-email">1448203623@qq.com</a>
        <p class="bug-note">所有反馈用户将记录到名单，网站持续维护更新</p>
      </div>
    </transition>
    <button class="bug-toggle" @click="expanded = !expanded" title="反馈问题">
      🐛
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const expanded = ref(false)
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
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: #4f46e5;
  font-size: 22px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4);
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bug-toggle:hover {
  background: #4338ca;
  transform: scale(1.1);
}

.bug-panel {
  background: white;
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  width: 260px;
  font-size: 13px;
  line-height: 1.6;
}

.bug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 10px;
  color: #1e293b;
}

.close-btn {
  border: none;
  background: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0 2px;
}
.close-btn:hover {
  color: #475569;
}

.bug-desc {
  color: #475569;
  margin-bottom: 6px;
}

.bug-email {
  display: block;
  color: #4f46e5;
  font-weight: 600;
  font-size: 14px;
  text-decoration: none;
  margin-bottom: 8px;
  word-break: break-all;
}
.bug-email:hover {
  text-decoration: underline;
}

.bug-note {
  color: #94a3b8;
  font-size: 12px;
  margin: 0;
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
  .bug-toggle {
    width: 50px;
    height: 50px;
    font-size: 24px;
  }
  .bug-panel {
    width: calc(100vw - 32px);
    max-width: 300px;
  }
}
</style>
