<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="font-size:20px">📋 操作日志</h1>
      <button class="btn-primary btn-sm" @click="handleExport">导出 CSV</button>
    </div>

    <!-- 筛选 -->
    <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <select v-model="filterAction" @change="page=1;loadLogs()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px">
        <option value="">全部操作</option>
        <option value="login">登录</option>
        <option value="create">创建</option>
        <option value="update">更新</option>
        <option value="delete">删除</option>
        <option value="disable">禁用</option>
        <option value="enable">启用</option>
        <option value="approve">审核通过</option>
        <option value="reject">审核拒绝</option>
      </select>
      <select v-model="filterTarget" @change="page=1;loadLogs()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px">
        <option value="">全部对象</option>
        <option value="user">用户</option>
        <option value="experience">面经</option>
        <option value="announcement">公告</option>
        <option value="admin">管理员</option>
        <option value="setting">设置</option>
        <option value="feedback">反馈</option>
      </select>
      <input v-model="dateFrom" type="date" @change="page=1;loadLogs()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px" placeholder="开始日期" />
      <input v-model="dateTo" type="date" @change="page=1;loadLogs()" style="padding:6px 12px;border-radius:6px;border:1px solid #d1d5db;font-size:13px" placeholder="结束日期" />
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>操作人</th>
            <th>操作类型</th>
            <th>操作对象</th>
            <th>对象ID</th>
            <th>详情</th>
            <th>IP</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in logs" :key="l.id">
            <td>{{ l.id }}</td>
            <td>{{ l.admin_id }}</td>
            <td><span class="tag" :class="`action-${l.action}`">{{ actionLabels[l.action] || l.action }}</span></td>
            <td>{{ targetLabels[l.target_type] || l.target_type }}</td>
            <td>{{ l.target_id || '-' }}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ l.detail || '-' }}</td>
            <td>{{ l.ip_address || '-' }}</td>
            <td>{{ formatDate(l.created_at) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > perPage">
        <button class="btn-sm" :disabled="page <= 1" @click="page--;loadLogs()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }}</span>
        <button class="btn-sm" :disabled="page >= Math.ceil(total / perPage)" @click="page++;loadLogs()">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { auditLogApi } from '../api'

const logs = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const filterAction = ref('')
const filterTarget = ref('')
const dateFrom = ref('')
const dateTo = ref('')

const actionLabels = { login: '登录', create: '创建', update: '更新', delete: '删除', disable: '禁用', enable: '启用', approve: '审核通过', reject: '审核拒绝' }
const targetLabels = { user: '用户', experience: '面经', announcement: '公告', admin: '管理员', setting: '设置', feedback: '反馈' }

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN')
}

async function loadLogs() {
  try {
    const params = { page: page.value, per_page: perPage }
    if (filterAction.value) params.action = filterAction.value
    if (filterTarget.value) params.target_type = filterTarget.value
    if (dateFrom.value) params.date_from = dateFrom.value + 'T00:00:00'
    if (dateTo.value) params.date_to = dateTo.value + 'T23:59:59'
    const data = await auditLogApi.list(params)
    logs.value = data.items
    total.value = data.total
  } catch (e) { console.error(e) }
}

async function handleExport() {
  try {
    const params = {}
    if (filterAction.value) params.action = filterAction.value
    if (filterTarget.value) params.target_type = filterTarget.value
    if (dateFrom.value) params.date_from = dateFrom.value + 'T00:00:00'
    if (dateTo.value) params.date_to = dateTo.value + 'T23:59:59'
    const blob = await auditLogApi.export(params)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit_logs.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert('导出失败: ' + e.message) }
}

onMounted(loadLogs)
</script>

<style scoped>
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.action-login { background: #dbeafe; color: #1e40af; }
.action-create { background: #d1fae5; color: #065f46; }
.action-update { background: #fef3c7; color: #92400e; }
.action-delete { background: #fef2f2; color: #dc2626; }
.action-disable { background: #fce7f3; color: #9d174d; }
.action-enable { background: #d1fae5; color: #065f46; }
.action-approve { background: #d1fae5; color: #065f46; }
.action-reject { background: #fef2f2; color: #dc2626; }
</style>
