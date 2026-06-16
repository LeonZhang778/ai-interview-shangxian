import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', name: 'Landing', component: () => import('../views/Landing.vue') },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue') },
  { path: '/forgot-password', name: 'ForgotPassword', component: () => import('../views/ForgotPassword.vue') },
  { path: '/waiting-list', name: 'WaitingList', component: () => import('../views/WaitingList.vue') },
  { path: '/waiting-list/verify', redirect: to => ({ path: '/waiting-list', query: to.query }) },
  { path: '/dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { auth: true } },
  { path: '/resume/upload', name: 'ResumeUpload', component: () => import('../views/ResumeUpload.vue'), meta: { auth: true } },
  { path: '/interview/:id', name: 'Interview', component: () => import('../views/Interview.vue'), meta: { auth: true } },
  { path: '/interview/:id/report', name: 'Report', component: () => import('../views/Report.vue'), meta: { auth: true } },
  { path: '/profile', name: 'Profile', component: () => import('../views/Profile.vue'), meta: { auth: true } },
  { path: '/experiences', name: 'Experiences', component: () => import('../views/Experiences.vue') },
  { path: '/experiences/:id', name: 'ExperienceDetail', component: () => import('../views/ExperienceDetail.vue') },
  { path: '/image-studio', name: 'ImageStudio', component: () => import('../views/ImageStudio.vue'), meta: { auth: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.auth && !authStore.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})

export default router
