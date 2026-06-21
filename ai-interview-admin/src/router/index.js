import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { auth: true } },
  { path: '/users', name: 'Users', component: () => import('../views/Users.vue'), meta: { auth: true } },
  { path: '/interviews', name: 'Interviews', component: () => import('../views/Interviews.vue'), meta: { auth: true } },
  { path: '/interviews/:id', name: 'InterviewDetail', component: () => import('../views/InterviewDetail.vue'), meta: { auth: true } },
  { path: '/admins', name: 'Admins', component: () => import('../views/Admins.vue'), meta: { auth: true } },
  { path: '/waiting-list', name: 'WaitingList', component: () => import('../views/WaitingList.vue'), meta: { auth: true } },
  { path: '/announcements', name: 'Announcements', component: () => import('../views/Announcements.vue'), meta: { auth: true } },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings.vue'), meta: { auth: true } },
  { path: '/feedbacks', name: 'Feedbacks', component: () => import('../views/Feedbacks.vue'), meta: { auth: true } },
  { path: '/audit-logs', name: 'AuditLogs', component: () => import('../views/AuditLogs.vue'), meta: { auth: true } },
  { path: '/experiences', name: 'Experiences', component: () => import('../views/Experiences.vue'), meta: { auth: true } }
]

const router = createRouter({ history: createWebHistory('/admin/'), routes })

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.auth && !authStore.isLoggedIn) next('/login')
  else next()
})

export default router
