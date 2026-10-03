<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="font-size:20px">⚙️ 系统设置</h1>
      <button class="btn-primary btn-sm" @click="handleSave" :disabled="saving">
        {{ saving ? '保存中...' : '💾 保存所有设置' }}
      </button>
    </div>

    <div v-if="loading" style="text-align:center;padding:60px;color:#6b7280">加载中...</div>

    <div v-else class="settings-grid">
      <!-- 基本信息 -->
      <div class="card settings-section">
        <h3 class="section-title">🏷️ 基本信息</h3>
        <div class="form-group">
          <label>网站名称</label>
          <input v-model="form.site_name" placeholder="智面 AI" />
        </div>
        <div class="form-group">
          <label>标语</label>
          <input v-model="form.site_slogan" placeholder="AI 驱动的智能模拟面试平台" />
        </div>
        <div class="form-group">
          <label>Logo 路径</label>
          <input v-model="form.site_logo" placeholder="/uploads/logo.png" />
        </div>
      </div>

      <!-- SEO 设置 -->
      <div class="card settings-section">
        <h3 class="section-title">🔍 SEO 设置</h3>
        <div class="form-group">
          <label>SEO 标题</label>
          <input v-model="form.seo_title" placeholder="智面 AI — 智能模拟面试平台" />
        </div>
        <div class="form-group">
          <label>SEO 描述</label>
          <textarea v-model="form.seo_description" rows="3" placeholder="网站描述..."></textarea>
        </div>
      </div>

      <!-- 功能开关 -->
      <div class="card settings-section">
        <h3 class="section-title">🔧 功能开关</h3>
        <div class="toggle-group">
          <div class="toggle-item">
            <div>
              <div class="toggle-label">维护模式</div>
              <div class="toggle-desc">开启后前台显示维护公告，暂停所有用户操作</div>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="boolForm.maintenance_mode" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div>
              <div class="toggle-label">开放注册</div>
              <div class="toggle-desc">关闭后新用户无法注册，仅已有用户可登录</div>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="boolForm.register_enabled" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div>
              <div class="toggle-label">游客模式</div>
              <div class="toggle-desc">允许未注册用户以游客身份体验基础功能</div>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="boolForm.guest_enabled" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div>
              <div class="toggle-label">AI 生图</div>
              <div class="toggle-desc">开启后用户可使用 AI 画图功能，关闭后用户端提示“该生图功能已关闭请稍后再试~”</div>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="boolForm.image_generation_enabled" />
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- 其他 -->
      <div class="card settings-section">
        <h3 class="section-title">📧 其他</h3>
        <div class="form-group">
          <label>备案号</label>
          <input v-model="form.icp_number" placeholder="京ICP备XXXXXXXX号" />
        </div>
        <div class="form-group">
          <label>联系邮箱</label>
          <input v-model="form.contact_email" placeholder="contact@example.com" type="email" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { settingsApi } from '../api'

const loading = ref(true)
const saving = ref(false)

const form = ref({
  site_name: '',
  site_slogan: '',
  site_logo: '',
  seo_title: '',
  seo_description: '',
  icp_number: '',
  contact_email: '',
})

const boolForm = ref({
  maintenance_mode: false,
  register_enabled: true,
  guest_enabled: true,
  image_generation_enabled: true,
})

async function loadSettings() {
  try {
    const data = await settingsApi.list()
    const items = data.items || []
    for (const s of items) {
      if (s.key in form.value) {
        form.value[s.key] = s.value || ''
      }
      if (s.key in boolForm.value) {
        boolForm.value[s.key] = String(s.value).toLowerCase() === 'true'
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const settings = []
    for (const [key, value] of Object.entries(form.value)) {
      settings.push({ key, value })
    }
    for (const [key, value] of Object.entries(boolForm.value)) {
      settings.push({ key, value: String(value) })
    }
    await settingsApi.batchUpdate({ settings })
    alert('保存成功')
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.settings-section {
  padding: 20px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #1e293b;
}

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #374151;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group textarea {
  resize: vertical;
}

.toggle-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toggle-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.toggle-item:last-child {
  border-bottom: none;
}

.toggle-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.toggle-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

/* Toggle switch */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #cbd5e1;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #4f46e5;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

@media (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
