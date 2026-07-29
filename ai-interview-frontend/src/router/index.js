import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { trackPageView } from '../utils/tracker'

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
  { path: '/experiences/submit', name: 'ExperienceSubmit', component: () => import('../views/ExperienceSubmit.vue'), meta: { auth: true } },
  { path: '/my/experiences', name: 'MyExperiences', component: () => import('../views/MyExperiences.vue'), meta: { auth: true } },
  { path: '/my/experiences/:id/edit', name: 'EditExperience', component: () => import('../views/ExperienceSubmit.vue'), meta: { auth: true } },
  { path: '/experiences/:id', name: 'ExperienceDetail', component: () => import('../views/ExperienceDetail.vue') },
  { path: '/image-studio', name: 'ImageStudio', component: () => import('../views/ImageStudio.vue'), meta: { auth: true } },
  { path: '/announcements', name: 'Announcements', component: () => import('../views/Announcements.vue') },
  { path: '/announcements/:id', name: 'AnnouncementDetail', component: () => import('../views/AnnouncementDetail.vue') },
  { path: '/feedbacks', name: 'MyFeedbacks', component: () => import('../views/MyFeedbacks.vue'), meta: { auth: true } },
  { path: '/collections', name: 'MyCollections', component: () => import('../views/MyCollections.vue'), meta: { auth: true } },
  { path: '/learning-notes', name: 'LearningNotes', component: () => import('../views/LearningNotes.vue'), meta: { auth: true } },
  { path: '/learning-notes/edit/:id?', name: 'LearningNoteEdit', component: () => import('../views/LearningNoteEdit.vue'), meta: { auth: true } },
  { path: '/learning-notes/:id', name: 'LearningNoteDetail', component: () => import('../views/LearningNoteDetail.vue') },
  { path: '/notifications', name: 'Notifications', component: () => import('../views/Notifications.vue'), meta: { auth: true } },
  { path: '/analysis', name: 'Analysis', component: () => import('../views/Analysis.vue'), meta: { auth: true } },
  { path: '/shared/:token', name: 'SharedReport', component: () => import('../views/SharedReport.vue') }
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

router.afterEach((to) => {
  trackPageView(to.fullPath)
})

export default router
