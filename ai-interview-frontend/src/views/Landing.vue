<template>
  <div class="landing">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-content">
        <h1>AI 帮你模拟面试<br /><span class="highlight">提升通过率</span></h1>
        <p class="hero-desc">上传简历，AI 自动生成个性化面试题，实时评分反馈，生成综合评估报告</p>
        <div class="hero-actions">
          <button class="btn-glow" @click="handleGuest" :disabled="guestLoading">
            {{ guestLoading ? '进入中...' : '免费体验，无需注册' }}
          </button>
          <router-link to="/register" class="btn-outline">注册账号</router-link>
        </div>
        <p class="hero-stats">
          已服务 <strong>{{ userCount }}</strong> 位用户，完成 <strong>{{ interviewCount }}</strong> 次模拟面试
        </p>
      </div>
    </section>

    <!-- Features -->
    <section class="features">
      <h2 class="section-title">核心功能</h2>
      <div class="feature-grid">
        <div class="feature-card" v-for="f in features" :key="f.title">
          <span class="feature-icon">{{ f.icon }}</span>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="steps">
      <h2 class="section-title">使用流程</h2>
      <div class="step-list">
        <div class="step" v-for="(s, i) in steps" :key="i">
          <div class="step-num">{{ i + 1 }}</div>
          <div class="step-info">
            <h4>{{ s.title }}</h4>
            <p>{{ s.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta">
      <h2>准备好提升你的面试表现了吗？</h2>
      <p>无需注册，点击即刻开始 AI 模拟面试</p>
      <button class="btn-glow" @click="handleGuest" :disabled="guestLoading">
        {{ guestLoading ? '进入中...' : '立即开始' }}
      </button>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <p>智面 AI &copy; 2026 &mdash; 智能模拟面试平台</p>
      <p class="footer-links">
        <router-link to="/login">登录</router-link>
        <router-link to="/register">注册</router-link>
        <a href="mailto:1448203623@qq.com">反馈建议</a>
      </p>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { guestLogin } from '../api/auth'

const router = useRouter()
const authStore = useAuthStore()
const guestLoading = ref(false)
const userCount = ref('100+')
const interviewCount = ref('500+')

const features = [
  { icon: '📄', title: 'AI 简历解析', desc: '上传 PDF 简历，30 秒提取关键技能、经历和项目信息' },
  { icon: '🎯', title: '智能出题', desc: '根据你的简历和目标岗位，AI 定制个性化面试题' },
  { icon: '💬', title: '实时对话', desc: '像真人面试一样多轮对话，支持追问和深入探讨' },
  { icon: '📊', title: '即时评分', desc: '每道题实时评分（1-10 分），给出具体改进建议' },
  { icon: '📝', title: '综合报告', desc: '面试结束生成详细评估报告，含录用建议和提升方向' },
  { icon: '🔄', title: '反复练习', desc: '不限次数练习，每次题目不同，持续提升面试技巧' }
]

const steps = [
  { title: '上传简历', desc: '支持 PDF 格式，AI 自动解析个人信息和技能' },
  { title: '选择岗位', desc: '填写目标岗位、选择难度和题目数量' },
  { title: '开始面试', desc: 'AI 面试官逐题提问，你像真实面试一样回答' },
  { title: '查看报告', desc: '获得详细评分报告，了解优势和改进方向' }
]

async function handleGuest() {
  guestLoading.value = true
  try {
    const data = await guestLogin()
    authStore.setAuth(data)
    router.push('/dashboard')
  } catch (e) {
    router.push('/login')
  } finally {
    guestLoading.value = false
  }
}
</script>

<style scoped>
.landing {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #1e293b;
}

/* Hero */
.hero {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #6366f1 100%);
  color: white;
  padding: 80px 20px 60px;
  text-align: center;
}
.hero-content {
  max-width: 640px;
  margin: 0 auto;
}
.hero h1 {
  font-size: 40px;
  font-weight: 800;
  line-height: 1.3;
  margin-bottom: 16px;
}
.highlight {
  background: linear-gradient(90deg, #fbbf24, #f59e0b);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-desc {
  font-size: 17px;
  opacity: 0.9;
  line-height: 1.7;
  margin-bottom: 32px;
}
.hero-actions {
  display: flex;
  gap: 14px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 24px;
}
.btn-glow {
  padding: 14px 32px;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 700;
  color: #4f46e5;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.btn-glow:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0,0,0,0.2);
}
.btn-glow:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.btn-outline {
  padding: 14px 32px;
  border: 2px solid rgba(255,255,255,0.5);
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  text-decoration: none;
  transition: all 0.3s;
}
.btn-outline:hover {
  border-color: white;
  background: rgba(255,255,255,0.1);
}
.hero-stats {
  font-size: 14px;
  opacity: 0.8;
}

/* Features */
.features {
  padding: 60px 20px;
  max-width: 900px;
  margin: 0 auto;
}
.section-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 40px;
  color: #1e293b;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.feature-card {
  background: white;
  border-radius: 14px;
  padding: 28px 24px;
  text-align: center;
  border: 1px solid #f1f5f9;
  transition: all 0.3s;
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0,0,0,0.08);
}
.feature-icon {
  font-size: 36px;
  display: block;
  margin-bottom: 12px;
}
.feature-card h3 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 8px;
}
.feature-card p {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}

/* Steps */
.steps {
  background: #f8fafc;
  padding: 60px 20px;
}
.step-list {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.step {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.step-num {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}
.step-info h4 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
}
.step-info p {
  font-size: 14px;
  color: #64748b;
  line-height: 1.5;
}

/* CTA */
.cta {
  text-align: center;
  padding: 60px 20px;
  max-width: 500px;
  margin: 0 auto;
}
.cta h2 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 12px;
}
.cta p {
  color: #64748b;
  margin-bottom: 24px;
}

/* Footer */
.footer {
  text-align: center;
  padding: 30px 20px;
  border-top: 1px solid #e2e8f0;
  font-size: 13px;
  color: #94a3b8;
}
.footer-links {
  margin-top: 8px;
  display: flex;
  gap: 16px;
  justify-content: center;
}
.footer-links a {
  color: #64748b;
  text-decoration: none;
}
.footer-links a:hover {
  color: #4f46e5;
}

/* Responsive */
@media (max-width: 768px) {
  .hero { padding: 60px 20px 40px; }
  .hero h1 { font-size: 28px; }
  .feature-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 480px) {
  .hero h1 { font-size: 24px; }
  .hero-desc { font-size: 15px; }
  .feature-grid { grid-template-columns: 1fr; }
  .btn-glow, .btn-outline { width: 100%; text-align: center; }
}
</style>
