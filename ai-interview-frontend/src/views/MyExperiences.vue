<template>
  <StarryBackground />
  <div class="my-experiences-page">
    <div class="page-header">
      <h1>我的投稿</h1>
      <p>查看投稿状态，继续修改待完善内容</p>
    </div>

    <div class="main-container">
      <div v-if="loading" class="loading-state">加载中...</div>

      <div v-else-if="items.length === 0" class="empty-state">
        <div class="empty-icon"><BaseIcon name="file-text" :size="40" /></div>
        <p>你还没有投稿过面经</p>
        <router-link to="/experiences/submit" class="btn-submit-link">去投稿</router-link>
      </div>

      <div v-else class="experience-list">
        <article v-for="item in items" :key="item.id" class="experience-card">
          <div class="card-main">
            <div class="card-top">
              <h3>{{ item.title }}</h3>
              <span class="status-badge" :class="`status-${item.status}`">{{ statusLabel(item.status) }}</span>
            </div>
            <div class="meta-row">
              <span>{{ item.company }}</span>
              <span>{{ item.position }}</span>
              <span>{{ item.created_at }}</span>
            </div>
            <div v-if="item.tags?.length" class="tags-row">
              <span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>

          <div class="card-actions">
            <router-link :to="`/my/experiences/${item.id}/edit`" class="btn-secondary">编辑</router-link>
            <router-link v-if="item.status === 'published'" :to="`/experiences/${item.id}`" class="btn-primary">查看详情</router-link>
          </div>
        </article>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <button class="page-btn" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'
import { getMyExperiences } from '../api/experience'

const items = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const size = 20

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size)))

function statusLabel(status) {
  if (status === 'published') return '已发布'
  if (status === 'rejected') return '已拒绝'
  return '审核中'
}

async function loadData() {
  loading.value = true
  try {
    const data = await getMyExperiences({ page: page.value, size })
    items.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

function changePage(nextPage) {
  page.value = nextPage
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.my-experiences-page {
  min-height: 100vh;
  padding-bottom: 60px;
}

.page-header {
  text-align: center;
  padding: 40px 20px 22px;
}

.page-header h1 {
  font-size: 30px;
  font-weight: 800;
  margin: 0 0 10px;
  color: var(--text-primary);

}

.page-header p {
  color: var(--text-muted);
  margin: 0;
}

.main-container {
  max-width: 920px;
  margin: 0 auto;
  padding: 0 20px;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.btn-submit-link {
  display: inline-block;
  margin-top: 16px;
  padding: 10px 24px;
  border-radius: 8px;
  background: var(--accent-primary);
  color: #fff;
  text-decoration: none;
  font-weight: 600;
}

.experience-list {
  display: grid;
  gap: 14px;
}

.experience-card {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-card);
}

.card-main {
  flex: 1;
  min-width: 0;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.card-top h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: 10px;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 12px;
}

.status-badge {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
}

.status-published {
  background: var(--green-bg);
  color: var(--state-success);
}

.status-pending {
  background: var(--amber-bg);
  color: var(--state-warning);
}

.status-rejected {
  background: var(--red-bg);
  color: var(--state-error);
}

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: stretch;
}

.btn-secondary,
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112px;
  padding: 10px 14px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
}

.btn-secondary {
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.btn-primary {
  background: var(--accent-primary);
  color: #fff;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

.page-btn {
  padding: 8px 18px;
  border-radius: 8px;
  border: 1px solid var(--border-default);
  background: var(--bg-hover);
  color: var(--text-secondary);
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: var(--text-muted);
  font-size: 13px;
}

@media (max-width: 768px) {
  .experience-card {
    flex-direction: column;
  }

  .card-actions {
    flex-direction: row;
  }
}
</style>
