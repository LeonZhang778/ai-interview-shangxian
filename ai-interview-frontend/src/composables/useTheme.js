import { ref, watch } from 'vue'

const THEME_KEY = 'ai-interview-theme'

const theme = ref(localStorage.getItem(THEME_KEY) || 'dark')

function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t)
  // 让浏览器原生控件（select/option/input date 等）跟随主题渲染，
  // 避免夜间模式下出现白底白字看不清的问题。
  document.documentElement.style.colorScheme = t === 'light' ? 'light' : 'dark'
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
