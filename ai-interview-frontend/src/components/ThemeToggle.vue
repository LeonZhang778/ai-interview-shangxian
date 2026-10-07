<template>
  <button class="theme-toggle" @click="toggleTheme" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'">
    <span class="toggle-track" :class="{ light: theme === 'light' }">
      <span class="toggle-icon sun" :class="{ active: theme === 'light' }">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <circle cx="12" cy="12" r="5"/>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
      </span>
      <span class="toggle-thumb" :class="{ light: theme === 'light' }"></span>
      <span class="toggle-icon moon" :class="{ active: theme === 'dark' }">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </span>
    </span>
  </button>
</template>

<script setup>
import { useTheme } from '../composables/useTheme'
const { theme, toggleTheme } = useTheme()
</script>

<style scoped>
.theme-toggle {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
}
.toggle-track {
  width: 52px;
  height: 28px;
  border-radius: var(--radius-lg);
  background: var(--bg-hover);
  border: 1px solid var(--border-default);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}
.toggle-track.light {
  background: var(--bg-hover);
  border-color: var(--border-default);
}
.toggle-thumb {
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #EDEDED;
  top: 2px;
  left: 2px;
  transition: transform 0.2s ease;
  box-shadow: none;
}
.toggle-thumb.light {
  transform: translateX(24px);
  background: #0A0A0A;
}
.toggle-icon {
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  transition: color 0.2s ease;
}
.toggle-icon.active {
  color: var(--text-primary);
}
.toggle-icon.sun,
.toggle-icon.moon { color: var(--text-muted); }
.toggle-icon.sun.active,
.toggle-icon.moon.active { color: var(--text-primary); }
</style>
