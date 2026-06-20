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
            <button class="btn-logout" @click="logout">退出</button>
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
import { useRouter } from 'vue-router'
import { getProfile } from './api/user'

const authStore = useAuthStore()
const router = useRouter()
const avatarError = ref(false)

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
  background: rgba(8, 5, 25, 0.9);
  border-bottom: 1px solid rgba(139,92,246,0.1);
  padding: 0 20px;
  backdrop-filter: blur(20px);
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
  color: #9ca3af;
  transition: color 0.2s;
}
.nav-links a:hover {
  color: #c4b5fd;
}
.nav-links a.router-link-active {
  color: #a855f7;
  font-weight: 600;
}
.nav-user {
  color: #6b7280;
  font-size: 13px;
}
.nav-user-link {
  color: #9ca3af;
  font-size: 13px;
  transition: color 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-user-link:hover {
  color: #c4b5fd;
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
  background: rgba(139,92,246,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}
.guest-banner {
  background: rgba(245,158,11,0.08);
  color: #fbbf24;
  text-align: center;
  padding: 8px 16px;
  font-size: 13px;
  border-bottom: 1px solid rgba(245,158,11,0.15);
}
.guest-banner a {
  color: #a855f7;
  font-weight: 600;
  text-decoration: underline;
}
.btn-logout {
  padding: 6px 14px;
  font-size: 13px;
  background: rgba(139,92,246,0.08);
  color: #9ca3af;
  border: 1px solid rgba(139,92,246,0.12);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-logout:hover {
  background: rgba(239,68,68,0.1);
  color: #f87171;
  border-color: rgba(239,68,68,0.2);
}
</style>
