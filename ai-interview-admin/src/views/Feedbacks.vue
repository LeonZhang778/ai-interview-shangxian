<template>
  <div>
    <h1 style="font-size:20px;margin-bottom:20px">📝 用户反馈管理</h1>

    <!-- 统计卡片 -->
    <div style="display:flex;gap:16px;margin-bottom:20px">
      <div v-for="s in statCards" :key="s.key" class="stat-card" :style="{ borderColor: s.color }">
        <span class="stat-num" :style="{ color: s.color }">{{ feedbackStats[s.key] || 0 }}</span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
    </div>

    <!-- 筛选 -->
    <div style="display:flex;gap:12px;margin-bottom:16px">
      <select v-model="filterStatus" @change="page=1;loadFeedbacks()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px">
        <option value="">全部状态</option>
        <option value="pending">待处理</option>
        <option value="processing">处理中</option>
        <option value="resolved">已解决</option>
        <option value="ignored">已忽略</option>
      </select>
      <select v-model="filterType" @change="page=1;loadFeedbacks()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px">
        <option value="">全部类型</option>
        <option value="bug">Bug</option>
        <option value="suggestion">建议</option>
        <option value="other">其他</option>
      </select>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>类型</th>
            <th>内容摘要</th>
            <th>用户ID</th>
            <th>状态</th>
            <th>提交时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in feedbacks" :key="f.id">
            <td>{{ f.id }}</td>
            <td><span class="tag" :class="`type-${f.feedback_type}`">{{ typeLabels[f.feedback_type] || f.feedback_type }}</span></td>
            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ f.content }}</td>
            <td>{{ f.user_id || '游客' }}</td>
            <td><span :class="['badge', statusClass(f.status)]">{{ statusLabels[f.status] || f.status }}</span></td>
            <td>{{ formatDate(f.created_at) }}</td>
            <td>
              <button class="btn-sm" @click="openDetail(f)">详情</button>
              <button v-if="f.status==='pending'" class="btn-sm btn-primary" @click="updateStatus(f, 'processing')" style="margin-left:4px">处理</button>
              <button v-if="f.status!=='resolved'" class="btn-sm btn-primary" @click="updateStatus(f, 'resolved')" style="margin-left:4px">解决</button>
              <button v-if="f.status!=='ignored'" class="btn-sm" @click="updateStatus(f, 'ignored')" style="margin-left:4px">忽略</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > perPage">
        <button class="btn-sm" :disabled="page <= 1" @click="page--;loadFeedbacks()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }}</span>
        <button class="btn-sm" :disabled="page >= Math.ceil(total / perPage)" @click="page++;loadFeedbacks()">下一页</button>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="showDetail" class="modal-overlay" @click.self="showDetail = false">
      <div class="modal">
        <h2 style="margin-bottom:16px;font-size:18px">反馈详情 #{{ detailItem.id }}</h2>
        <div class="detail-row"><span class="detail-label">类型</span><span class="tag" :class="`type-${detailItem.feedback_type}`">{{ typeLabels[detailItem.feedback_type] }}</span></div>
        <div class="detail-row"><span class="detail-label">状态</span><span :class="['badge', statusClass(detailItem.status)]">{{ statusLabels[detailItem.status] }}</span></div>
        <div class="detail-row"><span class="detail-label">用户</span><span>{{ detailItem.user_id || '游客' }}</span></div>
        <div class="detail-row"><span class="detail-label">联系方式</span><span>{{ detailItem.contact || '未提供' }}</span></div>
        <div class="detail-row"><span class="detail-label">页面</span><span style="word-break:break-all">{{ detailItem.page_url || '未记录' }}</span></div>
        <div class="detail-row"><span class="detail-label">时间</span><span>{{ formatDate(detailItem.created_at) }}</span></div>
        <div style="margin:12px 0">
          <div class="detail-label">内容</div>
          <div style="background:#f8fafc;padding:12px;border-radius:8px;margin-top:4px;white-space:pre-wrap;font-size:14px">{{ detailItem.content }}</div>
        </div>
        <div v-if="detailItem.screenshot_url" style="margin:12px 0">
          <div class="detail-label">截图</div>
          <img :src="detailItem.screenshot_url" style="max-width:100%;border-radius:8px;margin-top:4px" />
        </div>
        <div v-if="detailItem.admin_reply" style="margin:12px 0">
          <div class="detail-label">管理员回复</div>
          <div style="background:#eff6ff;padding:12px;border-radius:8px;margin-top:4px;white-space:pre-wrap;font-size:14px">{{ detailItem.admin_reply }}</div>
        </div>
        <div style="margin-top:16px">
          <div class="detail-label">回复</div>
          <textarea v-model="replyText" rows="3" placeholder="输入回复内容..." style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;box-sizing:border-box;margin-top:4px"></textarea>
        </div>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
          <button class="btn-sm" @click="showDetail = false">关闭</button>
          <button class="btn-primary btn-sm" @click="handleReply" :disabled="!replyText">回复并解决</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { feedbackApi } from '../api'

const feedbacks = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const filterStatus = ref('')
const filterType = ref('')
const showDetail = ref(false)
const detailItem = ref({})
const replyText = ref('')
const feedbackStats = ref({})

const typeLabels = { bug: 'Bug', suggestion: '建议', other: '其他' }
const statusLabels = { pending: '待处理', processing: '处理中', resolved: '已解决', ignored: '已忽略' }
const statCards = [
  { key: 'pending', label: '待处理', color: '#f59e0b' },
  { key: 'processing', label: '处理中', color: '#3b82f6' },
  { key: 'resolved', label: '已解决', color: '#10b981' },
  { key: 'ignored', label: '已忽略', color: '#6b7280' },
]

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN')
}

function statusClass(status) {
  return { pending: 'badge-yellow', processing: 'badge-blue', resolved: 'badge-green', ignored: 'badge-gray' }[status] || ''
}

async function loadFeedbacks() {
  try {
    const params = { page: page.value, per_page: perPage }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterType.value) params.feedback_type = filterType.value
    const data = await feedbackApi.list(params)
    feedbacks.value = data.items
    total.value = data.total
  } catch (e) { console.error(e) }
}

async function loadStats() {
  try { feedbackStats.value = await feedbackApi.stats() } catch (e) { console.error(e) }
}

function openDetail(f) {
  detailItem.value = f
  replyText.value = ''
  showDetail.value = true
}

async function updateStatus(f, status) {
  try {
    await feedbackApi.updateStatus(f.id, status)
    f.status = status
    loadStats()
  } catch (e) { alert('操作失败: ' + e.message) }
}

async function handleReply() {
  try {
    await feedbackApi.reply(detailItem.value.id, replyText.value)
    detailItem.value.status = 'resolved'
    detailItem.value.admin_reply = replyText.value
    showDetail.value = false
    loadFeedbacks()
    loadStats()
  } catch (e) { alert('回复失败: ' + e.message) }
}

onMounted(() => { loadFeedbacks(); loadStats() })
</script>

<style scoped>
.stat-card {
  background: white;
  border-radius: 10px;
  padding: 16px 24px;
  border-left: 4px solid;
  display: flex;
  flex-direction: column;
  flex: 1;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stat-num { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: #6b7280; margin-top: 2px; }

.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.tag.type-bug { background: #fef2f2; color: #dc2626; }
.tag.type-suggestion { background: #eff6ff; color: #2563eb; }
.tag.type-other { background: #f1f5f9; color: #64748b; }

.badge-yellow { background: #fef3c7; color: #92400e; }
.badge-blue { background: #dbeafe; color: #1e40af; }
.badge-green { background: #d1fae5; color: #065f46; }
.badge-gray { background: #f1f5f9; color: #64748b; }

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 560px;
  max-height: 80vh;
  overflow-y: auto;
}
.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 14px;
}
.detail-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  min-width: 60px;
}
</style>
