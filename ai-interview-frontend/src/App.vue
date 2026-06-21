<template>
  <div id="app">
    <div class="top-sticky">
      <AnnouncementBanner />
      <nav class="navbar" v-if="authStore.token">
        <div class="nav-content">
          <router-link to="/dashboard" class="nav-logo">🎯 智面</router-link>
          <div class="nav-links">
            <router-link to="/experiences">面经广场</router-link>
            <router-link to="/image-studio">AI 画图</router-link>
            <router-link to="/dashboard">面试记录</router-link>
            <router-link to="/resume/upload">上传简历</router-link>
            <router-link to="/feedbacks" title="我的反馈">我的反馈</router-link>
            <router-link to="/profile" class="nav-user-link">
              <img v-if="authStore.userAvatar && !avatarError" :src="authStore.userAvatar" class="nav-avatar" alt="avatar" @error="avatarError = true" />
              <span v-else class="nav-avatar-placeholder">👤</span>
              <span>{{ authStore.userName || '个人中心' }}</span>
            </router-link>
            <ThemeToggle />
            <button class="btn-logout" @click="logout">退出</button>
          </div>
        </div>
      </nav>
      <nav class="navbar" v-else>
        <div class="nav-content">
          <router-link to="/" class="nav-logo">🎯 智面</router-link>
          <div class="nav-links">
            <ThemeToggle />
          </div>
        </div>
      </nav>
    </div>
    <div v-if="authStore.isGuest" class="guest-banner">
      <span>游客模式</span>，<router-link to="/register">注册账号</router-link>可永久保存面试记录
    </div>
    <router-view />
    <BugReportBanner />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from './stores/auth'
import BugReportBanner from './components/BugReportBanner.vue'
import AnnouncementBanner from './components/AnnouncementBanner.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import { useTheme } from './composables/useTheme'
import { useRouter } from 'vue-router'
import { getProfile } from './api/user'

const authStore = useAuthStore()
const router = useRouter()
const avatarError = ref(false)

// Initialize theme
const { theme } = useTheme()

onMounted(async () => {
  if (authStore.token) {
    try {
      const data = await getProfile()
      authStore.setUserInfo(data)
      avatarError.value = false
    } catch (e) {
      // 忽略
    }
  }
})

async function logout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.top-sticky {
  position: sticky;
  top: 0;
  z-index: 100;
}
.navbar {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  padding: 0 20px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.nav-content {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
}
.nav-logo {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #a855f7, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.nav-links {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 14px;
}
.nav-links a {
  color: var(--text-secondary);
  transition: color 0.2s;
}
.nav-links a:hover {
  color: var(--accent-light);
}
.nav-links a.router-link-active {
  color: var(--accent-primary);
  font-weight: 600;
}
.nav-user-link {
  color: var(--text-secondary);
  font-size: 13px;
  transition: color 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-user-link:hover {
  color: var(--accent-light);
}
.nav-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
}
.nav-avatar-placeholder {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--purple-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}
.guest-banner {
  background: var(--amber-bg);
  color: var(--amber);
  text-align: center;
  padding: 8px 16px;
  font-size: 13px;
  border-bottom: 1px solid rgba(245,158,11,0.15);
}
.guest-banner a {
  color: var(--accent-primary);
  font-weight: 600;
  text-decoration: underline;
}
.btn-logout {
  padding: 6px 14px;
  font-size: 13px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-logout:hover {
  background: var(--red-bg);
  color: var(--red);
  border-color: rgba(239,68,68,0.2);
}
</style>
