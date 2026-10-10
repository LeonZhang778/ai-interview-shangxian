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
            <BaseIcon :name="toast.type === 'success' ? 'check' : toast.type === 'error' ? 'x' : 'info'" :size="14" />
          </span>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close" type="button" aria-label="关闭" @click="store.removeToast(toast.id)"><BaseIcon name="x" :size="14" /></button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useMediaStore } from '../../stores/media'
import BaseIcon from '../BaseIcon.vue'

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
  border-radius: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-default, rgba(128, 128, 128, 0.1));
  box-shadow: var(--shadow-sm);
  pointer-events: auto;
  font-size: 13px;
  backdrop-filter: none;
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
  color: var(--bg-base);
}
.toast-success .toast-icon { background: var(--green, #A3A3A3); }
.toast-error .toast-icon { background: var(--red, #A3A3A3); }
.toast-info .toast-icon { background: var(--state-info); }
.toast-message {
  flex: 1;
  color: var(--text-primary);
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
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  border-radius: 4px;
}
.toast-close:hover {
  color: var(--text-primary);
  background: var(--bg-hover, rgba(128, 128, 128, 0.08));
}

/* 过渡动画 */
.toast-enter-active { transition: all .3s ease-out; }
.toast-leave-active { transition: all .2s ease-in; }
.toast-enter-from { opacity: 0; transform: translateX(40px); }
.toast-leave-to { opacity: 0; transform: translateX(40px); }
</style>
