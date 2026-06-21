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
  border-radius: 14px;
  background: rgba(139,92,246,0.15);
  border: 1px solid rgba(139,92,246,0.2);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px;
  transition: all 0.3s ease;
}
.toggle-track.light {
  background: rgba(139,92,246,0.1);
  border-color: rgba(139,92,246,0.15);
}
.toggle-thumb {
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  top: 2px;
  left: 2px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(124,58,237,0.4);
}
.toggle-thumb.light {
  transform: translateX(24px);
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  box-shadow: 0 2px 8px rgba(245,158,11,0.4);
}
.toggle-icon {
  color: rgba(255,255,255,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  transition: color 0.3s;
}
.toggle-icon.active {
  color: rgba(255,255,255,0.8);
}
.toggle-icon.sun { color: rgba(251,191,36,0.4); }
.toggle-icon.sun.active { color: #fbbf24; }
.toggle-icon.moon { color: rgba(167,139,250,0.4); }
.toggle-icon.moon.active { color: #c4b5fd; }
</style>
