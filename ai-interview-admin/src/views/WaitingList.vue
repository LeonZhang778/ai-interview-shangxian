<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="font-size:20px">📋 候选名单</h1>
      <div style="display:flex;gap:12px;align-items:center">
        <select v-model="statusFilter" @change="page = 1; loadList()" style="width:120px">
          <option value="all">全部状态</option>
          <option value="active">已验证</option>
          <option value="invited">未验证</option>
        </select>
        <select v-model="searchType" style="width:100px">
          <option value="all">全部</option>
          <option value="name">姓名</option>
          <option value="email">邮箱</option>
        </select>
        <input v-model="searchText" placeholder="搜索..." style="width:200px" @input="debouncedSearch" />
      </div>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>姓名</th>
            <th>邮箱</th>
            <th>学校</th>
            <th>状态</th>
            <th>验证时间</th>
            <th>提交时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in list" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.first_name }} {{ item.last_name }}</td>
            <td>{{ item.email }}</td>
            <td>{{ item.university || '-' }}</td>
            <td><span :class="['badge', item.is_verified ? 'badge-green' : 'badge-yellow']">{{ item.is_verified ? '已验证' : '未验证' }}</span></td>
            <td>{{ item.verified_at ? formatDate(item.verified_at) : '-' }}</td>
            <td>{{ formatDate(item.created_at) }}</td>
          </tr>
          <tr v-if="list.length === 0">
            <td colspan="7" style="text-align:center;color:#9ca3af;padding:40px">暂无数据</td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > perPage">
        <button class="btn-sm" :disabled="page <= 1" @click="page--; loadList()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }}</span>
        <button class="btn-sm" :disabled="page >= Math.ceil(total / perPage)" @click="page++; loadList()">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { waitingListApi } from '../api'

const list = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const statusFilter = ref('all')
const searchType = ref('all')
const searchText = ref('')
let searchTimer = null

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN')
}

async function loadList() {
  try {
    const params = { page: page.value, per_page: perPage }
    if (statusFilter.value !== 'all') params.status = statusFilter.value
    if (searchText.value) {
      params.search = searchText.value
      params.search_type = searchType.value
    }
    const data = await waitingListApi.list(params)
    list.value = data.items
    total.value = data.total
  } catch (e) { console.error(e) }
}

function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadList() }, 300)
}

onMounted(loadList)
</script>

<style scoped>
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 16px 0 0; font-size: 13px; color: #6b7280; }
</style>
