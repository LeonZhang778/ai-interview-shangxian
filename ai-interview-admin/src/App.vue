<template>
  <div class="admin-layout" v-if="authStore.isLoggedIn">
    <aside class="sidebar">
      <div class="sidebar-logo">
        <img src="/site-logo.png" class="logo-icon" alt="智面" />
        <span class="logo-text">智面</span>
      </div>
      <div class="sidebar-subtitle">后台管理</div>
      <nav class="sidebar-nav">
        <router-link to="/" exact-active-class="active">
          <span class="nav-icon">📊</span> 数据概览
        </router-link>
        <router-link to="/users" active-class="active">
          <span class="nav-icon">👥</span> 用户管理
        </router-link>
        <router-link to="/interviews" active-class="active">
          <span class="nav-icon">🎤</span> 面试记录
        </router-link>
        <router-link to="/admins" active-class="active">
          <span class="nav-icon">🛡️</span> 管理员管理
        </router-link>
        <router-link to="/announcements" active-class="active">
          <span class="nav-icon">📢</span> 公告管理
        </router-link>
        <router-link to="/settings" active-class="active">
          <span class="nav-icon">⚙️</span> 系统设置
        </router-link>
        <router-link to="/feedbacks" active-class="active">
          <span class="nav-icon">📝</span> 用户反馈
        </router-link>
        <router-link to="/audit-logs" active-class="active">
          <span class="nav-icon">📋</span> 操作日志
        </router-link>
        <router-link to="/experiences" active-class="active">
          <span class="nav-icon">📄</span> 面经管理
        </router-link>
        <router-link to="/waiting-list" active-class="active">
          <span class="nav-icon">⏳</span> 候选名单
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <span>{{ authStore.email }}</span>
        <button class="logout-btn" @click="logout">退出登录</button>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
  <router-view v-else />
</template>

<script setup>
import { useAuthStore } from './stores/auth'
import { useRouter } from 'vue-router'
const authStore = useAuthStore()
const router = useRouter()
async function logout() { await authStore.logout(); router.push('/login') }
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }

.sidebar {
  width: 230px;
  background: var(--admin-bg-sidebar);
  color: var(--admin-text-sidebar-active);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0; left: 0; bottom: 0;
  overflow: hidden;
}

.sidebar-logo {
  font-size: 22px;
  font-weight: 700;
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
}

.logo-icon {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  object-fit: cover;
  -webkit-text-fill-color: initial;
}

.logo-text {
  color: var(--admin-text-sidebar-active);
}

.sidebar-subtitle {
  font-size: 12px;
  color: var(--admin-text-sidebar);
  margin-bottom: 32px;
  position: relative;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  position: relative;
}

.sidebar-nav a {
  padding: 11px 14px;
  border-radius: var(--admin-radius-md);
  color: var(--admin-text-sidebar);
  font-size: 14px;
  transition: background 0.15s, color 0.15s;
  display: flex;
  align-items: center;
  gap: 10px;
}

.sidebar-nav a:hover {
  background: var(--admin-bg-sidebar-hover);
  color: var(--admin-text-sidebar-active);
}

.sidebar-nav a.active {
  background: var(--admin-bg-sidebar-active);
  color: var(--admin-text-sidebar-active);
}

.nav-icon { font-size: 16px; }

.sidebar-footer {
  font-size: 12px;
  color: var(--admin-text-sidebar);
  border-top: 1px solid #262626;
  padding-top: 16px;
  position: relative;
}

.logout-btn {
  display: block;
  width: 100%;
  margin-top: 10px;
  padding: 8px;
  border-radius: var(--admin-radius-md);
  font-size: 13px;
  background: transparent;
  color: var(--admin-text-sidebar);
  border: 1px solid #262626;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.logout-btn:hover {
  background: var(--admin-bg-sidebar-hover);
  color: var(--admin-text-sidebar-active);
  border-color: #404040;
}

.main-content {
  margin-left: 230px;
  flex: 1;
  padding: 28px;
  background: var(--admin-bg-page);
}
</style>
