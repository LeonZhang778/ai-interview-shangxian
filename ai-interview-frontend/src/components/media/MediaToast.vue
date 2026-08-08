<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite" aria-label="通知消息">
      <TransitionGroup name="toast">
        <div
          v-for="toast in store.toasts"
          :key="toast.id"
          :class="['toast-item', `toast-${toast.type}`]"
          role="alert"
        >
          <span class="toast-icon" aria-hidden="true">
            {{ toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : 'ℹ' }}
          </span>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close" type="button" aria-label="关闭" @click="store.removeToast(toast.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useMediaStore } from '../../stores/media'

const store = useMediaStore()
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 400px;
  pointer-events: none;
}
.toast-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--bg-card, #1e2243);
  border: 1px solid var(--border-default, rgba(139, 92, 246, 0.1));
  box-shadow: var(--shadow-lg, 0 8px 32px rgba(0,0,0,0.3));
  pointer-events: auto;
  font-size: 13px;
  backdrop-filter: blur(12px);
}
.toast-icon {
  flex: 0 0 22px;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  color: white;
}
.toast-success .toast-icon { background: var(--green, #34d399); }
.toast-error .toast-icon { background: var(--red, #f87171); }
.toast-info .toast-icon { background: var(--accent-cyan, #67d4e8); }
.toast-message {
  flex: 1;
  color: var(--text-primary, #e2e8f0);
  line-height: 1.4;
}
.toast-close {
  flex: 0 0 18px;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border: none;
  background: transparent;
  color: var(--text-muted, #6b7280);
  cursor: pointer;
  font-size: 11px;
  border-radius: 4px;
}
.toast-close:hover {
  color: var(--text-primary, #e2e8f0);
  background: var(--bg-hover, rgba(139, 92, 246, 0.08));
}

/* 过渡动画 */
.toast-enter-active { transition: all .3s ease-out; }
.toast-leave-active { transition: all .2s ease-in; }
.toast-enter-from { opacity: 0; transform: translateX(40px); }
.toast-leave-to { opacity: 0; transform: translateX(40px); }
</style>