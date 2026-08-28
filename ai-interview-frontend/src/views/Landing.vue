<template>
  <div class="landing">
    <StarryBackground />
    <!-- Hero -->
    <section class="hero">
      <div class="hero-content">
        <h1>AI 面试训练工作台<br /><span class="highlight">从简历到复盘一站完成</span></h1>
        <p class="hero-desc">{{ siteSlogan }} — 围绕真实求职场景，提供简历解析、模拟面试、评分报告、面经学习和媒体工具</p>
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

    <!-- Intro -->
    <section class="intro">
      <p class="intro-kicker">网站介绍</p>
      <h2>智面 AI 专注帮求职者把面试准备做扎实</h2>
      <p class="intro-desc">
        平台以简历为起点，结合目标岗位生成针对性问题，并在回答过程中给出评分与改进建议。
        面试结束后，你可以继续沉淀复盘报告、查看面经、整理学习笔记，也可以使用媒体工具处理视频素材。
      </p>
      <div class="intro-grid">
        <div class="intro-item" v-for="item in introItems" :key="item.title">
          <strong>{{ item.title }}</strong>
          <span>{{ item.desc }}</span>
        </div>
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
      <p>{{ siteName }} &copy; 2026 &mdash; {{ siteSlogan }}</p>
      <p class="footer-links">
        <router-link to="/experiences">面经广场</router-link>
        <router-link to="/learning-notes">学习笔记</router-link>
        <router-link to="/login">登录</router-link>
        <router-link to="/register">注册</router-link>
        <a v-if="contactEmail" :href="`mailto:${contactEmail}`">反馈建议</a>
        <a v-else href="mailto:1448203623@qq.com">反馈建议</a>
      </p>
      <p v-if="icpNumber" class="footer-icp" style="font-size:11px;color:var(--text-muted);margin-top:8px">
        {{ icpNumber }}
      </p>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { guestLogin } from '../api/auth'
import { getSiteInfo } from '../api/config'
import StarryBackground from '../components/StarryBackground.vue'

const router = useRouter()
const authStore = useAuthStore()
const guestLoading = ref(false)
const userCount = ref('100+')
const interviewCount = ref('500+')
const siteName = ref('智面 AI')
const siteSlogan = ref('AI 驱动的智能模拟面试平台')
const icpNumber = ref('')
const contactEmail = ref('')

onMounted(async () => {
  try {
    const info = await getSiteInfo()
    if (info.site_name) siteName.value = info.site_name
    if (info.site_slogan) siteSlogan.value = info.site_slogan
    if (info.icp_number) icpNumber.value = info.icp_number
    if (info.contact_email) contactEmail.value = info.contact_email
    if (info.seo_title) document.title = info.seo_title
  } catch (e) { /* use defaults */ }
})

const features = [
  { icon: '📄', title: 'AI 简历解析', desc: '上传 PDF 简历，30 秒提取关键技能、经历和项目信息' },
  { icon: '🎯', title: '智能出题', desc: '根据你的简历和目标岗位，AI 定制个性化面试题' },
  { icon: '💬', title: '实时对话', desc: '像真人面试一样多轮对话，支持追问和深入探讨' },
  { icon: '📊', title: '即时评分', desc: '每道题实时评分（1-10 分），给出具体改进建议' },
  { icon: '📝', title: '综合报告', desc: '面试结束生成详细评估报告，含录用建议和提升方向' },
  { icon: '📚', title: '学习笔记', desc: '沉淀面试知识点，支持公开分享，形成广场互助学习' },
  { icon: '🎬', title: '媒体工具箱', desc: '支持视频转换、压缩、裁剪、GIF、合并、水印和区域遮挡' },
  { icon: '🔄', title: '反复练习', desc: '不限次数练习，每次题目不同，持续提升面试技巧' }
]

const introItems = [
  { title: '面试前', desc: '解析简历、明确岗位方向、生成更贴近经历的问题' },
  { title: '面试中', desc: '通过 AI 面试官多轮追问，训练表达结构和临场反应' },
  { title: '面试后', desc: '输出评分报告与改进建议，结合面经和笔记持续复盘' }
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
    // 复用已有的游客 token，避免重复创建匿名用户
    if (authStore.isLoggedIn && authStore.isGuest) {
      router.push('/dashboard')
      return
    }
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
  color: var(--text-primary);
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

/* Hero */
.hero {
  position: relative;
  z-index: 2;
  background: linear-gradient(135deg, rgba(124,58,237,0.25) 0%, rgba(99,102,241,0.18) 50%, rgba(139,92,246,0.12) 100%);
  color: white;
  padding: 100px 20px 80px;
  text-align: center;
  border-bottom: 1px solid var(--border-default);
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
  font-family: 'Space Grotesk', sans-serif;
}
.highlight {
  background: linear-gradient(90deg, #c4b5fd, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-desc {
  font-size: 17px;
  opacity: 0.85;
  line-height: 1.7;
  margin-bottom: 32px;
  color: var(--text-secondary);
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
  color: white;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 24px rgba(124,58,237,0.35);
}
.btn-glow:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(124,58,237,0.5);
}
.btn-glow:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.btn-outline {
  padding: 14px 32px;
  border: 2px solid rgba(167,139,250,0.4);
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-light);
  text-decoration: none;
  transition: all 0.3s;
}
.btn-outline:hover {
  border-color: var(--accent-purple);
  background: rgba(139,92,246,0.1);
}
.hero-stats {
  font-size: 14px;
  color: var(--text-secondary);
}
.hero-stats strong {
  color: var(--accent-light);
}

/* Features */
.intro {
  position: relative;
  z-index: 2;
  max-width: 920px;
  margin: 0 auto;
  padding: 54px 20px 10px;
  text-align: center;
}
.intro-kicker {
  margin: 0 0 10px;
  color: var(--accent-cyan);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .12em;
}
.intro h2 {
  margin: 0 auto 14px;
  max-width: 680px;
  color: var(--text-primary);
  font-size: 28px;
  line-height: 1.35;
}
.intro-desc {
  max-width: 760px;
  margin: 0 auto 24px;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.8;
}
.intro-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.intro-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px 16px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-card);
  text-align: left;
}
.intro-item strong {
  color: var(--text-primary);
  font-size: 15px;
}
.intro-item span {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.features {
  position: relative;
  z-index: 2;
  padding: 60px 20px;
  max-width: 900px;
  margin: 0 auto;
}
.section-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 40px;
  font-family: 'Space Grotesk', sans-serif;
  background:var(--title-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.feature-card {
  background: var(--bg-card);
  border-radius: 14px;
  padding: 28px 24px;
  text-align: center;
  border: 1px solid var(--border-default);
  transition: all 0.3s;
}
.feature-card:hover {
  transform: translateY(-4px);
  border-color: var(--border-hover);
  box-shadow: 0 12px 40px rgba(139,92,246,0.1);
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
  color: var(--text-primary);
}
.feature-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Steps */
.steps {
  position: relative;
  z-index: 2;
  background: var(--bg-card);
  padding: 60px 20px;
  border-top: 1px solid var(--border-default);
  border-bottom: 1px solid var(--border-default);
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
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
  box-shadow: 0 4px 16px rgba(124,58,237,0.25);
}
.step-info h4 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--text-primary);
}
.step-info p {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* CTA */
.cta {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 60px 20px;
  max-width: 500px;
  margin: 0 auto;
}
.cta h2 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-primary);
}
.cta p {
  color: var(--text-secondary);
  margin-bottom: 24px;
}

/* Footer */
.footer {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 30px 20px;
  border-top: 1px solid var(--border-default);
  font-size: 13px;
  color: var(--text-muted);
}
.footer-links {
  margin-top: 8px;
  display: flex;
  gap: 16px;
  justify-content: center;
}
.footer-links a {
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.2s;
}
.footer-links a:hover {
  color: var(--accent-primary);
}

/* Responsive */
@media (max-width: 768px) {
  .hero { padding: 60px 20px 40px; }
  .hero h1 { font-size: 28px; }
  .feature-grid { grid-template-columns: 1fr 1fr; }
  .intro-grid { grid-template-columns: 1fr; }
  .intro h2 { font-size: 24px; }
}
@media (max-width: 640px) {
  .feature-grid { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .hero h1 { font-size: 24px; }
  .hero-desc { font-size: 15px; }
  .btn-glow, .btn-outline { width: 100%; text-align: center; }
}
</style>
