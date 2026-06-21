import { ref, watch } from 'vue'

const THEME_KEY = 'ai-interview-theme'

const theme = ref(localStorage.getItem(THEME_KEY) || 'dark')

function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t)
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

watch(theme, (t) => {
  localStorage.setItem(THEME_KEY, t)
  applyTheme(t)
})

// Apply on load
applyTheme(theme.value)

export function useTheme() {
  return { theme, toggleTheme }
}
