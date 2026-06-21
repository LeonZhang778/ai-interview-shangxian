<template>
  <div class="experiences-page">
    <div class="page-header">
      <h2>面经管理</h2>
      <div class="header-actions">
        <div class="status-tabs">
          <button
            v-for="tab in statusTabs"
            :key="tab.value"
            class="tab-btn"
            :class="{ active: currentStatus === tab.value }"
            @click="currentStatus = tab.value"
          >{{ tab.label }}</button>
        </div>
      </div>
    </div>

    <div class="content-card">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="items.length === 0" class="empty-state">暂无数据</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>标题</th>
            <th>公司</th>
            <th>岗位</th>
            <th>作者</th>
            <th>状态</th>
            <th>阅读/点赞</th>
            <th>投稿时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.id }}</td>
            <td class="title-cell">{{ item.title }}</td>
            <td>{{ item.company }}</td>
            <td>{{ item.position }}</td>
            <td>{{ item.author_name }}</td>
            <td>
              <span class="status-badge" :class="item.status">
                {{ statusMap[item.status] || item.status }}
              </span>
            </td>
            <td>{{ item.view_count }} / {{ item.like_count }}</td>
            <td>{{ item.created_at }}</td>
            <td class="action-cell">
              <button class="btn-action btn-view" @click="viewDetail(item)">查看</button>
              <template v-if="item.status === 'pending'">
                <button class="btn-action btn-approve" @click="review(item.id, 'approve')">通过</button>
                <button class="btn-action btn-reject" @click="review(item.id, 'reject')">拒绝</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 分页 -->
      <div class="pagination" v-if="total > perPage">
        <button :disabled="page <= 1" @click="page--; fetchData()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }}</span>
        <button :disabled="page * perPage >= total" @click="page++; fetchData()">下一页</button>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailItem" class="modal-overlay" @click.self="detailItem = null">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ detailItem.title }}</h3>
          <button class="modal-close" @click="detailItem = null">&times;</button>
        </div>
        <div class="modal-body">
          <div class="detail-meta">
            <span><strong>公司：</strong>{{ detailItem.company }}</span>
            <span><strong>岗位：</strong>{{ detailItem.position }}</span>
            <span v-if="detailItem.level"><strong>级别：</strong>{{ detailItem.level }}</span>
            <span v-if="detailItem.round"><strong>轮次：</strong>{{ detailItem.round }}</span>
            <span><strong>作者：</strong>{{ detailItem.author_name }}</span>
            <span><strong>状态：</strong>{{ statusMap[detailItem.status] }}</span>
          </div>
          <div v-if="detailItem.tags.length" class="detail-tags">
            <span v-for="t in detailItem.tags" :key="t" class="tag">{{ t }}</span>
          </div>
          <div class="detail-content">{{ detailItem.content }}</div>
        </div>
        <div class="modal-footer" v-if="detailItem.status === 'pending'">
          <button class="btn-action btn-approve" @click="review(detailItem.id, 'approve'); detailItem = null">通过</button>
          <button class="btn-action btn-reject" @click="review(detailItem.id, 'reject'); detailItem = null">拒绝</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { experienceApi } from '../api'

const items = ref([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)
const currentStatus = ref('')
const detailItem = ref(null)

const statusTabs = [
  { label: '全部', value: '' },
  { label: '待审核', value: 'pending' },
  { label: '已发布', value: 'published' },
  { label: '已拒绝', value: 'rejected' }
]

const statusMap = {
  pending: '待审核',
  published: '已发布',
  rejected: '已拒绝',
  draft: '草稿'
}

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, per_page: perPage }
    if (currentStatus.value) params.status = currentStatus.value
    const res = await experienceApi.list(params)
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    console.error('加载面经列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function viewDetail(item) {
  try {
    const res = await experienceApi.detail(item.id)
    detailItem.value = res
  } catch (e) {
    console.error('获取详情失败:', e)
  }
}

async function review(id, action) {
  try {
    await experienceApi.review(id, action)
    fetchData()
  } catch (e) {
    alert(e.response?.data?.message || '操作失败')
  }
}

watch(currentStatus, () => {
  page.value = 1
  fetchData()
})

onMounted(() => fetchData())
</script>

<style scoped>
.experiences-page { }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
}

.status-tabs { display: flex; gap: 4px; }
.tab-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  background: white;
  color: #64748b;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.2s;
}
.tab-btn:hover { background: #f1f5f9; }
.tab-btn.active {
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: white;
  border-color: transparent;
}

.content-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th {
  background: #f8fafc;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
}
.data-table td {
  padding: 12px 16px;
  font-size: 14px;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}
.data-table tr:hover { background: #f8fafc; }

.title-cell {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.status-badge.pending { background: #fef3c7; color: #92400e; }
.status-badge.published { background: #d1fae5; color: #065f46; }
.status-badge.rejected { background: #fee2e2; color: #991b1b; }

.action-cell { display: flex; gap: 6px; }
.btn-action {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-view { background: #e0e7ff; color: #3730a3; }
.btn-view:hover { background: #c7d2fe; }
.btn-approve { background: #d1fae5; color: #065f46; }
.btn-approve:hover { background: #a7f3d0; }
.btn-reject { background: #fee2e2; color: #991b1b; }
.btn-reject:hover { background: #fecaca; }

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-top: 1px solid #e2e8f0;
}
.pagination button {
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 13px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #475569;
  cursor: pointer;
}
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }

.loading-state, .empty-state {
  text-align: center;
  padding: 60px;
  color: #94a3b8;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: white;
  border-radius: 14px;
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}
.modal-header h3 { font-size: 18px; font-weight: 700; color: #1e293b; }
.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
}
.modal-body { padding: 24px; }
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #475569;
}
.detail-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.detail-tags .tag {
  padding: 3px 10px;
  background: #ede9fe;
  color: #6d28d9;
  border-radius: 12px;
  font-size: 12px;
}
.detail-content {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.8;
  color: #334155;
  background: #f8fafc;
  padding: 16px;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
}
.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
}
.modal-footer .btn-action { padding: 8px 20px; font-size: 14px; }
</style>
