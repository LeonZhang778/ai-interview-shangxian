<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="font-size:20px">📢 公告管理</h1>
      <button class="btn-primary btn-sm" @click="openCreate">+ 发布公告</button>
    </div>

    <!-- 筛选 -->
    <div style="display:flex;gap:12px;margin-bottom:16px">
      <select v-model="filterType" @change="page=1;loadAnnouncements()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px">
        <option value="">全部类型</option>
        <option value="info">通知</option>
        <option value="update">更新</option>
        <option value="maintenance">维护</option>
        <option value="activity">活动</option>
      </select>
      <select v-model="filterActive" @change="page=1;loadAnnouncements()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px">
        <option value="">全部状态</option>
        <option value="true">已上线</option>
        <option value="false">已下线</option>
      </select>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>标题</th>
            <th>类型</th>
            <th>状态</th>
            <th>置顶</th>
            <th>发布时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in announcements" :key="a.id">
            <td>{{ a.id }}</td>
            <td>{{ a.title }}</td>
            <td><span class="tag" :class="`type-${a.type}`">{{ typeLabels[a.type] || a.type }}</span></td>
            <td><span :class="['badge', a.is_active ? 'badge-green' : 'badge-red']">{{ a.is_active ? '已上线' : '已下线' }}</span></td>
            <td>
              <button class="btn-sm" :style="a.is_pinned ? 'background:#f59e0b;color:white' : ''" @click="togglePin(a)">
                {{ a.is_pinned ? '📌 已置顶' : '置顶' }}
              </button>
            </td>
            <td>{{ formatDate(a.published_at || a.created_at) }}</td>
            <td>
              <button class="btn-sm" @click="openEdit(a)">编辑</button>
              <button class="btn-sm" :class="a.is_active ? 'btn-danger' : 'btn-primary'" @click="toggleStatus(a)" style="margin-left:4px">
                {{ a.is_active ? '下线' : '上线' }}
              </button>
              <button class="btn-sm btn-danger" @click="handleDelete(a)" style="margin-left:4px">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > perPage">
        <button class="btn-sm" :disabled="page <= 1" @click="page--;loadAnnouncements()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }}</span>
        <button class="btn-sm" :disabled="page >= Math.ceil(total / perPage)" @click="page++;loadAnnouncements()">下一页</button>
      </div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h2 style="margin-bottom:16px;font-size:18px">{{ editingId ? '编辑公告' : '发布公告' }}</h2>
        <div class="form-group">
          <label>标题</label>
          <input v-model="form.title" placeholder="公告标题" />
        </div>
        <div class="form-group">
          <label>类型</label>
          <select v-model="form.announcement_type">
            <option value="info">通知</option>
            <option value="update">更新</option>
            <option value="maintenance">维护</option>
            <option value="activity">活动</option>
          </select>
        </div>
        <div class="form-group">
          <label>内容</label>
          <textarea v-model="form.content" rows="8" placeholder="公告内容（支持 **加粗** 语法）"></textarea>
        </div>
        <div style="display:flex;gap:16px;margin-bottom:12px">
          <label style="display:flex;align-items:center;gap:6px;font-size:13px">
            <input type="checkbox" v-model="form.is_pinned" /> 置顶
          </label>
        </div>
        <div class="form-group">
          <label>过期时间（可选）</label>
          <input v-model="form.expired_at" type="datetime-local" />
        </div>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
          <button class="btn-sm" @click="showModal = false">取消</button>
          <button class="btn-primary btn-sm" @click="handleSave" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { announcementApi } from '../api'

const announcements = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const filterType = ref('')
const filterActive = ref('')
const showModal = ref(false)
const editingId = ref(null)
const saving = ref(false)
const typeLabels = { info: '通知', update: '更新', maintenance: '维护', activity: '活动' }

const defaultForm = { title: '', content: '', announcement_type: 'info', is_pinned: false, expired_at: '' }
const form = ref({ ...defaultForm })

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN')
}

async function loadAnnouncements() {
  try {
    const params = { page: page.value, per_page: perPage }
    if (filterType.value) params.announcement_type = filterType.value
    if (filterActive.value) params.is_active = filterActive.value
    const data = await announcementApi.list(params)
    announcements.value = data.items
    total.value = data.total
  } catch (e) { console.error(e) }
}

function openCreate() {
  editingId.value = null
  form.value = { ...defaultForm }
  showModal.value = true
}

function openEdit(a) {
  editingId.value = a.id
  form.value = {
    title: a.title,
    content: a.content,
    announcement_type: a.type,
    is_pinned: a.is_pinned,
    expired_at: a.expired_at ? a.expired_at.slice(0, 16) : ''
  }
  showModal.value = true
}

async function handleSave() {
  if (!form.value.title || !form.value.content) { alert('标题和内容不能为空'); return }
  saving.value = true
  try {
    const payload = { ...form.value }
    if (payload.expired_at) payload.expired_at = new Date(payload.expired_at).toISOString()
    else delete payload.expired_at

    if (editingId.value) {
      await announcementApi.update(editingId.value, payload)
    } else {
      await announcementApi.create(payload)
    }
    showModal.value = false
    loadAnnouncements()
  } catch (e) { alert('保存失败: ' + e.message) }
  finally { saving.value = false }
}

async function togglePin(a) {
  try {
    const data = await announcementApi.togglePin(a.id)
    a.is_pinned = data.is_pinned
  } catch (e) { console.error(e) }
}

async function toggleStatus(a) {
  try {
    const data = await announcementApi.toggleStatus(a.id, !a.is_active)
    a.is_active = data.is_active
  } catch (e) { console.error(e) }
}

async function handleDelete(a) {
  if (!confirm(`确定删除公告「${a.title}」？`)) return
  try {
    await announcementApi.delete(a.id)
    loadAnnouncements()
  } catch (e) { alert('删除失败: ' + e.message) }
}

onMounted(loadAnnouncements)
</script>

<style scoped>
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.tag.type-info { background: #dbeafe; color: #1e40af; }
.tag.type-update { background: #d1fae5; color: #065f46; }
.tag.type-maintenance { background: #fef3c7; color: #92400e; }
.tag.type-activity { background: #fce7f3; color: #9d174d; }

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
  width: 520px;
  max-height: 80vh;
  overflow-y: auto;
}
.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #374151;
}
.form-group input,
.form-group select,
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
</style>
